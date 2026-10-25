"""Integrity, type, relationship, and feasible-state checks; safe to run offline."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

def validate(data,integrity=True):
 d=Path(data);read=lambda n:json.loads((d/n).read_text())
 if integrity:
  for f,v in read('data_manifest.json')['files'].items():
   raw=(d/f).read_bytes();assert len(raw)==v['bytes'] and hashlib.sha256(raw).hexdigest()==v['sha256'],f+' integrity mismatch'
 net=read('network.json');panel=read('assay_panel.json');cs=read('cultures.json');rules=read('design_rules.json')
 S=np.asarray(net['stoichiometry']);H=np.asarray(panel['H']);n=len(net['reactions'])
 assert S.shape==(9,32) and H.shape==(28,32) and n==len(set(net['reactions']))
 assert np.isfinite(S).all() and np.isfinite(H).all()
 assert len(panel['channels'])==len(set(panel['channels']))==28
 assert set(panel['offset_groups'])==set(range(4))
 ids={m['id'] for m in rules['modules']};assert len(ids)==9
 assert set(m['group'] for m in rules['modules'])=={'uptake','redox','export'}
 assert all(set(p)<=ids and len(p)==2 for p in rules['incompatible_pairs'])
 assert len(cs)==8 and len({c['id'] for c in cs})==8
 for c in cs:
  bounds=c['bounds']+c['offset_bounds'];assert len(bounds)==36
  assert all(np.isfinite(pair).all() and pair[0]<=pair[1] for pair in bounds)
  A=[];b=[]
  assert len(c['observations'])==28 and {o['channel'] for o in c['observations']}==set(panel['channels'])
  assert len(c['standards'])==12 and len({o['id'] for o in c['standards']})==12
  for o in c['observations']:
   j=panel['channels'].index(o['channel']);a=np.r_[H[j],np.zeros(4)];a[n+panel['offset_groups'][j]]=1
   assert o['halfwidth']>0 and np.isfinite([o['value'],o['halfwidth']]).all()
   A.extend([a,-a]);b.extend([o['value']+o['halfwidth'],-o['value']+o['halfwidth']])
  for o in c['standards']:
   assert 0<=o['offset_group']<4 and o['halfwidth']>0
   a=np.zeros(36);a[n+o['offset_group']]=1;y=o['observed']-o['known'];assert np.isfinite([y,o['halfwidth']]).all()
   A.extend([a,-a]);b.extend([y+o['halfwidth'],-y+o['halfwidth']])
  response=c['response'];assert set(response['modules'])==ids
  for r in [dict(intercept=response['baseline_intercept'],coefficients=response['baseline_coefficients'])]+list(response['modules'].values()):
   assert len(r['coefficients'])==32 and np.isfinite(r['coefficients']).all() and np.isfinite(r['intercept'])
  r=linprog(np.zeros(36),A_ub=A,b_ub=b,A_eq=np.pad(S,((0,0),(0,4))),b_eq=np.zeros(9),bounds=bounds,method='highs')
  assert r.success,c['id']+' infeasible'
 return {'status':'success','cultures':len(cs),'fluxes':n,'channels':28,'offset_groups':4}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();print(json.dumps(validate(a.data)))
