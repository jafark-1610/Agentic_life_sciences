"""Generate both rubric representations from staged facts and predictions."""
import argparse
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
from model import read_json
HERE = Path(__file__).resolve().parent


def build():
    data = HERE.parent/'task/data'
    meta = read_json(data/'study_metadata.json')
    answer = read_json(HERE/'final_answer.json')
    contract = read_json(data/'grading_contract.json')
    assert {p['id'] for p in answer['proteins']} == {p['id'] for p in meta['proteins']}
    for p in answer['proteins']:
        assert len(p['energy']) == len(p['apo_folded']) == len(p['challenge_a']) == meta['n_variants']
    rubric = dict(contract, rubric_version='1.0', acceptance_thresholds=meta['acceptance_thresholds'],
                  report_tolerances=meta['report_tolerances'], numeric_tolerance=0.0001,
                  numeric_tolerance_role='serialization comparison only; scientific tolerances are the six named thresholds',
                  binder_ids=[p['id'] for p in meta['proteins']], variant_count=meta['n_variants'],
                  screen_variant_count=meta['n_screen'], energy_columns=meta['energy_columns'],
                  screen_condition_count=len(meta['screen_conditions']), challenge_condition_count=len(meta['challenge_conditions']),
                  canonical_answer_sha256=hashlib.sha256((HERE/'final_answer.json').read_bytes()).hexdigest(),
                  solver_slots=read_json(HERE.parent/'task/deliverables.json'),
                  grading_scope='Hidden simulation truth for scientific metrics; report evidence recomputed from submitted arrays',
                  execution_scope='Artifact grader cannot establish execution. Full verification requires isolated base and regenerated runs.')
    js = json.dumps(rubric, indent=2)+'\n'
    text = '# Thermodynamic protein design rubric\n\nGenerated from `rubric.json`, the public contract, metadata, and canonical answer.\n\n'
    text += ('The answer covers '+str(len(rubric['binder_ids']))+' binders and '+str(rubric['variant_count'])+
             ' variants per binder, with '+str(rubric['screen_variant_count'])+' measured variants, '+
             str(rubric['screen_condition_count'])+' screen conditions, and '+str(rubric['challenge_condition_count'])+
             ' competitive challenges. Arrays follow the staged variant order.\n\n')
    text += ('Each scientific group is divided equally among binders. Every validity and accuracy requirement is mandatory. '
             'An invalid binder block earns no scientific credit for that binder. Any failed scientific gate caps the score at '+
             str(rubric['scientific_gate_cap'])+'. Passing requires '+str(rubric['pass_threshold'])+' points, inclusive.\n\n')
    text += '| Metric | Answer field | Package points | Maximum error |\n|---|---|---:|---:|\n'
    for g in rubric['groups']:
        text += '|'+g['metric']+'|`'+g['field']+'`|'+str(g['points'])+'|'+str(rubric['acceptance_thresholds'][g['threshold']])+'|\n'
    text += ('\nError definitions and utility are in the public prompt. The private simulation coefficients generate the scoring truth. '
             'A selection within the regret limit receives full decision credit, regardless of tie order or estimator.\n\n')
    text += ('The '+str(rubric['report_points'])+' report points require the complete calculated JSON evidence block. '
             'An absent or inconsistent block withholds those points and never activates the scientific cap.\n\n')
    text += '| Computed report field | Absolute comparison tolerance |\n|---|---:|\n'
    for k, v in rubric['report_tolerances'].items(): text += '|'+k+'|'+str(v)+'|\n'
    text += ('\nRecoverable presentation deviations listed in the public Execution section cost '+str(rubric['presentation_deduction'])+
             ' points once, after any scientific cap. They never activate the cap. Missing or unreadable answers and missing or '
             'non-running pipelines receive zero. Stored answers and external evidence require documented isolated-execution evidence.\n\n')
    text += ('Artifact grading establishes numerical results only. `verify_submission.py` executes the single source file against the '
             'published and regenerated inputs with private files inaccessible. Infrastructure failures are blocked checks, not model failures. '
             'The generic numeric comparison tolerance is '+str(rubric['numeric_tolerance'])+
             '; the named scientific limits above are the authoritative accuracy gates.\n\n')
    text += 'Canonical answer SHA-256: `'+rubric['canonical_answer_sha256']+'`.\n'
    return js, text


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    for name, text in zip(['rubric.json', 'rubric.md'], build()):
        if a.check: assert (HERE/name).read_text() == text, name+' is stale'
        else: (HERE/name).write_text(text)
