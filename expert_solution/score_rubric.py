"""Scientific scoring plus executable delivery coverage. Read rubric for caps and deductions."""
import json,re,math,argparse,hashlib,sys
from pathlib import Path
import numpy as np
import jsonschema
from expert_solution import load,select
from mechanism import simulate
from artifacts import input_hash,evidence
HERE=Path(__file__).resolve().parent

def strict_read(path):
 def pair(rows):
  out={}
  for k,v in rows:
   if k in out:raise ValueError('duplicate JSON key')
   out[k]=v
  return out
 def number(x):
  v=float(x)
  if not math.isfinite(v):raise ValueError('nonfinite JSON')
  return v
 def invalid(x):raise ValueError('nonfinite JSON')
 return json.loads(Path(path).read_text(),object_pairs_hook=pair,parse_float=number,parse_constant=invalid)

def normalize(raw):
 changed=False
 if isinstance(raw,list) and len(raw)==1 and isinstance(raw[0],dict):raw=raw[0];changed=True
 def recover(o,key=None):
  nonlocal changed
  if isinstance(o,dict):return {k:recover(v,k) for k,v in o.items()}
  if isinstance(o,list):return [recover(v,key) for v in o]
  if isinstance(o,str) and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',o) and key not in ['id','course','chip','scenario','case_id','schema','status']:
   v=float(o)
   if math.isfinite(v):changed=True;return int(v) if key in ['model_index','local_rank'] else v
  return o
 return recover(raw),changed

def unique(rows,key):
 result={}
 for row in rows:
  k=key(row)
  if k in result:raise ValueError('duplicate scientific ID')
  result[k]=row
 return result

def science(raw,data,reference=None):
 D=load(data);ref=reference or strict_read(HERE/'final_answer.json');a=D['model_spec']['acceptance'];rub=strict_read(HERE/'rubric.json');ans,format_issue=normalize(raw)
 schema=strict_read(Path(data)/'output_schema.json');errors=list(jsonschema.Draft202012Validator(schema).iter_errors(ans));format_issue |=bool(errors)
 checks={};details={};mapping={};rchip={c['id']:c for c in ref['chips']};chips={}
 def close(x,y,tol):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=tol
 try:
  chips=unique(ans['chips'],lambda c:c['id']);ok=set(chips)==set(rchip)
  for cid,r in rchip.items():
   c=chips[cid];models=c['models'];expected=r['models'];ok &=len(models)==len(expected);matched=set();mapping[cid]={}
   for i,p in enumerate(models):
    pp=np.asarray(p,float);dist=[bool(pp.shape==(10,) and np.all(np.abs(pp-np.asarray(q))<=a['parameter_absolute']+a['parameter_relative']*np.abs(q))) for q in expected]
    if sum(dist)!=1:ok=False;continue
    k=dist.index(True);ok &=k not in matched;matched.add(k);mapping[cid][i]=k
   ok &=len(matched)==len(expected)
   for x,y in zip(c['target_capacity_interval'],r['target_capacity_interval']):ok &=close(x,y,a['parameter_absolute']+a['parameter_relative']*abs(y))
   ok &=len(c['target_capacity_interval'])==2 and type(c['target_capacity_point_identified']) is bool and c['target_capacity_point_identified']==r['target_capacity_point_identified']
   ok &=type(c['local_rank']) is int and c['local_rank']==r['local_rank']
  checks['global_identifiability']=bool(ok)
 except (KeyError,TypeError,ValueError,OverflowError):checks['global_identifiability']=False
 try:
  ok=True;max_rmse=0.
  for cid,r in rchip.items():
   c=chips[cid];chip=next(ch for ch in D['chips'] if ch['id']==cid)
   for channel in D['model_spec']['channels']:
    for field in ['gain','kd','offset']:ok &=close(c['calibration'][channel][field],r['calibration'][channel][field],a['calibration_absolute'])
   for p in c['models']:
    bounds=np.asarray(D['model_spec']['parameter_bounds']);p=np.asarray(p,float)
    if p.shape!=(10,) or not np.isfinite(p).all() or np.any(p<bounds[:,0]) or np.any(p>bounds[:,1]):raise ValueError('parameters outside model domain')
    res=[]
    for proto in D['protocols']:
     times=sorted({o['time'] for o in chip['observations'] if o['protocol']==proto['id']});Y=simulate(p,chip['known'],proto,times,precise=True)['states']
     for t,y in zip(times,Y):
      for channel,x in [('plasma',y[1]),('tissue_total',y[2]+y[3]+y[4])]:
       s=c['calibration'][channel];obs=next(o for o in chip['observations'] if o['protocol']==proto['id'] and o['time']==t and o['channel']==channel)['signal'];z=obs-s['offset'];observed=s['kd']*z/(s['gain']-z);res.append(x-observed)
    rmse=float(np.sqrt(np.mean(np.square(res))));max_rmse=max(max_rmse,rmse);ok &=rmse<=a['fit_rmse_max'] and close(c['fit_rmse'],rmse,a['fit_rmse_max'])
  checks['measurement_fit']=bool(ok);details['max_recomputed_fit_rmse']=max_rmse
 except (KeyError,TypeError,ValueError,OverflowError,StopIteration,ZeroDivisionError):checks['measurement_fit']=False
 try:
  courses=unique(ans['courses'],lambda c:c['id']);wanted={c['id']:c for c in ref['courses']};ok=set(courses)==set(wanted);err_e=0.;err_p=0.
  for cid,r in wanted.items():
   c=courses[cid];cases=unique(c['cases'],lambda x:(x['chip'],mapping[x['chip']][x['model_index']],x['scenario']));rc=unique(r['cases'],lambda x:(x['chip'],x['model_index'],x['scenario']));ok &=set(cases)==set(rc)
   for key,x in rc.items():
    for field,tol in [('efficacy',a['efficacy_absolute']),('peak_free',a['peak_absolute'])]:
     value=cases[key][field];ok &=close(value,x[field],tol)
     if field=='efficacy':err_e=max(err_e,abs(value-x[field]))
     else:err_p=max(err_p,abs(value-x[field]))
   ok &=close(c['minimum_efficacy'],r['minimum_efficacy'],a['efficacy_absolute']) and close(c['maximum_peak_free'],r['maximum_peak_free'],a['peak_absolute'])
  checks['counterfactual_predictions']=bool(ok);details.update(max_efficacy_error=err_e,max_peak_error=err_p)
 except (KeyError,TypeError,ValueError,OverflowError):checks['counterfactual_predictions']=False
 try:
  sel=ans['selection'];raw_courses={c['id']:c for c in D['courses']};limits=D['model_spec']['decision'];safe=[c for c in ref['courses'] if c['minimum_efficacy']>=limits['efficacy_floor'] and c['maximum_peak_free']<=limits['peak_ceiling']]
  if not safe:ok=sel['status']=='no_qualifying_course' and sel['course'] is None
  else:ok=sel['status']=='selected' and sel['course'] in {c['id'] for c in safe} and raw_courses[sel['course']]['cost']<=min(raw_courses[c['id']]['cost'] for c in safe)+a['cost_slack']
  checks['course_decision']=bool(ok)
 except (KeyError,TypeError,ValueError):checks['course_decision']=False
 try:
  sel=ans['selection'];w=sel['peak_witness']
  if ref['selection']['status']=='no_qualifying_course':ok=w is None
  else:
   course=next(c for c in D['courses'] if c['id']==sel['course']);chip=next(c for c in D['chips'] if c['id']==w['chip']);scenario=next(c for c in D['scenarios'] if c['id']==w['scenario']);p=rchip[chip['id']]['models'][mapping[chip['id']][w['model_index']]];t=w['time'];Y=simulate(p,chip['known'],course,[t],scenario['multipliers'],precise=True);peak=next(c['maximum_peak_free'] for c in ref['courses'] if c['id']==course['id'])
   ok=0<=t<=course['horizon'] and close(w['value'],Y['states'][0,2],a['witness_value_absolute']) and close(w['value'],peak,a['witness_value_absolute']) and Y['mass_error']<=a['mass_balance_max']
  checks['continuous_peak_witness']=bool(ok)
 except (KeyError,TypeError,ValueError,IndexError,OverflowError,StopIteration):checks['continuous_peak_witness']=False
 rawscore=sum(rub['weights'][k] for k,v in checks.items() if v);score=min(rawscore,rub['scientific_failure_cap']) if not all(checks.values()) else rawscore
 if format_issue:score-=rub['presentation_deduction']
 return {'checks':checks,'details':details,'raw_score':rawscore,'final_score':max(0,score),'scientific_cap_applied':not all(checks.values()),'presentation_deduction':rub['presentation_deduction'] if format_issue else 0,'passed':score>=rub['pass_threshold'],'scope':'scientific_answer_only; full submission additionally requires delivery checks and isolated rerun','schema_errors':[e.message for e in errors]}

def delivery(raw,data,artifacts):
 ans,_=normalize(raw);D=load(data);out=Path(artifacts);errors=[]
 try:
  text=(out/'analysis.md').read_text();blocks=re.findall(r'```json\s*\n(.*?)\n```',text,re.S);assert len(blocks)==1
  actual=json.loads(blocks[0]);wanted=evidence(ans,D)
  def compatible(x,y,key=''):
   if isinstance(y,dict):return isinstance(x,dict) and all(k in x and compatible(x[k],v,k) for k,v in y.items())
   if isinstance(y,list):
    if key=='chip_diagnostics':
     xx=unique(x,lambda r:r['id']);yy=unique(y,lambda r:r['id']);return set(xx)==set(yy) and all(compatible(xx[k],yy[k]) for k in yy)
    if key=='limitations':return isinstance(x,list) and set(y)<=set(x)
    return isinstance(x,list) and len(x)==len(y) and all(compatible(a,b,key) for a,b in zip(x,y))
   if isinstance(y,bool):return type(x) is bool and x==y
   if isinstance(y,(int,float)):
    tolerance=D['model_spec']['acceptance']['fit_rmse_max'] if key=='fit_rmse' else D['model_spec']['acceptance']['parameter_absolute'] if key=='target_capacity_interval' else 1e-8
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=tolerance
   return x==y
  assert compatible(actual,wanted)
 except (OSError,ValueError,KeyError,TypeError,AssertionError):errors.append('analysis diagnostic evidence missing or inconsistent')
 try:
  summary=strict_read(out/'run_summary.json');jsonschema.validate(summary,strict_read(Path(data)/'run_summary_schema.json'));assert summary['input_sha256']==input_hash(data);assert summary['answer_sha256']==hashlib.sha256((out/'final_answer.json').read_bytes()).hexdigest()
 except (OSError,ValueError,KeyError,TypeError,AssertionError,jsonschema.ValidationError):errors.append('run summary invalid or hashes incorrect')
 return {'errors':errors,'deduction':min(10,5*len(errors))}

def evaluate(path,data,artifacts=None,reference=None):
 try:raw=strict_read(path);r=science(raw,data,reference)
 except (OSError,ValueError,TypeError,OverflowError) as e:return {'final_score':0,'passed':False,'automatic_zero':str(e)}
 if artifacts:
  d=delivery(raw,data,artifacts);r['delivery']=d;r['final_score']=max(0,r['final_score']-d['deduction']);r['passed']=r['final_score']>=80
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--answer',type=Path,required=True);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--artifacts-dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=evaluate(a.answer,a.data,a.artifacts_dir);s=json.dumps(r,indent=2,allow_nan=False)+'\n'
 if a.output:a.output.write_text(s)
 print(s);sys.exit(0 if r['passed'] else 1)
