import json,copy
from pathlib import Path

def stable(answer):
 if isinstance(answer,dict):return {k:stable(v) for k,v in answer.items()}
 if isinstance(answer,list):return [stable(v) for v in answer]
 if isinstance(answer,float):
  value=round(answer,5);return 0.0 if value==0 else value
 return answer

def evidence(a,D):
 selected=a['selection']['policy'];row=next((r for r in a['global_policies'] if r['id']==selected),None)
 return {'case_id':a['case_id'],'selected_policy':selected,'selected_policy_metrics':row,'decision_limits':D['study_metadata']['decision'],'interval_interpretation':'sharp_bounds_over_compatible_causal_models','context_diagnostics':[{'id':c['id'],'point_identified_policy_count':sum(r['point_identified'] for r in c['policies']),'largest_net_gain_width':max(r['net_gain_upper']-r['net_gain_lower'] for r in c['policies'])} for c in a['contexts']]}

def write_outputs(a,D,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);a=stable(a)
 (out/'final_answer.json').write_text(json.dumps(a,indent=2,allow_nan=False)+'\n')
 (out/'analysis.md').write_text('# Paired-clone policy analysis\n\n```json\n'+json.dumps(evidence(a,D),indent=2)+'\n```\n\nThe compatible family preserves the same latent clone and instrument variables across potential worlds. Survival-conditioned target comparisons retain their joint conditioning event. The intervals are population-limit causal bounds under the stipulated model and measurement bands. They are not sampling confidence intervals or clinical findings.\n')
