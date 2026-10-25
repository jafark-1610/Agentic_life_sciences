import json,hashlib,time
from pathlib import Path
from mechanism import simulate

def stable_answer(answer,D=None):
 """Serialize computed results reproducibly; never use stored answer values.

 Eight decimal places retain much more precision than the scientific gates.
 A peak-time coordinate is only a witness, so the oracle uses a millihour
 coordinate and recomputes the physical value there. Solver answers need not
 follow this serialization policy.
 """
 def rounded(value,path=()):
  if isinstance(value,dict):return {k:rounded(v,path+(k,)) for k,v in value.items()}
  if isinstance(value,list):return [rounded(v,path+(i,)) for i,v in enumerate(value)]
  if isinstance(value,float):
   decimals=3 if path==('selection','peak_witness','time') else 8
   result=round(value,decimals)
   return 0.0 if result==0 else result
  return value
 result=rounded(answer)
 if D is not None and result['selection']['status']=='selected':
  selection=result['selection'];w=selection['peak_witness']
  chip=next(c for c in D['chips'] if c['id']==w['chip'])
  fitted=next(c for c in result['chips'] if c['id']==w['chip'])
  course=next(c for c in D['courses'] if c['id']==selection['course'])
  scenario=next(s for s in D['scenarios'] if s['id']==w['scenario'])
  evaluated=simulate(fitted['models'][w['model_index']],chip['known'],course,[w['time']],scenario['multipliers'],precise=True)
  w['value']=round(float(evaluated['states'][0,2]),8)
 return result

def input_hash(data):
 d=Path(data);manifest=json.loads((d/'data_manifest.json').read_text())
 hashes={f:hashlib.sha256((d/f).read_bytes()).hexdigest() for f in manifest['files']}
 return hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def add_witness(answer,D):
 s=answer['selection'];s['peak_witness']=None
 if s['status']!='selected':return
 course=next(c for c in D['courses'] if c['id']==s['course']);row=next(c for c in answer['courses'] if c['id']==s['course']);case=max(row['cases'],key=lambda c:c['peak_free']);chip=next(c for c in D['chips'] if c['id']==case['chip']);fit=next(c for c in answer['chips'] if c['id']==chip['id']);scenario=next(c for c in D['scenarios'] if c['id']==case['scenario'])
 sim=simulate(fit['models'][case['model_index']],chip['known'],course,scenario=scenario['multipliers'],precise=True)
 s['peak_witness']={'chip':chip['id'],'model_index':case['model_index'],'scenario':scenario['id'],'time':sim['peak_time'],'value':sim['peak_free']}

def evidence(answer,D):
 return {'case_id':answer['case_id'],'chip_diagnostics':[{k:c[k] for k in ['id','fit_rmse','local_rank','target_capacity_interval','target_capacity_point_identified']} for c in answer['chips']],'selection':answer['selection'],'decision_limits':D['model_spec']['decision'],'limitations':['synthetic_reduced_system','rounded_deterministic_signals','counterfactuals_depend_on_model']}

def write_outputs(answer,D,data,out,elapsed):
 answer=stable_answer(answer,D)
 out=Path(out);out.mkdir(parents=True,exist_ok=True);raw=(json.dumps(answer,indent=2,allow_nan=False)+'\n').encode();(out/'final_answer.json').write_bytes(raw)
 report='# Computed disposition and course diagnostics\n\n```json\n'+json.dumps(evidence(answer,D),indent=2)+'\n```\n\nThe parameter solutions describe chemical-site identities without imposing a rate ordering. Counterfactuals cover every returned solution and specified scenario. Continuous free-tissue peaks are optimized between input events. The model is synthetic and is not a clinical dosing recommendation.\n'
 (out/'analysis.md').write_text(report)
 summary={'case_id':answer['case_id'],'status':'success','input_sha256':input_hash(data),'answer_sha256':hashlib.sha256(raw).hexdigest(),'elapsed_seconds':elapsed}
 (out/'run_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
