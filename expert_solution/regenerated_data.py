"""Trusted-side physically consistent instrument replay dataset."""
from pathlib import Path
import shutil,json,hashlib
import numpy as np
from mechanism import simulate
from expert_solution import load,swap,predict,select
from artifacts import add_witness

def regenerate(src,dst,truth,seed=49173):
 src=Path(src);dst=Path(dst);shutil.copytree(src,dst);D=load(dst);rng=np.random.default_rng(seed);newtruth={}
 for chip in D['chips']:
  original=truth[chip['id']];p=np.array(original['parameters'])*rng.uniform(.86,1.14,10);bounds=np.array(D['model_spec']['parameter_bounds']);p=np.clip(p,bounds[:,0]*1.05,bounds[:,1]*.95)
  sensors={c:{'gain':s['gain']*float(rng.uniform(.96,1.04)),'kd':s['kd']*float(rng.uniform(.96,1.04)),'offset':s['offset']+float(rng.uniform(-.003,.003))} for c,s in original['calibration'].items()}
  def detector(c,x):s=sensors[c];return round(float(s['offset']+s['gain']*x/(s['kd']+x)),12)
  for o in chip['standards']:o['signal']=detector(o['channel'],o['concentration'])
  for proto in D['protocols']:
   times=sorted({o['time'] for o in chip['observations'] if o['protocol']==proto['id']});Y=simulate(p,chip['known'],proto,times,precise=True)['states'];by={t:y for t,y in zip(times,Y)}
   for o in chip['observations']:
    if o['protocol']!=proto['id']:continue
    y=by[o['time']];x=y[1] if o['channel']=='plasma' else y[2]+y[3]+y[4];o['signal']=detector(o['channel'],x)
  chip['observations'].reverse();newtruth[chip['id']]={'parameters':p.tolist(),'calibration':sensors}
 (dst/'chips.json').write_text(json.dumps(D['chips'],indent=2)+'\n')
 m=json.loads((dst/'data_manifest.json').read_text())
 for f in m['files']:
  b=(dst/f).read_bytes();m['files'][f]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
 (dst/'data_manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 return newtruth

def truth_answer(data,truth):
 D=load(data);chips=[]
 for chip in D['chips']:
  t=truth[chip['id']];p=np.array(t['parameters']);models=sorted([p.tolist(),swap(p).tolist()],key=tuple)
  # Independent central-difference local sensitivity matrix, in concentration coordinates.
  rows=[]
  for j in range(10):
   h=1e-4;pl=p.copy();ph=p.copy();pl[j]*=np.exp(-h);ph[j]*=np.exp(h);column=[]
   for proto in D['protocols']:
    times=sorted({o['time'] for o in chip['observations'] if o['protocol']==proto['id']})
    L=simulate(pl,chip['known'],proto,times,precise=True)['states'];H=simulate(ph,chip['known'],proto,times,precise=True)['states'];diff=(H-L)/(2*h);column.extend(np.column_stack((diff[:,1],diff[:,2]+diff[:,3]+diff[:,4])).ravel())
   rows.append(column)
  sv=np.linalg.svd(np.array(rows).T,compute_uv=False);rank=int(np.sum(sv>sv[0]*D['model_spec']['local_rank_relative_cutoff']))
  chips.append({'id':chip['id'],'calibration':t['calibration'],'models':models,'target_capacity_interval':[min(p[6],p[9]),max(p[6],p[9])],'target_capacity_point_identified':bool(abs(p[6]-p[9])<=D['model_spec']['acceptance']['parameter_absolute']),'local_rank':rank,'fit_rmse':0.})
 courses=predict(D,chips);answer={'case_id':D['model_spec']['case_id'],'schema':D['model_spec']['schema'],'chips':chips,'courses':courses,'selection':select(D,courses)};add_witness(answer,D);return answer
