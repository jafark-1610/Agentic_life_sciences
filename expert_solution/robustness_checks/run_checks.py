"""Score scientific controls, verify exact fitting, and audit model-class relaxations."""
import os
import sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXPERT=HERE.parent
sys.path.insert(0,str(EXPERT))
import argparse
import json
import tempfile
import numpy as np
from kinetics import read_json,load_data,candidate_statistics
from expert_solution import analyse
from artifacts import write_outputs,evidence
from score_rubric import assess
from compute_truth import exact_families
from envelopes import feasible_joint_indices,joint_bounds
from controls import single_compatible_model,separate_endpoint_extrema,convexified_endpoint


def run(independent_output=None):
    data=EXPERT.parent/'task/data';config=read_json(EXPERT/'config/parameters.yaml');D=load_data(data)
    expected=read_json(EXPERT/'private/expected_answer.json');truth=read_json(EXPERT/'private/truth.json')
    answer=read_json(EXPERT/'final_answer.json');report=(EXPERT/'analysis.md').read_text();checks=[]
    def record(name,passed,details):checks.append(dict(name=name,passed=bool(passed),details=details))
    grade=assess(answer,D,report)
    ratios=[g['maximum_absolute_error']/g['tolerance'] for g in grade['scientific_gates'] if g.get('tolerance')]
    record('expert_gate_clearance',grade['passed'] and max(ratios)<1/3,{'score':grade['final_score'],'maximum_error_to_tolerance_ratio':max(ratios)})
    override=lambda panel,meta:exact_families(panel,meta,truth)
    with tempfile.TemporaryDirectory() as tmp:
        point,_,_=analyse(data,config,bound_function=single_compatible_model,family_override=override)
        write_outputs(point,D,tmp,'A single exactly fitting, bulk-compatible preparation model is retained using minimum dissipation regularization. The resulting prediction is used as a plug-in estimate.')
        point_grade=assess(point,D,(Path(tmp)/'analysis.md').read_text());ev=evidence(point,D)
        errors=max(max(p['moment2_max_abs_error'],p['moment3_max_abs_error']) for p in ev)
        regs=[]
        by_expected={p['id']:p for p in expected['preparations']}
        for p in point['preparations']:
            e=by_expected[p['id']];net={q['id']:q['net_bounds'][0] for q in e['policies']}
            regs.append(max(net.values())-net[p['selected_policy']])
        witness_data=[g for g in point_grade['scientific_gates'] if g['field']=='net_witnesses']
        calibration_fit=all(panel['protocol']['bulk_turnover']['lower']-1e-9<=g['details']['lower']['turnover']<=panel['protocol']['bulk_turnover']['upper']+1e-9 for panel,g in zip(D['panels'],witness_data))
        record('exactly_fitting_single_model_fails_science',not point_grade['passed'] and errors<1e-9 and calibration_fit,
               {'score':point_grade['final_score'],'maximum_reset_moment_error':errors,'all_bulk_intervals_satisfied':calibration_fit,
                'true_robust_choice_regrets':regs,'maximum_choice_regret':max(regs),'failed_gate_count':len(point_grade['failed_gates'])})
    # Same-model differences must be optimized together.
    penalties={(p['protocol']['loss_penalty'],p['protocol']['resource_penalty']) for p in D['panels']};assert len(penalties)==1
    separate_endpoint_extrema.loss_penalty,separate_endpoint_extrema.resource_penalty=next(iter(penalties))
    with tempfile.TemporaryDirectory() as tmp:
        outer,_,_=analyse(data,config,bound_function=separate_endpoint_extrema,family_override=override)
        write_outputs(outer,D,tmp,'Independent extrema of success, benchmark success, loss, and resource are combined as outer bounds.')
        outer_grade=assess(outer,D,(Path(tmp)/'analysis.md').read_text())
        record('outer_bounds_do_not_receive_sharpness_credit',not outer_grade['passed'],{'score':outer_grade['final_score'],'failed_gate_count':len(outer_grade['failed_gates'])})
    with tempfile.TemporaryDirectory() as tmp:
        endpoint,_,_=analyse(data,config,endpoint=True,family_override=override)
        write_outputs(endpoint,D,tmp,'Follow-up success is approximated by endpoint occupancy instead of competing first passage.')
        endpoint_grade=assess(endpoint,D,(Path(tmp)/'analysis.md').read_text())
        record('endpoint_occupancy_is_not_first_passage',not endpoint_grade['passed'],{'score':endpoint_grade['final_score'],'failed_gate_count':len(endpoint_grade['failed_gates'])})
    if independent_output:
        alt=read_json(Path(independent_output)/'final_answer.json');alt_report=(Path(independent_output)/'analysis.md').read_text()
        alt_grade=assess(alt,D,alt_report)
        record('independent_pencil_and_joint_enumeration',alt_grade['passed'],{'score':alt_grade['final_score'],'failed_gate_count':len(alt_grade['failed_gates'])})
    else:record('independent_pencil_and_joint_enumeration',False,{'status':'not supplied; run tests/independent_oracle.py first'})
    # An LP that allows mixtures of microscopic aliases changes the stipulated three-subtype class.
    panel=D['panels'][0];weights,families=exact_families(panel,D['meta'],truth)
    stats=[candidate_statistics(f,panel['protocol'],D['meta']['policies']) for f in families]
    joint=feasible_joint_indices(stats,weights,panel['protocol']['bulk_turnover'])
    true_net,_,_=joint_bounds(stats,weights,'net',joint=joint)
    selected=int(np.argmax(true_net[:,0]));lp,active=convexified_endpoint(stats,weights,panel['protocol']['bulk_turnover'],'net',selected,True)
    record('convexification_audit',lp<=true_net[selected,0]+1e-8,{'integer_lower_net':float(true_net[selected,0]),'relaxed_lower_net':lp,'gap':float(true_net[selected,0]-lp),'active_microscopic_models_per_subtype':active,
      'interpretation':'Relaxing one generator per physical subtype to a mixture enlarges the admissible class. This audit does not require the gap to exceed a scientific tolerance and is not counted as model difficulty evidence.'})
    wrapped=assess([answer],D,report)
    record('correct_science_format_recovery',wrapped['passed'] and wrapped['final_score']==95 and not wrapped['failed_gates'],{'score':wrapped['final_score']})
    fake=assess(answer,D,'Every value is correct.')
    record('uncomputed_report_withholds_only_report_credit',fake['final_score']==95 and not fake['failed_gates'],{'score':fake['final_score']})
    result=dict(case_id=D['meta']['case_id'],status='success' if all(c['passed'] for c in checks) else 'fail',checks=checks,
                qualification='Scientific controls are not Meta Muse attempts. External model qualification remains unverified.')
    (HERE/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (HERE/'result.md').write_text('# Scientific control results\n\n| Check | Passed |\n|---|---|\n'+''.join('|'+c['name']+'|'+str(c['passed'])+'|\n' for c in checks))
    print(json.dumps({'status':result['status'],'checks':len(checks)}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--independent-output',type=Path);a=p.parse_args();sys.exit(0 if run(a.independent_output)['status']=='success' else 1)
