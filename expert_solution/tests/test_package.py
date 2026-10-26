"""Population, first-passage, finite ambiguity, grading, and packaging regressions."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys
from pathlib import Path
EXPERT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EXPERT));sys.path.insert(0,str(EXPERT/'tests'))
import copy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from itertools import product
import ast
import numpy as np
from scipy.linalg import expm
import jsonschema
from kinetics import load_data,read_json,generator,first_passage,observable,moments,decompose,compatible_family,candidate_statistics
from envelopes import feasible_joint_indices,joint_bounds
from score_rubric import assess,load_answer
from compute_truth import exact_families
from build_rubric_md import build,comparison_items
from independent_oracle import independent_join,independent_bounds,pencil_decomposition
from export_solver import export


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=EXPERT.parent/'task/data';cls.D=load_data(cls.data)
        cls.answer=read_json(EXPERT/'final_answer.json');cls.report=(EXPERT/'analysis.md').read_text()
        cls.truth=read_json(EXPERT/'private/truth.json');cls.expected=read_json(EXPERT/'private/expected_answer.json')

    def test_data_integrity_normalization_and_marginals(self):
        import runpy
        self.assertTrue(runpy.run_path(str(self.data/'validate_dataset.py'))['validate'](self.data))

    def test_answer_schema(self):
        jsonschema.validate(self.answer,read_json(self.data/'output_schema.json'))

    def test_expert_full_credit_and_threefold_clearance(self):
        r=assess(self.answer,self.D,self.report)
        self.assertEqual(r['final_score'],100)
        self.assertTrue(all(g['maximum_absolute_error']<=g['tolerance']/3 for g in r['scientific_gates'] if g.get('tolerance')))

    def test_generator_rows_and_rates(self):
        panel=self.D['panels'][0];_,families=exact_families(panel,self.D['meta'],self.truth)
        for f in families:
            Q=generator(f['exchange'],f['models'][0]);np.testing.assert_allclose(Q.sum(axis=1),0,atol=1e-14)
            self.assertGreater(float(np.min(Q-np.diag(np.diag(Q)))), -1e-14)

    def test_three_views_are_persistent_not_redrawn_types(self):
        a=self.D['panels'][0]['arrays']
        self.assertGreater(float(np.max(np.abs(a['moment2']-np.outer(a['moment1'],a['moment1'])))),1e-5)

    def test_two_independent_tensor_recoveries(self):
        panel=self.D['panels'][0];cfg=read_json(EXPERT/'config/parameters.yaml')
        w,A=decompose(panel['arrays'],3,cfg['tensor_contraction']);v,B=pencil_decomposition(panel['arrays'],3,cfg['tensor_contraction'])
        np.testing.assert_allclose(w,v,atol=1e-9);np.testing.assert_allclose(A,B,atol=1e-9)

    def test_distinct_kinetics_have_identical_reset_observations(self):
        panel=self.D['panels'][0];_,families=exact_families(panel,self.D['meta'],self.truth)
        f=families[0];Q0=generator(f['exchange'],f['models'][0]);Q1=generator(f['exchange'],f['models'][-1])
        self.assertGreater(float(np.max(np.abs(Q0-Q1))),1)
        np.testing.assert_allclose(observable(Q0,panel['arrays']['response'],1),observable(Q1,panel['arrays']['response'],1),atol=1e-12)
        self.assertGreater(float(np.max(np.abs(expm(Q0*.075)-expm(Q1*.075)))),.1)

    def test_alias_family_count_is_stable_and_exhaustive_in_bounds(self):
        panel=self.D['panels'][0];w,families=exact_families(panel,self.D['meta'],self.truth)
        cfg=read_json(EXPERT/'config/parameters.yaml');u,A=decompose(panel['arrays'],3,cfg['tensor_contraction'])
        fitted=compatible_family(u,A,panel['arrays'],self.D['meta'])
        for f,g in zip(families,fitted):
            self.assertEqual(len(f['models']),len(g['models']))
            np.testing.assert_allclose(f['models'],g['models'],atol=1e-7)

    def test_first_passage_matches_independent_transient_integral(self):
        Q=np.array([[-4.,3.,1.],[2.,-3.,1.],[1.,2.,-3.]])
        action={'multiplier':np.ones((3,3)).tolist(),'loss_rate':[.4,.7,.2]}
        hit,loss=first_passage(Q,action,[2],.8)
        T=Q[:2,:2]-np.diag([.4,.7]);integral=np.linalg.solve(T,expm(T*.8)-np.eye(2))
        np.testing.assert_allclose(hit[:2],integral@Q[:2,2],atol=1e-14)
        np.testing.assert_allclose(loss[:2],integral@np.array([.4,.7]),atol=1e-14)
        self.assertEqual(hit[2],1);self.assertEqual(loss[2],0)

    def test_endpoint_occupancy_differs_from_capture(self):
        Q=np.array([[-4.,3.,1.],[2.,-3.,1.],[1.,2.,-3.]])
        action={'multiplier':np.ones((3,3)).tolist(),'loss_rate':[.4,.7,.2]}
        hit,_=first_passage(Q,action,[2],.8);endpoint,_=first_passage(Q,action,[2],.8,True)
        self.assertGreater(float(np.max(hit-endpoint)),.1)

    def toy(self):
        stats=[]
        for h in range(3):
            stats.append({'flux':np.array([-1.,1.]),'d':np.array([.2+.1*h,.9-.1*h]),
                          'net':np.array([[.1+h*.02,.2-h*.01],[.6-h*.03,.1+h*.04]])})
        return stats,np.ones(3)/3,{'lower':.32,'upper':.34}

    def test_calibrated_join_matches_full_cartesian_enumeration(self):
        s,w,c=self.toy();joint=feasible_joint_indices(s,w,c)
        brute=np.array([a for a in product(range(2),repeat=3) if c['lower']<=sum(w[h]*s[h]['flux'][a[h]] for h in range(3))<=c['upper']])
        self.assertEqual({tuple(a) for a in joint},{tuple(a) for a in brute})
        self.assertEqual(len(joint),3)

    def test_independent_join_and_fractional_endpoints(self):
        s,w,c=self.toy();j=feasible_joint_indices(s,w,c);k=independent_join(s,w,c)
        self.assertEqual({tuple(a) for a in j},{tuple(a) for a in k})
        a,lo,hi=joint_bounds(s,w,'net',joint=j);b,_,_=independent_bounds(s,w,'net',joint=k)
        np.testing.assert_allclose(a,b,atol=1e-14)
        for col,row in enumerate(lo):
            value=sum(w[h]*s[h]['net'][row[h],col] for h in range(3))/sum(w[h]*s[h]['d'][row[h]] for h in range(3))
            self.assertAlmostEqual(value,a[col,0])

    def test_bulk_measurement_changes_admissible_joint_set(self):
        s,w,c=self.toy();j=feasible_joint_indices(s,w,c);self.assertLess(len(j),8)
        allj=np.array(list(product(range(2),repeat=3)));a,_,_=joint_bounds(s,w,'net',joint=j);b,_,_=joint_bounds(s,w,'net',joint=allj)
        self.assertGreater(float(np.max(np.abs(a-b))),.01)

    def test_correct_wrapper_retains_science(self):
        r=assess([self.answer],self.D,self.report);self.assertEqual(r['final_score'],95);self.assertFalse(r['failed_gates'])

    def test_numeric_strings_in_witnesses_are_recovered(self):
        a=copy.deepcopy(self.answer);a['preparations'][0]['net_witnesses']['lower'][0][0][0]=str(a['preparations'][0]['net_witnesses']['lower'][0][0][0])
        r=assess(a,self.D,self.report);self.assertEqual(r['final_score'],95);self.assertFalse(r['failed_gates'])

    def test_consistent_subtype_permutation_is_presentation_only(self):
        a=copy.deepcopy(self.answer);p=a['preparations'][0];order=[2,0,1]
        for key in ['mixture_weights','exchange_generators','forward_bounds','backward_bounds','candidate_counts']:p[key]=[p[key][i] for i in order]
        for side in ['lower','upper']:p['net_witnesses'][side]=[p['net_witnesses'][side][i] for i in order]
        r=assess(a,self.D,self.report);self.assertEqual(r['final_score'],95);self.assertFalse(r['failed_gates'])

    def test_wrong_net_endpoint_cannot_pass(self):
        a=copy.deepcopy(self.answer);a['preparations'][0]['policies'][1]['net_bounds'][0]+=.1
        r=assess(a,self.D,self.report);self.assertFalse(r['passed']);self.assertTrue(r['scientific_cap_applied'])

    def test_wrong_choice_uses_regret_not_identifier_equality(self):
        a=copy.deepcopy(self.answer);a['preparations'][0]['selected_policy']='p00'
        r=assess(a,self.D,self.report);self.assertFalse(r['passed'])

    def test_no_computed_report_only_loses_report_points(self):
        r=assess(self.answer,self.D,'All checks pass.');self.assertEqual(r['final_score'],95);self.assertFalse(r['scientific_cap_applied'])

    def test_malformed_numbers_localize_failure(self):
        for value in ['unreadable',True,float('inf'),10**400]:
            a=copy.deepcopy(self.answer);a['preparations'][0]['mixture_weights'][0]=value
            r=assess(a,self.D,self.report);self.assertFalse(r['passed']);self.assertTrue(r['scientific_cap_applied'])

    def test_duplicate_json_keys_are_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.json';p.write_text('{"a":1,"a":2}');a,findings,error=load_answer(p)
            self.assertEqual(a,{'a':2});self.assertTrue(findings);self.assertIsNone(error)

    def test_unreadable_root_is_zero(self):
        self.assertEqual(assess(None,self.D,self.report)['final_score'],0)

    def test_generated_rubric_contains_every_compared_target(self):
        for name,text in zip(['rubric.json','rubric.md'],build()):self.assertEqual((EXPERT/name).read_text(),text)
        rubric=read_json(EXPERT/'rubric.json');self.assertEqual(rubric['comparison_items'],comparison_items(self.D['meta'],self.expected))
        self.assertEqual(sum(g['points'] for g in rubric['groups'])+rubric['report_points'],100)

    def test_regenerated_expected_target_changes_comparisons(self):
        e=copy.deepcopy(self.expected);e['preparations'][0]['policies'][0]['net_bounds']=[.5,.5]
        r=assess(self.answer,self.D,self.report,expected=e)
        self.assertFalse(r['passed']);self.assertIn(e['preparations'][0]['id']+':policies.p00.net_bounds',r['failed_gates'])

    def test_exact_slots_and_required_expert_paths(self):
        slots=['run_pipeline.py','final_answer.json','analysis.md']
        for name in ['deliverables.json','required_deliverables.json']:self.assertEqual(read_json(EXPERT.parent/'task'/name),slots)
        for name in ['config/parameters.yaml','results/run_summary.json']:self.assertTrue((EXPERT/name).is_file())
        self.assertFalse(any('run_summary' in p.read_text() for p in (EXPERT.parent/'task').rglob('*') if p.is_file() and p.suffix!='.npz'))

    def test_summary_identifies_published_answer_and_inputs(self):
        summary=read_json(EXPERT/'results/run_summary.json')
        self.assertEqual(summary['answer_sha256'],hashlib.sha256((EXPERT/'final_answer.json').read_bytes()).hexdigest())
        self.assertEqual(summary['data_manifest_sha256'],hashlib.sha256((self.data/'data_manifest.json').read_bytes()).hexdigest())

    def test_single_source_has_no_local_imports_or_private_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=export(Path(tmp)/'run_pipeline.py');tree=ast.parse(code)
            imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
            self.assertFalse(imports&{'kinetics','envelopes','artifacts','expert_solution','compute_truth'})
            self.assertNotIn('private/truth',code);self.assertNotIn('expected_answer.json',code)

    def test_missing_required_summary_is_detected_before_upload(self):
        import validate_package
        original=Path.is_file
        def exists(path):return False if path==EXPERT/'results/run_summary.json' else original(path)
        with patch.object(Path,'is_file',exists):
            with self.assertRaisesRegex(AssertionError,'expert_solution/results/run_summary.json'):validate_package.validate(EXPERT.parent)


if __name__=='__main__':unittest.main()
