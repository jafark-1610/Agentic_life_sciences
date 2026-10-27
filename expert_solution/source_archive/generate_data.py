import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from analysis_engine import trajectory
ROOT=Path(__file__).resolve().parents[2]
def generate(root=ROOT,seed=48031):
 root=Path(root);data=root/'task/data';data.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(seed);G=600;P=6;times=np.array([0,.25,.75,1.5,3,5,8,12,18.]);T=len(times)
 stress=np.arange(G)<120;ratebase=np.column_stack([rng.uniform(.16,.45,G),rng.uniform(.08,.25,G),rng.uniform(.04,.15,G)])
 effect=rng.normal(0,.035,(G,3));effect[:120,0]=-1.1;effect[:120,2]=.65;effect[120:180,0]=.9;effect[180:240,1]=1.0;effect[240:300,2]=-1.0
 shared=rng.normal(0,.12,(P,3));group_effect=rng.normal(0,.12,(P,3));params=np.zeros((G,P,2,4));pop=np.zeros((G,P,2,T,2));cells=np.zeros((P,2,T));pre=rng.uniform(.035,.075,(P,2));runon=np.zeros((P,2,T-1,2));A=np.zeros((P,2,T,2,2))
 for p in range(P):
  for arm in range(2):
   g=pre[p,arm]*(.25+.75*np.exp(-times[:-1]/(3+arm)));cells[p,arm]=1e6*np.r_[1,np.exp(np.cumsum(g*np.diff(times)))]
   q=(.055+.12*arm)+(.6-.2*arm)*np.exp(-times[1:]/.45);runon[p,arm]=q[:,None]*np.exp(rng.normal(0,.008,(T-1,2)))
   rates=ratebase*2**(shared[p][None,:]+rng.normal(0,.055,(G,3))+arm*(effect+stress[:,None]*group_effect[p]+rng.normal(0,.055,(G,3))))
   n0=np.exp(rng.uniform(2,5,G)+rng.normal(0,.05,G));x=np.column_stack([np.log(n0),np.log(rates)]);params[:,p,arm]=x;pop[:,p,arm]=trajectory(x,np.diff(times),g,q,pre[p,arm])
   for j in range(T):
    exposure=rng.uniform(.7,2.,2);mix=np.array([[rng.uniform(.7,.9),rng.uniform(.08,.24)],[rng.uniform(.10,.3),rng.uniform(.65,.9)]]);A[p,arm,j]=exposure[:,None]*mix
 known=np.array([10000.,15000.]);spikes=A[...,None]*known[None,None,None,None,:,None]*np.exp(rng.normal(0,.0005,(*A.shape,2)))
 mu=np.einsum('patij,gpatj->gpati',A,pop);sigma=.025;raw=mu*np.exp(rng.normal(0,sigma,mu.shape));limits=np.full((P,2,T,2),1.5);observed=np.where(raw>=limits[None],raw,np.nan)
 np.savez_compressed(data/'hybridization.npz',observed=observed,spike_observed=spikes,spike_known=known,cell_counts=cells,pre_growth=pre,run_on=runon,limits=limits)
 meta={'case_id':'ALS_RNA_TRANSPORT_006','genes':['tx_%04d'%i for i in range(G)],'stress_group':stress.tolist(),'parents':P,'arms':['vehicle','perturbed'],'parameters':['export','nuclear_decay','cytoplasmic_decay'],'times':times.tolist(),'log_sigma':sigma,'material_log2':float(np.log2(1.5))}
 (data/'study_metadata.json').write_text(json.dumps(meta,indent=2)+'\n');(root/'expert_solution/private').mkdir(parents=True,exist_ok=True);np.savez_compressed(root/'expert_solution/private/truth.npz',parameters=params,effects=effect)
 update_manifest(data)
def update_manifest(data):
 files={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(data.iterdir()) if p.is_file() and p.name!='data_manifest.json'};(data/'data_manifest.json').write_text(json.dumps({'files':files},indent=2)+'\n')
if __name__=='__main__':generate()
