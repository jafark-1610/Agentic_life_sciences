"""Grade numerical science and a feasible adversarial witness. No text claims are proof."""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
import jsonschema
from expert_solution import load,polytope,utility,portfolios
HERE=Path(__file__).resolve().parent

def read_strict(path):
 def pairs(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('duplicate key: '+k)
   d[k]=v
  return d
 def bad(x):raise ValueError('nonfinite JSON: '+x)
 def finite_float(x):
  value=float(x)
  if not math.isfinite(value):raise ValueError('nonfinite JSON number')
  return value
 return json.loads(Path(path).read_text(),object_pairs_hook=pairs,parse_constant=bad,parse_float=finite_float)

def grade(answer,data,reference=None):
 D=load(data);ref=reference or read_strict(HERE/'final_answer.json');rub=read_strict(HERE/'rubric.json');acc=D['study_metadata']['acceptance'];tol=acc['numeric_abs'];ft=acc['witness_feasibility_abs']
 schema=read_strict(Path(data)/'output_schema.json');errors=list(jsonschema.Draft202012Validator(schema).iter_errors(answer))
 # Extra keys or metadata slips alone cost 5. Missing numerical content fails its scientific group.
 presentation=bool(errors)
 checks={};details={}
 def close(x,y):
  return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and abs(x-y)<=tol
 def unique(items,key):
  out={}
  for item in items:
   k=key(item)
   if k in out:raise ValueError('duplicate scientific identifier')
   out[k]=item
  return out
 try:
  cultures=unique(answer['cultures'],lambda c:c['id']);expected={c['id'] for c in ref['cultures']}
  ok=set(cultures)==expected;worst=0.
  for rc in ref['cultures']:
   actual=unique(cultures[rc['id']]['flux_ranges'],lambda r:r['reaction']);ok &= set(actual)=={r['reaction'] for r in rc['flux_ranges']}
   for rr in rc['flux_ranges']:
    a=actual[rr['reaction']]
    ok &= close(a['lower'],rr['lower']) and close(a['upper'],rr['upper']) and type(a['identifiable']) is bool and a['identifiable']==rr['identifiable']
    worst=max(worst,abs(a['lower']-rr['lower']),abs(a['upper']-rr['upper']))
  checks['flux_ranges']=bool(ok);details['flux_max_absolute_error']=worst
 except (KeyError,TypeError,ValueError,OverflowError):checks['flux_ranges']=False
 try:
  designs=unique(answer['designs'],lambda d:tuple(sorted(d['modules'])));wanted=unique(ref['designs'],lambda d:tuple(d['modules']));ok=set(designs)==set(wanted);worst=0.
  for p,r in wanted.items():
   a=designs[p]
   for key in ['floor','regret']:
    ok &=close(a[key],r[key]);worst=max(worst,abs(a[key]-r[key]))
   ac=unique(a['by_culture'],lambda d:d['culture']);rc=unique(r['by_culture'],lambda d:d['culture']);ok &=set(ac)==set(rc)
   for cid in rc:
    for key in ['floor','regret']:
     ok &=close(ac[cid][key],rc[cid][key]);worst=max(worst,abs(ac[cid][key]-rc[cid][key]))
  checks['utility_envelopes']=bool(ok);details['utility_max_absolute_error']=worst
 except (KeyError,TypeError,ValueError,OverflowError):checks['utility_envelopes']=False
 try:
  s=answer['selection'];rs=ref['selection'];p=tuple(sorted(s['modules']));wanted={tuple(d['modules']):d for d in ref['designs']};safe=[d for d in ref['designs'] if d['floor']>=D['design_rules']['safety_floor']-D['study_metadata']['tie_tolerance']]
  if not safe:ok=s['status']=='no_robust_rescue' and not p and s['witness'] is None
  else:
   best=min(d['regret'] for d in safe)
   ok=s['status']=='selected' and p in wanted and wanted[p]['floor']>=D['design_rules']['safety_floor']-D['study_metadata']['tie_tolerance'] and wanted[p]['regret']<=best+acc['selection_regret_slack']
  checks['robust_selection']=bool(ok)
 except (KeyError,TypeError,ValueError):checks['robust_selection']=False
 try:
  if ref['selection']['status']=='no_robust_rescue':ok=answer['selection']['witness'] is None
  else:
   s=answer['selection'];w=s['witness'];p=tuple(sorted(s['modules']));q=tuple(sorted(w['challenger']));cs={c['id']:c for c in D['cultures']};culture=cs[w['culture']];poly=polytope(D,culture)
   x=np.r_[np.asarray(w['flux'],float),np.asarray(w['offsets'],float)];a,c=utility(culture,p);aa,cc=utility(culture,q);actual=aa-a+float((cc-c)@x)
   global_r=next(d['regret'] for d in ref['designs'] if tuple(d['modules'])==p)
   bounds=np.asarray(poly['bounds']);violation=max(float(np.max(poly['A_ub']@x-poly['b_ub'])),float(np.max(np.abs(poly['A_eq']@x-poly['b_eq']))),float(np.max(bounds[:,0]-x)),float(np.max(x-bounds[:,1])))
   ok=x.shape==(36,) and np.isfinite(x).all() and q in portfolios(D['design_rules']) and violation<=ft and abs(actual-global_r)<=acc['witness_objective_abs'] and close(w['regret'],actual)
   details.update(witness_violation=violation,witness_objective_error=abs(actual-global_r))
  checks['adversarial_witness']=bool(ok)
 except (KeyError,TypeError,ValueError,StopIteration):checks['adversarial_witness']=False
 raw=sum(rub['weights'][key] for key,v in checks.items() if v);cap=any(not v for v in checks.values());score=min(raw,rub['scientific_failure_cap']) if cap else raw;score=max(0,score-(rub['presentation_deduction'] if presentation else 0))
 return {'role':'numerical_rubric_evaluation','checks':checks,'details':details,'raw_score':raw,'scientific_cap_applied':cap,'presentation_deduction':rub['presentation_deduction'] if presentation else 0,'final_score':score,'passed':score>=rub['pass_threshold'],'schema_errors':[e.message for e in errors]}

def main():
 p=argparse.ArgumentParser();p.add_argument('--answer',required=True,type=Path);p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output',type=Path);a=p.parse_args()
 try: result=grade(read_strict(a.answer),a.data)
 except (OSError,ValueError,TypeError,OverflowError) as e:result={'final_score':0,'passed':False,'automatic_zero':'unreadable or non-strict JSON','reason':str(e)}
 text=json.dumps(result,indent=2,allow_nan=False)+'\n'
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
 print(text,end='');return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
