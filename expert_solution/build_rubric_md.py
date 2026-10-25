"""Generate both rubric views from published tolerances and computed answer dimensions."""
from pathlib import Path
import json,argparse
HERE=Path(__file__).resolve().parent

def build():
 meta=json.loads((HERE.parent/'task/data/study_metadata.json').read_text());ref=json.loads((HERE/'final_answer.json').read_text());a=meta['acceptance']
 spec={'case_id':meta['case_id'],'version':'1.0','weights':{'robust_selection':55,'utility_envelopes':20,'flux_ranges':15,'adversarial_witness':10},'pass_threshold':80,'scientific_failure_cap':79,'presentation_deduction':5,'automatic_zero':['answer missing, unreadable, duplicate-key or nonfinite JSON'],'acceptance':a,'counts':{'cultures':len(ref['cultures']),'reactions_per_culture':len(ref['cultures'][0]['flux_ranges']),'feasible_designs':len(ref['designs'])},'field_contract':{'robust_selection':'prompt.md: Decision and Deliverables selection','utility_envelopes':'prompt.md: Deliverables designs','flux_ranges':'prompt.md: Deliverables cultures','adversarial_witness':'prompt.md: Adversarial witness'},'policy':'All comparisons use supplied public inputs and computed reference. No method requirement. All scientific groups are gates. Any failed scientific group caps at 79. Presentation-only schema errors deduct 5 once, never activate cap. Arrays are matched by IDs or sorted module tuples. Malformed/missing numerical entries fail their group. Each group is all-or-nothing. Code provenance and offline execution are separately reviewed, not inferred from text or automatically scored. No other caps or deductions.'}
 md=['# Rubric','',f"Case: {spec['case_id']}",'','| Scientific group | Points | Required behavior |','|---|---:|---|','| robust_selection | 55 | Safe minimax-regret design within published selection slack, or correct no-rescue status |','| utility_envelopes | 20 | Every culture and global floor and regret within numeric tolerance |','| flux_ranges | 15 | Every feasible flux endpoint and width-based identifiability flag correct |','| adversarial_witness | 10 | Feasible shared state and legal challenger attain selected global regret |','',spec['policy'],'',f"Pass threshold: {spec['pass_threshold']} inclusive. Automatic zero: "+'; '.join(spec['automatic_zero'])+'.','', '## Published tolerances','```json',json.dumps(a,indent=2),'```','','## Dataset dimensions','```json',json.dumps(spec['counts'],indent=2),'```','','## Graded field contract','```json',json.dumps(spec['field_contract'],indent=2),'```','']
 return json.dumps(spec,indent=2)+'\n','\n'.join(md)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
 for name,text in zip(['rubric.json','rubric.md'],build()):
  if a.check:assert (HERE/name).read_text()==text,name+' stale'
  else:(HERE/name).write_text(text)
