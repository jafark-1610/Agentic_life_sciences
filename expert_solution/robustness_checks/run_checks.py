"""Scientific margins, independent inference, symmetry, and weaker-estimator controls."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent; EXPERT = HERE.parent
sys.path.insert(0, str(EXPERT)); sys.path.insert(0, str(EXPERT/'tests'))
import argparse
import copy
import json
import tempfile
import numpy as np
from scipy.special import expit
from model import load_data, read_json, features, slope, occupancy, evidence
from score_rubric import assess
from artifacts import write_outputs
from baselines import two_stage


def run(independent_dir=None):
    data = EXPERT.parent/'task/data'; D = load_data(data); D['data_dir'] = str(data)
    answer = read_json(EXPERT/'final_answer.json'); report = (EXPERT/'analysis.md').read_text()
    grade = assess(answer, D, report); checks = []
    def record(name, passed, details): checks.append(dict(name=name, passed=bool(passed), details=details))
    ratios = [g['value']/g['threshold'] for g in grade['scientific_gates'] if g['threshold']]
    record('expert_scientific_gate_clearance', grade['passed'] and max(ratios) <= 1/3,
           {'max_error_to_limit_ratio': max(ratios), 'score': grade['final_score']})
    # Full physical family has a binding-equivalent reflection at zero denaturant offset.
    X = features(D['bits']); truth = read_json(EXPERT/'private/truth.json')
    symmetry, apo_gaps = [], []
    for p in D['meta']['proteins']:
        en = X@np.asarray(truth['proteins'][p['id']]['coefficients']).T
        transformed = np.column_stack([-en[:, 0], en[:, 1]+en[:, 0], en[:, 2]+en[:, 0]])
        co = [c for c in D['meta']['screen_conditions'] if c['urea'] == 0]
        original = occupancy(en, slope(D['bits'], p), co)[:2]
        changed = occupancy(transformed, slope(D['bits'], p), co)[:2]
        symmetry.append(max(float(np.max(np.abs(a-b))) for a, b in zip(original, changed)))
        apo_gaps.append(float(np.sqrt(np.mean((expit(-en[:, 0])-expit(en[:, 0]))**2))))
    record('binding_fit_alone_does_not_identify_apo_folding', max(symmetry) < 1e-12 and min(apo_gaps) > .2,
           {'maximum_zero_offset_occupancy_difference': max(symmetry), 'minimum_apo_rmse_between_reflections': min(apo_gaps),
            'scope': 'A baseline-offset-only mathematical control. Additional supplied denaturation measurements distinguish the states; no claim that both fit the full task.'})
    baseline, fits = two_stage(D)
    with tempfile.TemporaryDirectory() as tmp:
        write_outputs(baseline, D, tmp, 'Per-variant denaturation profiles are estimated first and then projected onto quadratic sequence energies by ordinary least squares.')
        bad = assess(baseline, D, (Path(tmp)/'analysis.md').read_text())
    record('two_stage_latent_estimation_control', not bad['passed'],
           {'score': bad['final_score'], 'failed_gates': bad['failed_gates'], 'per_variant_fits_before_sequence_projection': fits,
            'interpretation': 'Individual measured-variant fits can look adequate while extrapolated sequence landscapes fail. These fit diagnostics precede sequence projection; they are not claims about the final projected capture residual.'})
    wrapped = assess([answer], D, report)
    record('correct_science_presentation_recovery', wrapped['passed'] and wrapped['final_score'] == 95 and not wrapped['failed_gates'],
           {'score': wrapped['final_score']})
    fabricated = report.replace('capture_deviance_per_observation', 'uncomputed_claim')
    fabricated_grade = assess(answer, D, fabricated)
    record('computed_report_evidence_enforcement', fabricated_grade['final_score'] == 95 and not fabricated_grade['failed_gates'],
           {'score': fabricated_grade['final_score'], 'report_points': fabricated_grade['report_points']})
    if independent_dir:
        alt = read_json(Path(independent_dir)/'final_answer.json')
        alt_report = (Path(independent_dir)/'analysis.md').read_text()
    else:
        from independent_oracle import infer
        alt, _ = infer(data)
        with tempfile.TemporaryDirectory() as tmp:
            write_outputs(alt, D, tmp, 'Independent weighted apparent-energy least squares with endpoint calibration.')
            alt_report = (Path(tmp)/'analysis.md').read_text()
    independent_grade = assess(alt, D, alt_report)
    record('independent_correct_estimator', independent_grade['passed'],
           {'score': independent_grade['final_score'], 'failed_gates': independent_grade['failed_gates'],
            'method': 'Independent feature order, endpoint calibration, transformed-energy criterion, Levenberg-Marquardt, direct state arithmetic'})
    record('three_solver_slots_and_expert_metadata',
           read_json(EXPERT.parent/'task/deliverables.json') == ['run_pipeline.py', 'final_answer.json', 'analysis.md'] and
           (EXPERT/'config/parameters.yaml').is_file() and (EXPERT/'results/run_summary.json').is_file(),
           {'slots': read_json(EXPERT.parent/'task/deliverables.json'), 'expert_summary_present': (EXPERT/'results/run_summary.json').is_file()})
    result = dict(case_id=D['meta']['case_id'], status='success' if all(c['passed'] for c in checks) else 'fail',
                  checks=checks, model_evaluation='not performed by these scientific controls; fresh external runs required')
    (HERE/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    text = '# Scientific robustness checks\n\nThese are deterministic scientific controls, not Meta Muse model attempts.\n\n'
    text += '| Check | Passed |\n|---|---|\n'+''.join('|'+c['name']+'|'+str(c['passed'])+'|\n' for c in checks)
    (HERE/'result.md').write_text(text)
    print(json.dumps({'status': result['status'], 'checks': len(checks)}))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--independent-output', type=Path); a = p.parse_args()
    sys.exit(0 if run(a.independent_output)['status'] == 'success' else 1)
