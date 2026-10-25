import json,re,math,argparse,sys
from pathlib import Path
import jsonschema
from expert_solution import load
from artifacts import evidence
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
  if not math.isfinite(v):raise ValueError('nonfinite JSON number')
  return v
 def invalid(x):raise ValueError('nonfinite JSON number')
 return json.loads(Path(path).read_text(),object_pairs_hook=pair,parse_float=number,parse_constant=invalid)

def normalize(raw):
 changed=False
 if isinstance(raw,list) and len(raw)==1 and isinstance(raw[0],dict):raw=raw[0];changed=True
 def convert(v,key=None):
  nonlocal changed
  if isinstance(v,dict):return {k:convert(x,k) for k,x in v.items()}
  if isinstance(v,list):return [convert(x,key) for x in v]
  if isinstance(v,str) and key not in ['id','case_id','schema','policy','status'] and re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',v):
   x=float(v)
   if math.isfinite(x):changed=True;return x
  return v
 return convert(raw),changed

def keyed(rows):
 out={}
 for row in rows:
  if row['id'] in out:raise ValueError('duplicate ID')
  out[row['id']]=row
 return out

def science(raw,data,reference=None):
 D=load(data);a=D['study_metadata']['acceptance'];tol=a['numeric_absolute'];ref=reference or strict_read(HERE/'final_answer.json');rub=strict_read(HERE/'rubric.json');answer,presentation=normalize(raw)
 errors=list(jsonschema.Draft202012Validator(strict_read(Path(data)/'output_schema.json')).iter_errors(answer));presentation|=bool(errors);checks={};details={}
 def close(x,y):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=tol
 try:
  cs=keyed(answer['contexts']);rc=keyed(ref['contexts']);ok=set(cs)==set(rc);maxerr=0.
  for cid,r in rc.items():
   actual=keyed(cs[cid]['policies']);expected=keyed(r['policies']);ok &=set(actual)==set(expected)
   for pid,p in expected.items():
    for k in ['eligibility_lower','eligibility_upper','net_gain_lower','net_gain_upper','harm_upper','cost_upper']:
     x=actual[pid][k];ok &=close(x,p[k]);maxerr=max(maxerr,abs(x-p[k]))
  checks['sharp_bounds']=bool(ok);details['max_bound_error']=maxerr
 except (KeyError,TypeError,ValueError,OverflowError):checks['sharp_bounds']=False
 try:
  ok=True
  for cid,r in rc.items():
   actual=keyed(cs[cid]['policies'])
   for p in r['policies']:
    v=actual[p['id']]['point_identified'];ok &=type(v) is bool and v==p['point_identified']
  checks['identification']=bool(ok)
 except (KeyError,TypeError,ValueError,UnboundLocalError):checks['identification']=False
 try:
  global_=keyed(answer['global_policies']);rg=keyed(ref['global_policies']);ok=set(global_)==set(rg)
  for pid,r in rg.items():
   for k in ['worst_net_gain','worst_harm','worst_cost','minimum_eligibility']:ok &=close(global_[pid][k],r[k])
   x=global_[pid]['resource_adjusted_score'];ok &=isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-r['resource_adjusted_score'])<=a['policy_score_absolute']
  checks['global_envelopes']=bool(ok)
 except (KeyError,TypeError,ValueError):checks['global_envelopes']=False
 try:
  limits=D['study_metadata']['decision'];eligible=[p for p in ref['global_policies'] if p['worst_harm']<=limits['maximum_harm'] and p['worst_cost']<=limits['maximum_cost'] and p['minimum_eligibility']>=limits['minimum_eligibility']];s=answer['selection']
  if not eligible:ok=s['status']=='no_qualifying_policy' and s['policy'] is None
  else:
   best=max(p['resource_adjusted_score'] for p in eligible);valid={p['id'] for p in eligible if p['resource_adjusted_score']>=best-a['decision_slack']};ok=s['status']=='selected' and s['policy'] in valid
  checks['policy_decision']=bool(ok)
 except (KeyError,TypeError,ValueError):checks['policy_decision']=False
 rawscore=sum(rub['weights'][k] for k,v in checks.items() if v);capped=not all(checks.values());score=min(rawscore,rub['scientific_failure_cap']) if capped else rawscore
 if presentation:score-=rub['presentation_deduction']
 return {'role':'scientific_answer_evaluation','checks':checks,'details':details,'raw_score':rawscore,'scientific_cap_applied':capped,'presentation_deduction':rub['presentation_deduction'] if presentation else 0,'final_score':max(0,score),'passed':score>=rub['pass_threshold'],'scope':'Complete submission also requires actual isolated input-dependent execution.','schema_errors':[e.message for e in errors]}

def delivery(raw,data,folder):
 answer,_=normalize(raw);D=load(data);errors=[]
 try:
  text=(Path(folder)/'analysis.md').read_text();blocks=re.findall(r'```json\s*\n(.*?)\n```',text,re.S);assert len(blocks)==1;got=json.loads(blocks[0]);want=evidence(answer,D)
  def eq(x,y,key=''):
   if isinstance(y,dict):return isinstance(x,dict) and all(k in x and eq(x[k],v,k) for k,v in y.items())
   if isinstance(y,list):
    if key=='context_diagnostics':
     xx=keyed(x);yy=keyed(y);return set(xx)==set(yy) and all(eq(xx[k],yy[k]) for k in yy)
    return isinstance(x,list) and len(x)==len(y) and all(eq(xx,yy,key) for xx,yy in zip(x,y))
   if isinstance(y,bool):return type(x) is bool and x==y
   if isinstance(y,(int,float)):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=D['study_metadata']['acceptance']['numeric_absolute']
   return x==y
  assert eq(got,want)
 except (OSError,KeyError,TypeError,ValueError,AssertionError):errors.append('Required analysis diagnostic block missing or inconsistent')
 return {'errors':errors,'deduction':5 if errors else 0}

def evaluate(path,data,artifacts=None,reference=None):
 try:raw=strict_read(path);r=science(raw,data,reference)
 except (OSError,ValueError,TypeError,OverflowError) as e:return {'final_score':0,'passed':False,'automatic_zero':str(e)}
 if artifacts:
  d=delivery(raw,data,artifacts);r['delivery']=d;r['final_score']=max(0,r['final_score']-d['deduction']);r['passed']=r['final_score']>=80
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--answer',type=Path,required=True);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--artifacts-dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=evaluate(a.answer,a.data,a.artifacts_dir);text=json.dumps(r,indent=2,allow_nan=False)+'\n'
 if a.output:a.output.write_text(text)
 print(text);sys.exit(0 if r['passed'] else 1)
