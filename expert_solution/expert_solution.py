"""Polyhedral flux uncertainty and discrete minimax-regret rescue design."""
from pathlib import Path
import itertools,json
import numpy as np
from scipy.optimize import linprog

def load(data):
 data=Path(data)
 return {x:json.loads((data/(x+'.json')).read_text()) for x in ['network','assay_panel','cultures','design_rules','study_metadata']}

def portfolios(rules):
 groups=sorted({m['group'] for m in rules['modules']})
 lookup={m['id']:m for m in rules['modules']}
 result=[]
 for p in itertools.product(*[[m['id'] for m in rules['modules'] if m['group']==g] for g in groups]):
  if sum(lookup[i]['cost'] for i in p)>rules['budget']:continue
  if any(set(pair)<=set(p) for pair in rules['incompatible_pairs']):continue
  result.append(tuple(sorted(p)))
 return sorted(result)

def polytope(D,culture):
 S=np.asarray(D['network']['stoichiometry'],float);H=np.asarray(D['assay_panel']['H'],float)
 n=S.shape[1];g=len(culture['offset_bounds']);A=[];b=[]
 channels=D['assay_panel']['channels'];groups=D['assay_panel']['offset_groups']
 for o in culture['observations']:
  j=channels.index(o['channel']);row=np.zeros(n+g);row[:n]=H[j];row[n+groups[j]]=1
  A.extend([row,-row]);b.extend([o['value']+o['halfwidth'],-o['value']+o['halfwidth']])
 for o in culture['standards']:
  row=np.zeros(n+g);row[n+o['offset_group']]=1;y=o['observed']-o['known']
  A.extend([row,-row]);b.extend([y+o['halfwidth'],-y+o['halfwidth']])
 return {'A_ub':np.asarray(A),'b_ub':np.asarray(b),'A_eq':np.pad(S,((0,0),(0,g))),'b_eq':np.zeros(S.shape[0]),'bounds':culture['bounds']+culture['offset_bounds']}

def solve(poly,c):
 r=linprog(c,**poly,method='highs')
 if not r.success:raise ValueError('LP failed: '+r.message)
 return float(r.fun),r.x

def utility(culture,plan):
 r=culture['response'];a=r['baseline_intercept'];c=np.asarray(r['baseline_coefficients'],float).copy()
 for m in plan:
  a+=r['modules'][m]['intercept'];c+=r['modules'][m]['coefficients']
 return a,np.r_[c,np.zeros(len(culture['offset_bounds']))]

def analyse(data):
 D=load(data);plans=portfolios(D['design_rules']);n=len(D['network']['reactions']);tol=D['study_metadata']['tie_tolerance']
 answer={'schema':D['study_metadata']['schema'],'case_id':D['study_metadata']['case_id'],'cultures':[],'designs':[]}
 floors=np.full(len(plans),np.inf);regrets=np.zeros(len(plans));witnesses={};polys={}
 for culture in sorted(D['cultures'],key=lambda x:x['id']):
  cid=culture['id'];poly=polytope(D,culture);polys[cid]=poly
  ranges=[]
  for i,name in enumerate(D['network']['reactions']):
   e=np.zeros(n+4);e[i]=1
   lo,_=solve(poly,e);neg,_=solve(poly,-e);hi=-neg
   ranges.append({'reaction':name,'lower':lo,'upper':hi,'identifiable':bool(hi-lo<=D['study_metadata']['acceptance']['identifiable_width'])})
  # The ordinary least-squares point is deliberately not the decision target.
  answer['cultures'].append({'id':cid,'flux_ranges':ranges})
  utility_rows=[utility(culture,p) for p in plans]
  for i,(a,c) in enumerate(utility_rows):
   low,_=solve(poly,c);floors[i]=min(floors[i],a+low)
   for j,(aa,cc) in enumerate(utility_rows):
    neg,x=solve(poly,c-cc);gap=aa-a-neg
    if i not in witnesses or gap>regrets[i]+tol:
     regrets[i]=max(0.,gap)
     witnesses[i]={'culture':cid,'challenger':list(plans[j]),'flux':x[:n].tolist(),'offsets':x[n:].tolist(),'regret':max(0.,gap)}
  for i,p in enumerate(plans):
   # Per-culture floor and regret, in addition to global values, are independently graded.
   a,c=utility_rows[i];low,_=solve(poly,c)
   rr=max(aa-a-solve(poly,c-cc)[0] for aa,cc in utility_rows)
   answer.setdefault('_per_culture',{}).setdefault(i,[]).append({'culture':cid,'floor':a+low,'regret':max(0.,rr)})
 for i,p in enumerate(plans):
  answer['designs'].append({'modules':list(p),'floor':float(floors[i]),'regret':float(regrets[i]),'by_culture':answer['_per_culture'][i]})
 del answer['_per_culture']
 safe=[i for i in range(len(plans)) if floors[i]>=D['design_rules']['safety_floor']-tol]
 if not safe:
  answer['selection']={'status':'no_robust_rescue','modules':[],'witness':None}
 else:
  optimum=min(regrets[i] for i in safe)
  chosen=min((i for i in safe if regrets[i]<=optimum+tol),key=lambda i:plans[i])
  answer['selection']={'status':'selected','modules':list(plans[chosen]),'witness':witnesses[chosen]}
 return answer
