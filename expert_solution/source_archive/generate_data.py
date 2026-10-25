"""Original synthetic target-mediated disposition experiments."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'expert_solution'))
from mechanism import simulate,NAMES

def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def generate(root=ROOT):
 d=root/'task/data';rng=np.random.default_rng(618420)
 times=[.06,.13,.27,.5,.85,1.3,2.,2.8,4.,5.5,7.,8.5,10.,12.,16.,20.,26.,34.,42.,48.]
 protocols=[{'id':'low','horizon':48.,'pulses':[[0.,.8]],'blockade':[]},{'id':'high','horizon':48.,'pulses':[[0.,5.5]],'blockade':[]},{'id':'wash','horizon':48.,'pulses':[[0.,3.],[10.,2.]],'blockade':[{'start':2.,'end':8.,'strength':12.,'site':'both'}]}]
 bounds=[[.3,4.],[.04,.45],[.3,2.],[.15,2.5],[.2,3.],[.008,.8],[.2,3.],[.2,3.],[.008,.8],[.2,3.]]
 spec={'case_id':'ALS_TMDD_PULSE_002','schema':'tmdd_pulse/1','parameters':NAMES,'parameter_bounds':bounds,'channels':['plasma','tissue_total'],'standards':[0.,.1,.4,1.5,4.,12.], 'calibration_bounds':{'gain':[.5,4.],'kd':[.3,8.],'offset':[-.1,.2]},'horizon':36.,'local_rank_relative_cutoff':1e-7,'acceptance':{'parameter_relative':.015,'parameter_absolute':.0005,'calibration_absolute':.0001,'fit_rmse_max':.00002,'efficacy_absolute':.002,'peak_absolute':.003,'witness_value_absolute':.003,'mass_balance_max':.00002,'cost_slack':.000001},'decision':{'efficacy_floor':.4,'peak_ceiling':.93}}
 save(d/'model_spec.json',spec);save(d/'protocols.json',protocols)
 chips=[];truth={}
 for j in range(6):
  cid=f'chip_{j+1:02d}'
  p=np.array([rng.uniform(1.2,2.5),rng.uniform(.11,.23),rng.uniform(.65,1.3),rng.uniform(.45,1.05),rng.uniform(.45,1.0),rng.uniform(.025,.055),rng.uniform(1.0,1.8),rng.uniform(.9,1.8),rng.uniform(.19,.45),rng.uniform(.5,1.0)])
  # Chemical identity is generated arbitrarily. Observations are invariant to this swap.
  if j%2:p[[4,5,6,7,8,9]]=p[[7,8,9,4,5,6]]
  known={'kreturn':float(rng.uniform(.12,.23)),'kint1':.02,'kint2':.02}
  sensors={c:{'gain':float(rng.uniform(1.2,2.5)),'kd':float(rng.uniform(1.2,3.2)),'offset':float(rng.uniform(.01,.06))} for c in spec['channels']}
  def detect(channel,x):
   k=sensors[channel];return round(float(k['offset']+k['gain']*x/(k['kd']+x)),12)
  standards=[{'channel':c,'concentration':v,'signal':detect(c,v)} for c in spec['channels'] for v in spec['standards']]
  observations=[]
  for proto in protocols:
   Y=simulate(p,known,proto,times,precise=True)['states']
   for t,y in zip(times,Y):
    for c,x in [('plasma',y[1]),('tissue_total',y[2]+y[3]+y[4])]:observations.append({'protocol':proto['id'],'time':t,'channel':c,'signal':detect(c,x)})
  chips.append({'id':cid,'known':known,'standards':standards,'observations':observations})
  truth[cid]={'parameters':p.tolist(),'calibration':sensors}
 save(d/'chips.json',chips)
 scenarios=[{'id':'baseline','multipliers':{}},{'id':'slow_clearance','multipliers':{'kel':.65,'vmax':1.15}},{'id':'acid_shift','multipliers':{'koff1':1.8,'koff2':.7,'kel':1.15}}]
 save(d/'scenarios.json',scenarios)
 timings=[[[0.,1.],[8.,1.],[16.,1.]],[[0.,1.5],[12.,1.5]],[[0.,1.],[6.,.5],[18.,1.5]],[[0.,.7],[4.,.8],[12.,.8],[24.,.7]]]
 candidates=[]
 for k,weights in enumerate(timings):
  for block in [False,True]:
   for q,scale in enumerate([.65,1.,1.5,2.2,3.1,4.3]):
    candidates.append({'id':f'course_{len(candidates)+1:03d}','horizon':36.,'pulses':[[t,w*scale] for t,w in weights],'blockade':[{'start':3.,'end':11.,'strength':10.,'site':'site1'}] if block else [],'cost':round(3*scale+.12*len(weights)+(.22 if block else 0),8)})
 save(d/'courses.json',candidates);save(root/'expert_solution/private/generation_truth.json',truth)
 save(d/'source_provenance.json',{'origin':'Original synthetic organ-chip experiments, no human or animal measurements','seed':618420,'method':'Numerical integration of the declared mass-conserving two-site disposition system; sensor signals rounded to 12 decimals','generator':'expert_solution/source_archive/generate_data.py','rights':'CC0-1.0 for synthetic fixtures; MIT for code; see SOURCE_RIGHTS.md'})
 manifest(d)
def manifest(d):
 names=['model_spec.json','protocols.json','chips.json','scenarios.json','courses.json','source_provenance.json']
 save(d/'data_manifest.json',{'files':{f:{'sha256':hashlib.sha256((d/f).read_bytes()).hexdigest(),'bytes':(d/f).stat().st_size} for f in names}})
if __name__=='__main__':generate()
