"""Deterministic synthetic population distributions for paired-clone causal analysis."""
from pathlib import Path
import json,sys,csv,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'expert_solution'))
from causal_model import observation,prior,policies,REF
PROTOCOLS=['natural','priming_trial','rescue_trial','sequential_trial']
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False)+'\n')
def update_manifest(data):
 names=['study_metadata.json','contexts.json','protocols.json','policies.json','benchmark.json','tables.csv','source_provenance.json']
 save(data/'data_manifest.json',{'files':{f:{'bytes':(data/f).stat().st_size,'sha256':hashlib.sha256((data/f).read_bytes()).hexdigest()} for f in names}})
def cells():
 for z in range(2):
  for a in range(2):
   for w in range(2):
    for b in range(2):
     for s,y in [(0,'NA'),(1,'0'),(1,'1')]:yield z,a,w,b,s,y

def write_tables(data,contexts,truth):
 with (data/'tables.csv').open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['context','lab','protocol','Z','A','W','B','S','Y','probability'])
  for c in contexts:
   for lab in c['labs']:
    for protocol in PROTOCOLS:
     probs=observation(c,lab,protocol)@np.array(truth[c['id']])
     for cell,p in zip(cells(),probs):writer.writerow([c['id'],lab['id'],protocol,*cell,format(float(p),'.12f')])

def generate(root=ROOT):
 data=root/'task/data';contexts=[];truth={}
 for k,x in enumerate([.44,.52,.60]):
  c={'id':f'cohort_{k+1:02d}','z_false_positive':.08+.01*k,'z_false_negative':.14+.02*k,'image_flip':.09+.02*k,'target_x1':x,'rescue_cost':.65,'probability_band':1e-7,'labs':[{'id':'lab_L','x1':.2},{'id':'lab_H','x1':.8}]}
  contexts.append(c);truth[c['id']]=prior(c,62914+k*31).tolist()
 save(data/'contexts.json',contexts);save(data/'policies.json',policies());save(data/'benchmark.json',REF)
 save(data/'protocols.json',{'natural':{'A':'natural','B':'natural'},'priming_trial':{'A':'randomized','B':'natural'},'rescue_trial':{'A':'natural','B':'randomized'},'sequential_trial':{'A':'randomized','B':'randomized'},'randomization':{'P_A1':.45,'P_B1_given_W':[.7,.35]}})
 save(data/'study_metadata.json',{'case_id':'ALS_PAIRED_IMMUNITY_003','schema':'paired_immunity/1','acceptance':{'numeric_absolute':.001,'policy_score_absolute':.002,'decision_slack':.001,'identification_width':.0001},'decision':{'maximum_harm':.22,'maximum_cost':1.30,'minimum_eligibility':.80,'resource_penalty':.215},'units':{'gain':'probability difference','harm':'probability','eligibility':'probability','cost':'resource units'}})
 save(data/'source_provenance.json',{'origin':'Entirely synthetic population-limit assay distributions; no patient, donor, animal or external experimental data','seed':62914,'generator':'expert_solution/source_archive/generate_data.py','rounding':'Cell probabilities rounded to 12 decimal places; admissibility uses the public probability band','rights':'Original fixtures CC0-1.0 and source code MIT; see SOURCE_RIGHTS.md'})
 save(root/'expert_solution/private/generation_laws.json',truth);write_tables(data,contexts,truth);update_manifest(data)
if __name__=='__main__':generate()
