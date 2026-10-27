import json
from pathlib import Path
import numpy as np
from scipy.special import exprel,log_ndtr
from scipy.stats import t

def trajectory(theta,dt,g,q,gpre):
 n=np.exp(theta[:,0]);e,dn,dc=np.exp(theta[:,1:]).T;c=n*e/(dc+gpre);alpha=(e+dn+gpre)*n
 out=[np.column_stack([n,c])]
 for h,gg,qq in zip(dt,g,q):
  a=e+dn+gg;b=dc+gg;A=np.exp(-a*h);B=np.exp(-b*h);J=B*h*exprel(-(a-b)*h);s=alpha*qq
  c=c*B+e*(n*J+s/a*(h*exprel(-b*h)-J));n=n*A+s*h*exprel(-a*h);out.append(np.column_stack([n,c]))
 return np.array(out).transpose(1,0,2)

def fit(obs,cal,dt,g,q,gpre,sigma,limit,iterations=65,no_growth=False,no_source=False,no_mixing=False):
 if no_growth:g=np.zeros_like(g);gpre=0.
 if no_source:q=np.zeros_like(q)
 if no_mixing:cal=cal.copy();cal[:,1,0]=0;cal[:,0,1]=0
 G=len(obs);cal=cal[0] if cal.ndim==4 else cal
 finite=np.isfinite(obs);logs=np.log(np.where(finite,obs,limit));floor=np.log(limit)
 def residual(x):
  pop=trajectory(x,dt,g,q,gpre);mu=np.einsum('tij,gtj->gti',cal,pop);z=(np.log(np.maximum(mu,1e-20))-logs)/sigma
  censor=np.sqrt(np.maximum(0,-2*log_ndtr((floor-np.log(np.maximum(mu,1e-20)))/sigma)))
  return np.where(finite,z,censor).reshape(G,-1)
 initial=np.maximum(np.einsum('ij,gj->gi',np.linalg.inv(cal[0]),np.nan_to_num(obs[:,0],nan=float(np.min(limit))))[:,0],.2)
 best=np.full(G,np.inf);answer=np.zeros((G,4));eye=np.eye(4)[None]
 for nuclear in [.05,.25]:
  x=np.column_stack([np.log(initial),np.full(G,np.log(.25)),np.full(G,np.log(nuclear)),np.full(G,np.log(.12))]);lam=np.full(G,.01)
  for it in range(iterations):
   r=residual(x);J=np.stack([(residual(x+eye[:,j,:]*1e-4)-r)/1e-4 for j in range(4)],axis=2)
   H=np.einsum('gti,gtj->gij',J,J);gradient=np.einsum('gti,gt->gi',J,r)
   scale=np.maximum(np.diagonal(H,axis1=1,axis2=2),.01);step=np.linalg.solve(H+lam[:,None,None]*eye*scale[:,None,:],gradient[...,None])[...,0]
   step=np.clip(step,-1.2,1.2);trial=x-step;trial[:,0]=np.clip(trial[:,0],-3,13);trial[:,1:]=np.clip(trial[:,1:],-7,1.5)
   old=np.sum(r*r,axis=1);new=np.sum(residual(trial)**2,axis=1);accept=new<old;x[accept]=trial[accept];lam=np.where(accept,np.maximum(lam*.3,1e-8),np.minimum(lam*8,1e9))
  loss=np.sum(residual(x)**2,axis=1);accept=loss<best;answer[accept]=x[accept];best[accept]=loss[accept]
 return answer,best

def load(data):
 data=Path(data);m=json.loads((data/'study_metadata.json').read_text())
 with np.load(data/'hybridization.npz',allow_pickle=False) as f:D={k:f[k].copy() for k in f.files}
 return m,D

def inference(est,m,indices,unpaired=False):
 # Genes x parents x arms x kinetic parameters, base-2 log rate contrasts.
 values=est/np.log(2);diff=values[:,indices,1,1:]-values[:,indices,0,1:];n=len(indices);mean=diff.mean(axis=1);se=diff.std(axis=1,ddof=1)/np.sqrt(n)
 if unpaired:se=np.sqrt(values[:,indices,1,1:].var(axis=1,ddof=1)/n+values[:,indices,0,1:].var(axis=1,ddof=1)/n)
 se=np.maximum(se,.015);ci=np.stack([mean-t.ppf(.975,n-1)*se,mean+t.ppf(.975,n-1)*se],axis=-1);eq=np.stack([mean-t.ppf(.95,n-1)*se,mean+t.ppf(.95,n-1)*se],axis=-1)
 p=t.sf((np.abs(mean)-m['material_log2'])/se,n-1);order=np.argsort(p.ravel());adjust=np.minimum.accumulate((p.ravel()[order]*p.size/np.arange(1,p.size+1))[::-1])[::-1];q=np.empty(p.size);q[order]=np.minimum(adjust,1);q=q.reshape(p.shape)
 classes=np.full(mean.shape,'UNRESOLVED',dtype=object);classes[(eq[:,:,0]>-m['material_log2'])&(eq[:,:,1]<m['material_log2'])]='EQUIVALENT';classes[(q<=.05)&(mean>0)]='INCREASED';classes[(q<=.05)&(mean<0)]='DECREASED'
 rows=[]
 for j,gid in enumerate(m['genes']):
  effects={}
  for k,name in enumerate(m['parameters']):effects[name]={'log2_ratio':float(mean[j,k]),'interval':ci[j,k].tolist(),'equivalence_interval':eq[j,k].tolist(),'class':classes[j,k],'vehicle_rate':float(2**values[j,indices,0,k+1].mean()),'perturbed_rate':float(2**values[j,indices,1,k+1].mean())}
  rows.append({'id':gid,'effects':effects})
 group=[];mask=np.array(m['stress_group'])
 for k,name in enumerate(m['parameters']):
  v=diff[mask,:,k].mean(axis=0)-diff[~mask,:,k].mean(axis=0);s=v.std(ddof=1)/np.sqrt(n);group.append({'parameter':name,'estimate':float(v.mean()),'interval':[float(v.mean()-t.ppf(.975,n-1)*s),float(v.mean()+t.ppf(.975,n-1)*s)]})
 return {'genes':rows,'group_contrasts':group}

def analyse(data,config):
 m,D=load(data);G=len(m['genes']);P=m['parents'];est=np.zeros((G,P,2,4));analyses={};diagnostics={}
 for variant in ['base','early_window','leave_parent_out']:
  if variant=='leave_parent_out':analyses[variant]=inference(est,m,list(range(P-1)),config.get('unpaired',False));continue
  last=len(m['times']) if variant=='base' else len(m['times'])-2
  cal=D['spike_observed']/D['spike_known'][None,None,None,:,None]
  # geometric mean over two independently read standards for each matrix coefficient
  cal=np.exp(np.log(cal).mean(axis=-1))
  result=np.zeros_like(est);losses=[]
  for p in range(P):
   for arm in range(2):
    growth=np.diff(np.log(D['cell_counts'][p,arm,:last]))/np.diff(m['times'][:last]);q=D['run_on'][p,arm,:last-1].mean(axis=-1)
    x,loss=fit(D['observed'][:,p,arm,:last],cal[p,arm,:last],np.diff(m['times'][:last]),growth,q,D['pre_growth'][p,arm],m['log_sigma'],D['limits'][p,arm,:last],config['iterations'],config.get('no_growth',False),config.get('no_source',False),config.get('no_mixing',False))
    result[:,p,arm]=x;losses.extend(loss.tolist())
  analyses[variant]=inference(result,m,list(range(P)),config.get('unpaired',False));diagnostics[variant]={'mean_deviance':float(np.mean(losses)),'fits':len(losses)}
  if variant=='base':est=result.copy()
 return {'schema':'rna_transport/1','case_id':m['case_id'],'analyses':analyses},diagnostics
