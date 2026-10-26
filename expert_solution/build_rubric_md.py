"""Generate an explicit numerical rubric from public contracts and exact targets."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def comparison_items(meta,expected):
    tol = meta['tolerances']; items=[]
    mapping = [('mixture_weights','mixture','identification'), ('exchange_generators','exchange','identification'),
               ('forward_bounds','cycle_bounds','identification'), ('backward_bounds','cycle_bounds','identification'),
               ('candidate_counts',None,'identification'), ('retention_bounds','retention','identification'),
               ('retained_epr_bounds','epr','retained_entropy')]
    for prep in expected['preparations']:
        pid=prep['id']
        for key,tkey,group in mapping:
            items.append(dict(preparation=pid,group=group,path=key,kind='exact' if tkey is None else 'numeric',
                              expected=prep[key],absolute_tolerance=0 if tkey is None else tol[tkey]))
        for policy in prep['policies']:
            for key in ['success','loss','cost','gain','net']:
                tkey='probability_bounds' if key in ['success','loss','cost'] else key+'_bounds'
                group='policy_probabilities' if key in ['success','loss','cost'] else 'joint_gain_and_net'
                items.append(dict(preparation=pid,group=group,path='policies.'+policy['id']+'.'+key+'_bounds',kind='numeric',
                                  expected=policy[key+'_bounds'],absolute_tolerance=tol[tkey]))
        best=max(p['net_bounds'][0] for p in prep['policies'])
        allowed=[p['id'] for p in prep['policies'] if best-p['net_bounds'][0] <= tol['choice_regret']]
        items.append(dict(preparation=pid,group='robust_choice',path='selected_policy',kind='allowed_set',expected=allowed,
                          decision_regret_tolerance=tol['choice_regret']))
    return items


def build():
    data = HERE.parent/'task/data'
    meta = json.loads((data/'study_metadata.json').read_text())
    contract = json.loads((data/'grading_contract.json').read_text())
    expected = json.loads((HERE/'private/expected_answer.json').read_text())
    items=comparison_items(meta,expected)
    tol=meta['tolerances']
    rubric=dict(contract,rubric_version='1.0',numeric_tolerance=.0001,preparation_ids=[p['id'] for p in meta['preparations']],
                tolerances=tol,report_tolerances=meta['report_tolerances'],comparison_items=items,
                dynamic_witness_checks={'field':'net_witnesses','group':'attaining_witnesses',
                  'requirements':'Both physical witnesses snap uniquely within witness_rates to locally compatible models; their common preparation satisfies bulk turnover within witness_turnover and selected net endpoint within witness_endpoint. Any attaining witness is accepted.',
                  'prompt_section':'Answer structure and attaining witnesses'},
                target_source='private/expected_answer.json, computed from exact simulation invariants; inference uses only task inputs',
                canonical_answer_sha256=hashlib.sha256((HERE/'final_answer.json').read_bytes()).hexdigest(),
                expected_answer_sha256=hashlib.sha256((HERE/'private/expected_answer.json').read_bytes()).hexdigest(),
                required_deliverables=json.loads((HERE.parent/'task/deliverables.json').read_text()))
    js=json.dumps(rubric,indent=2)+'\n'
    text='# Persistent-cycle intervention rubric\n\nGenerated from `rubric.json`, public metadata, and exact simulation-derived targets.\n\n'
    text+=str(len(meta['preparations']))+' preparations; '+str(len(meta['policies']))+' policies per preparation. Every scientific requirement is mandatory.\n\n'
    text+='| Group | Package points | Fields |\n|---|---:|---|\n'
    for group in contract['groups']:text+='|'+group['id']+'|'+str(group['points'])+'|'+', '.join(group['fields'])+'|\n'
    text+='\nEach group is divided equally across preparations and earns credit when all its requirements pass. The calculated report earns '+str(contract['report_points'])+' further points.\n\n'
    text+='A scientific failure caps the score at '+str(contract['scientific_gate_cap'])+'. Passing is '+str(contract['pass_threshold'])+' or greater. Recoverable presentation deviations cost '+str(contract['presentation_deduction'])+' once after any cap and never activate a scientific cap.\n\n'
    text+='| Quantity | Absolute tolerance |\n|---|---:|\n'
    for k,v in tol.items():text+='|'+k+'|'+str(v)+'|\n'
    text+='\n`comparison_items` contains every fixed expected value, field path, group and tolerance. Policy choices are accepted from computed regret sets, rather than one canonical identifier. Witnesses are checked physically and may differ from the canonical witnesses. Candidate counts are exact integers.\n\n'
    text+='The report evidence is recomputed from submitted physical rates and public arrays. Artifact grading does not establish execution. The isolated verifier runs original and regenerated experiments with private files inaccessible. Missing/non-running code, unreadable answers, or demonstrated stored/external answers receive zero; infrastructure failures are BLOCKED.\n'
    return js,text


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,text in zip(['rubric.json','rubric.md'],build()):
        if a.check:assert (HERE/name).read_text()==text,name+' is stale'
        else:(HERE/name).write_text(text)
