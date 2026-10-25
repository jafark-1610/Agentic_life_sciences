"""Data-driven nonlinear inversion and global observational-equivalence analysis."""
from pathlib import Path
import json,itertools
import numpy as np
from scipy.optimize import least_squares
from mechanism import simulate,NAMES

def load(data):
 d=Path(data);return {f:json.loads((d/(f+'.json')).read_text()) for f in ['model_spec','protocols','chips','scenarios','courses']}
def swap(p):return np.asarray(p)[[0,1,2,3,7,8,9,4,5,6]]
def calibrate(chip,spec):
 out={}
 for c in spec['channels']:
  rows=[o for o in chip['standards'] if o['channel']==c];x=np.array([o['concentration'] for o in rows]);y=np.array([o['signal'] for o in rows])
  def residual(p):g,k,b=p;return b+g*x/(k+x)-y
  r=least_squares(residual,[2.,2.,.03],bounds=tuple(zip(*[spec['calibration_bounds'][k] for k in ['gain','kd','offset']])),gtol=1e-13,xtol=1e-13,ftol=1e-13)
  out[c]=dict(zip(['gain','kd','offset'],map(float,r.x)))
 return out

def fit_chip(chip,D):
 spec=D['model_spec'];sensors=calibrate(chip,spec);bounds=np.array(spec['parameter_bounds']);protocols={p['id']:p for p in D['protocols']};rows=chip['observations'];batches=[]
 for pid,proto in protocols.items():
  times=sorted({o['time'] for o in rows if o['protocol']==pid});ys=[]
  for t in times:
   pair=[]
   for c in spec['channels']:
    o=next(o for o in rows if o['protocol']==pid and o['time']==t and o['channel']==c);s=sensors[c];z=o['signal']-s['offset'];pair.append(s['kd']*z/(s['gain']-z))
   ys.append(pair)
  batches.append((proto,times,np.array(ys)))
 def residual(z,precise=False):
  pieces=[]
  for proto,times,ys in batches:
   sim=simulate(np.exp(z),chip['known'],proto,times,precise=precise);Y=sim['states'] if precise else sim
   pieces.extend((np.column_stack((Y[:,1],Y[:,2]+Y[:,3]+Y[:,4]))-ys).ravel())
  return np.array(pieces)
 # Asymmetric deterministic initializations avoid the coincident-pool stationary set.
 initials=[np.sqrt(bounds[:,0]*bounds[:,1]) for _ in range(2)]
 initials[0][[4,5,6,7,8,9]]=[.65,.04,1.4,1.3,.3,.7]
 initials[1][[4,5,6,7,8,9]]=[1.6,.35,.8,.5,.025,1.6]
 fits=[]
 for initial in initials:
  r=least_squares(residual,np.log(initial),bounds=(np.log(bounds[:,0]),np.log(bounds[:,1])),diff_step=2e-4,x_scale='jac',max_nfev=180,gtol=1e-10,xtol=1e-10,ftol=1e-10)
  fits.append(r)
 best=min(fits,key=lambda r:np.linalg.norm(r.fun));p=np.exp(best.x)
 # Refine against the high-accuracy observation operator used for reporting.
 r=least_squares(lambda z:residual(z,True),np.log(p),bounds=(np.log(bounds[:,0]),np.log(bounds[:,1])),diff_step=1e-4,x_scale='jac',max_nfev=60,gtol=2e-12,xtol=2e-12,ftol=2e-12)
 p=np.exp(r.x);models=sorted([p.tolist(),swap(p).tolist()],key=lambda x:tuple(x));sv=np.linalg.svd(r.jac,compute_uv=False);rank=int(np.sum(sv>sv[0]*spec['local_rank_relative_cutoff']))
 rmse=float(np.sqrt(np.mean(r.fun**2)))
 return {'id':chip['id'],'calibration':sensors,'models':models,'target_capacity_interval':[float(min(p[6],p[9])),float(max(p[6],p[9]))],'target_capacity_point_identified':bool(abs(p[6]-p[9])<=spec['acceptance']['parameter_absolute']),'local_rank':rank,'fit_rmse':rmse}

def predict(D,fits):
 by={f['id']:f for f in fits};courses=[]
 for course in D['courses']:
  cases=[]
  for chip in D['chips']:
   for j,p in enumerate(by[chip['id']]['models']):
    for scenario in D['scenarios']:
     sim=simulate(p,chip['known'],course,scenario=scenario['multipliers'],precise=True)
     cases.append({'chip':chip['id'],'model_index':j,'scenario':scenario['id'],'efficacy':sim['efficacy'],'peak_free':sim['peak_free']})
  courses.append({'id':course['id'],'minimum_efficacy':min(c['efficacy'] for c in cases),'maximum_peak_free':max(c['peak_free'] for c in cases),'cases':cases})
 return courses

def select(D,courses):
 rules=D['model_spec']['decision'];raw={c['id']:c for c in D['courses']};feasible=[c for c in courses if c['minimum_efficacy']>=rules['efficacy_floor'] and c['maximum_peak_free']<=rules['peak_ceiling']]
 if not feasible:return {'status':'no_qualifying_course','course':None}
 best=min(feasible,key=lambda c:(raw[c['id']]['cost'],c['id']));return {'status':'selected','course':best['id']}

def analyse(data):
 D=load(data);fits=[fit_chip(chip,D) for chip in D['chips']];courses=predict(D,fits)
 return {'schema':D['model_spec']['schema'],'case_id':D['model_spec']['case_id'],'chips':fits,'courses':courses,'selection':select(D,courses)}
