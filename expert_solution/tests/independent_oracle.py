"""Independent matrix assembly and primal/dual verification; imports no expert code."""
from pathlib import Path
import json,itertools
import numpy as np
from scipy.optimize import linprog

def inputs(data):
 d=Path(data);j=lambda f:json.loads((d/f).read_text())
 return j('network.json'),j('assay_panel.json'),j('cultures.json'),j('design_rules.json')

def menu(rules):
 out=[]
 for combo in itertools.combinations(rules['modules'],3):
  names=tuple(sorted(m['id'] for m in combo))
  if len({m['group'] for m in combo})!=3:continue
  if sum(m['cost'] for m in combo)>rules['budget']:continue
  if any(all(x in names for x in pair) for pair in rules['incompatible_pairs']):continue
  out.append(names)
 return sorted(out)

def matrix(net,panel,c):
 obs={o['channel']:o for o in c['observations']};ys=np.array([obs[ch]['value'] for ch in panel['channels']]);es=np.array([obs[ch]['halfwidth'] for ch in panel['channels']])
 H=np.array(panel['H']);G=np.eye(4)[panel['offset_groups']];T=np.column_stack((H,G))
 standards=c['standards'];Q=np.column_stack((np.zeros((len(standards),32)),np.eye(4)[[o['offset_group'] for o in standards]]))
 yy=np.array([o['observed']-o['known'] for o in standards]);ee=np.array([o['halfwidth'] for o in standards])
 A=np.vstack((T,-T,Q,-Q));b=np.r_[ys+es,es-ys,yy+ee,ee-yy];E=np.column_stack((np.array(net['stoichiometry']),np.zeros((9,4))))
 return A,b,E,c['bounds']+c['offset_bounds']

def opt(model,coeff,maximize=False):
 A,b,E,bounds=model;c=np.array(coeff,float)*(-1 if maximize else 1)
 r=linprog(c,A_ub=A,b_ub=b,A_eq=E,b_eq=np.zeros(9),bounds=bounds,method='highs')
 if not r.success:raise ValueError(r.message)
 lo=np.array(bounds)[:,0];hi=np.array(bounds)[:,1]
 dual=float(b@r.ineqlin.marginals+lo@r.lower.marginals+hi@r.upper.marginals)
 if abs(dual-r.fun)>1e-7:raise ValueError('primal-dual mismatch')
 return (-r.fun if maximize else r.fun),r.x

def response(c,plan):
 r=c['response'];a=sum([r['baseline_intercept']]+[r['modules'][m]['intercept'] for m in plan]);v=np.sum([r['baseline_coefficients']]+[r['modules'][m]['coefficients'] for m in plan],axis=0)
 return a,np.r_[v,np.zeros(4)]

def verify(data,answer):
 net,panel,cs,rules=inputs(data);plans=menu(rules);by={tuple(d['modules']):d for d in answer['designs']};ranges={c['id']:c['flux_ranges'] for c in answer['cultures']};worst=0.;n=0
 global_r={p:0. for p in plans};global_l={p:float('inf') for p in plans}
 for c in cs:
  model=matrix(net,panel,c);co={p:response(c,p) for p in plans}
  for j,rr in enumerate(ranges[c['id']]):
   assert rr['reaction']==net['reactions'][j];e=np.eye(36)[j]
   for field,maximum in [('lower',False),('upper',True)]:
    x,_=opt(model,e,maximum);worst=max(worst,abs(x-rr[field]));n+=1
  for p,(a,v) in co.items():
   low,_=opt(model,v);rr=0.
   for q,(aa,vv) in co.items():
    gap,_=opt(model,vv-v,True);rr=max(rr,aa-a+gap);n+=1
   actual=next(k for k in by[p]['by_culture'] if k['culture']==c['id'])
   worst=max(worst,abs(actual['floor']-a-low),abs(actual['regret']-rr));global_r[p]=max(global_r[p],rr);global_l[p]=min(global_l[p],a+low)
 for p in plans:worst=max(worst,abs(global_r[p]-by[p]['regret']),abs(global_l[p]-by[p]['floor']))
 return {'lp_checks':n,'maximum_absolute_error':float(worst),'primal_dual_tolerance':1e-7}
