"""Physical model, grading, portability, and package-contract regression tests."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
from pathlib import Path
EXPERT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERT))
import ast
import copy
import hashlib
import json
import tempfile
import unittest
import numpy as np
import jsonschema
from scipy.special import expit
from model import load_data, read_json, features, occupancy, slope, protein_arrays, evidence
from score_rubric import assess, load_answer
from build_rubric_md import build
from export_solver import export


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = EXPERT.parent/'task/data'
        cls.D = load_data(cls.data); cls.D['data_dir'] = str(cls.data)
        cls.answer = read_json(EXPERT/'final_answer.json')
        cls.report = (EXPERT/'analysis.md').read_text()

    def test_input_integrity_and_keys(self):
        import runpy
        self.assertTrue(runpy.run_path(str(self.data/'validate_dataset.py'))['validate'](self.data))

    def test_schema(self):
        jsonschema.validate(self.answer, read_json(self.data/'output_schema.json'))

    def test_oracle_100_and_margin(self):
        r = assess(self.answer, self.D, self.report)
        self.assertEqual(r['final_score'], 100)
        self.assertTrue(all(g['value'] <= g['threshold']/3 for g in r['scientific_gates'] if g['threshold']))

    def test_full_quadratic_feature_rank(self):
        train = [i for i, r in enumerate(self.D['rows']) if r['role'] == 'screen']
        X = features(self.D['bits'][train])
        self.assertEqual(X.shape[1], 1+20+190)
        self.assertEqual(np.linalg.matrix_rank(X), X.shape[1])

    def test_partition_matches_independent_direct_formula(self):
        en = np.array([[.7, -1.3, .4], [-2., .2, -1.]])
        m = np.array([1.1, .8]); co = [dict(urea=.6, ligand_a=2., ligand_b=3.)]
        f = np.exp(-en[:, 0]-m*.6); a = 2*f*np.exp(-en[:, 1]); b = 3*f*np.exp(-en[:, 2]); z = 1+f+a+b
        pa, pb, folded = occupancy(en, m, co)
        np.testing.assert_allclose(pa[:, 0], a/z, atol=1e-15)
        np.testing.assert_allclose(pb[:, 0], b/z, atol=1e-15)
        np.testing.assert_allclose(folded[:, 0], (f+a+b)/z, atol=1e-15)

    def test_apo_identity_and_probability_conservation(self):
        en = np.array([[1000., -1000., 0.], [-1000., 1., 2.], [.3, .2, -.4]])
        pa, pb, folded = occupancy(en, np.ones(3), [dict(urea=0, ligand_a=0, ligand_b=0)])
        np.testing.assert_allclose(folded[:, 0], expit(-en[:, 0]), atol=1e-14)
        self.assertTrue(np.isfinite(folded).all()); self.assertTrue(np.max(pa+pb) <= 1)

    def test_capture_rows_have_no_order_dependence(self):
        D = dict(self.D); D['counts'] = list(reversed(self.D['counts']))
        p = self.D['meta']['proteins'][0]
        for a, b in zip(protein_arrays(D, p), protein_arrays(self.D, p)):
            np.testing.assert_array_equal(a, b)

    def test_zero_urea_reflection_and_denaturation_break(self):
        en = np.array([[1.2, -.6, .7], [-1.4, .8, -1.]])
        reflected = np.column_stack([-en[:, 0], en[:, 1]+en[:, 0], en[:, 2]+en[:, 0]])
        co = [dict(urea=0., ligand_a=2., ligand_b=4.), dict(urea=1., ligand_a=2., ligand_b=4.)]
        a = occupancy(en, np.ones(2), co)[0]; b = occupancy(reflected, np.ones(2), co)[0]
        np.testing.assert_allclose(a[:, 0], b[:, 0], atol=1e-15)
        self.assertGreater(float(np.max(np.abs(a[:, 1]-b[:, 1]))), .01)

    def test_wrapped_answer_only_loses_format_points(self):
        r = assess([self.answer], self.D, self.report)
        self.assertEqual(r['final_score'], 95); self.assertFalse(r['scientific_cap_applied'])

    def test_transpose_and_numeric_string_recovery(self):
        a = copy.deepcopy(self.answer)
        a['proteins'][0]['energy'] = np.array(a['proteins'][0]['energy']).T.tolist()
        a['proteins'][1]['energy'][0][0] = str(a['proteins'][1]['energy'][0][0])
        r = assess(a, self.D, self.report)
        self.assertEqual(r['final_score'], 95); self.assertFalse(r['failed_gates'])

    def test_one_probability_failure_cannot_pass(self):
        a = copy.deepcopy(self.answer); a['proteins'][0]['apo_folded'][0] = -.1
        r = assess(a, self.D, self.report)
        self.assertFalse(r['passed']); self.assertTrue(r['scientific_cap_applied'])

    def test_bad_energy_cannot_hide_behind_accurate_occupancy(self):
        a = copy.deepcopy(self.answer)
        a['proteins'][0]['energy'] = (np.array(a['proteins'][0]['energy'])+2).tolist()
        r = assess(a, self.D, self.report)
        self.assertFalse(r['passed']); self.assertTrue(any('energy_rmse' in g for g in r['failed_gates']))

    def test_wrong_design_is_scored_against_truth(self):
        from score_rubric import true_outputs
        truth = true_outputs(self.D, read_json(EXPERT/'private/truth.json'))
        a = copy.deepcopy(self.answer); obj = a['proteins'][0]
        i = int(np.argmin(truth[obj['id']]['utility']))
        obj['selected_variant'] = self.D['rows'][i]['variant_id']
        r = assess(a, self.D, self.report)
        self.assertFalse(r['passed']); self.assertIn(obj['id']+':design_regret', r['failed_gates'])

    def test_report_must_be_computed(self):
        r = assess(self.answer, self.D, 'All results are correct.')
        self.assertEqual(r['final_score'], 95); self.assertFalse(r['scientific_cap_applied'])

    def test_malformed_and_huge_values_do_not_crash(self):
        for bad in ['not_a_number', float('inf'), 10**400, True]:
            a = copy.deepcopy(self.answer); a['proteins'][0]['energy'][0][0] = bad
            r = assess(a, self.D, self.report)
            self.assertFalse(r['passed']); self.assertTrue(r['scientific_cap_applied'])

    def test_duplicates_recover_last_json_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'answer.json'; p.write_text('{"a":1,"a":2}')
            obj, findings, error = load_answer(p)
            self.assertEqual(obj, {'a': 2}); self.assertTrue(findings); self.assertIsNone(error)

    def test_unreadable_answer_is_zero(self):
        r = assess(None, self.D, self.report)
        self.assertEqual(r['final_score'], 0)

    def test_rubric_generated_from_contract_and_answer(self):
        for name, content in zip(['rubric.json', 'rubric.md'], build()):
            self.assertEqual((EXPERT/name).read_text(), content)
        contract = read_json(self.data/'grading_contract.json')
        self.assertEqual(sum(g['points'] for g in contract['groups'])+contract['report_points'], 100)
        prompt = (EXPERT.parent/'task/prompt.md').read_text()
        for g in contract['groups']: self.assertIn(g['threshold'], prompt)

    def test_exact_slots_and_required_expert_paths(self):
        slots = ['run_pipeline.py', 'final_answer.json', 'analysis.md']
        for name in ['deliverables.json', 'required_deliverables.json']:
            self.assertEqual(read_json(EXPERT.parent/'task'/name), slots)
        for name in ['config/parameters.yaml', 'results/run_summary.json']:
            self.assertTrue((EXPERT/name).is_file(), name)
        self.assertFalse(any('run_summary' in p.read_text() for p in (EXPERT.parent/'task').rglob('*') if p.is_file()))

    def test_summary_hashes_identify_shipped_inputs_and_answer(self):
        summary = read_json(EXPERT/'results/run_summary.json')
        self.assertEqual(summary['answer_sha256'], hashlib.sha256((EXPERT/'final_answer.json').read_bytes()).hexdigest())
        self.assertEqual(summary['data_manifest_sha256'], hashlib.sha256((self.data/'data_manifest.json').read_bytes()).hexdigest())

    def test_single_file_export_has_no_local_imports_or_truth_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = export(Path(tmp)/'run_pipeline.py'); tree = ast.parse(code)
            imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertFalse(imports & {'model', 'artifacts', 'expert_solution'})
            self.assertNotIn('private/truth', code)

    def test_missing_expert_summary_is_detected(self):
        # Simulate the exact prior missing path without altering shipped artifacts.
        import validate_package
        from unittest.mock import patch
        original = Path.is_file
        def present(path):
            return False if path == EXPERT/'results/run_summary.json' else original(path)
        with patch.object(Path, 'is_file', present):
            with self.assertRaisesRegex(AssertionError, 'expert_solution/results/run_summary.json'):
                validate_package.validate(EXPERT.parent)


if __name__ == '__main__':
    unittest.main()
