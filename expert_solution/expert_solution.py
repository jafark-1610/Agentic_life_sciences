"""Sharp same-clone estimands over the full compatible causal family."""
from pathlib import Path
import csv,json
import numpy as np
from causal_model import poly,coefficients,solve,ratio
PROTOCOLS=['natural','priming_trial','rescue_trial','sequential_trial']
def load(data):
 d=Path(data);D={k:json.loads((d/(k+'.json')).read_text()) for k in ['study_metadata','contexts','policies','benchmark','protocols']}
 with (d/'tables.csv').open() as stream:D['tables']=list(csv.DictReader(stream))
 return D

def observed_vector(D,c):
 records={(o['lab'],o['protocol'],int(o['Z']),int(o['A']),int(o['W']),int(o['B']),int(o['S']),o['Y']):float(o['probability']) for o in D['tables'] if o['context']==c['id']}
 out=[]
 for lab in c['labs']:
  for protocol in PROTOCOLS:
   for z in range(2):
    for a in range(2):
     for w in range(2):
      for b in range(2):
       for s,y in [(0,'NA'),(1,'0'),(1,'1')]:out.append(records[(lab['id'],protocol,z,a,w,b,s,y)])
 return out

def summarize(D,contexts):
 lookup={c['id']:c for c in contexts};global_rows=[];limits=D['study_metadata']['decision']
 for p in D['policies']:
  rows=[next(r for r in c['policies'] if r['id']==p['id']) for c in contexts]
  global_rows.append({'id':p['id'],'worst_net_gain':min(r['net_gain_lower'] for r in rows),'worst_harm':max(r['harm_upper'] for r in rows),'worst_cost':max(r['cost_upper'] for r in rows),'minimum_eligibility':min(r['eligibility_lower'] for r in rows)})
 for row in global_rows:row['resource_adjusted_score']=row['worst_net_gain']-limits['resource_penalty']*row['worst_cost']
 safe=[p for p in global_rows if p['worst_harm']<=limits['maximum_harm'] and p['worst_cost']<=limits['maximum_cost'] and p['minimum_eligibility']>=limits['minimum_eligibility']]
 if not safe:selection={'status':'no_qualifying_policy','policy':None}
 else:
  best=max(p['resource_adjusted_score'] for p in safe);winner=min((p for p in safe if p['resource_adjusted_score']>=best-1e-7),key=lambda p:p['id']);selection={'status':'selected','policy':winner['id']}
 return global_rows,selection

def analyse(data):
 D=load(data);contexts=[]
 # Validate that the implemented design is the declared one, rather than silently ignoring edits.
 assert D['protocols']['randomization']=={'P_A1':.45,'P_B1_given_W':[.7,.35]}
 assert D['benchmark']=={'a':[1,1],'b':[[0,1],[0,1]]}
 for c in D['contexts']:
  P=poly(c,observed_vector(D,c));solve(P,np.zeros(P['A_eq'].shape[1]));rows=[]
  for policy in D['policies']:
   v=coefficients(c,policy);gl=solve(P,v['eligibility'])[0];gu=-solve(P,-v['eligibility'])[0]
   if gl<=1e-5:raise ValueError('Eligibility can vanish: conditional estimand needs a separate limit analysis')
   low=ratio(P,v['gain'],v['eligibility']);high=ratio(P,v['gain'],v['eligibility'],True);harm=ratio(P,v['harm'],v['eligibility'],True);cost=-solve(P,-v['cost'])[0]
   rows.append({'id':policy['id'],'eligibility_lower':gl,'eligibility_upper':gu,'net_gain_lower':low,'net_gain_upper':high,'harm_upper':max(0.,harm),'cost_upper':max(0.,cost),'point_identified':bool(high-low<=D['study_metadata']['acceptance']['identification_width'])})
  contexts.append({'id':c['id'],'policies':rows})
 globals_,selection=summarize(D,contexts)
 return {'schema':D['study_metadata']['schema'],'case_id':D['study_metadata']['case_id'],'contexts':contexts,'global_policies':globals_,'selection':selection}
