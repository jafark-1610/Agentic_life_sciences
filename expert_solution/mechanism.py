import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar
NAMES=['ka','kel','vmax','km','kon1','koff1','q1','kon2','koff2','q2']

def simulate(p,known,protocol,times=None,scenario=None,precise=False,method='LSODA',peak_step=.12):
 p=np.array(p,float).copy();scenario=scenario or {}
 for key,scale in scenario.items():p[NAMES.index(key)]*=scale
 ka,kel,vm,km,on1,off1,q1,on2,off2,q2=p
 kr,i1,i2=[known[x] for x in ['kreturn','kint1','kint2']]
 T=protocol['horizon'];pulses=protocol['pulses'];windows=protocol.get('blockade',[])
 events=sorted(set([0.,T]+[float(t) for t,d in pulses]+[float(w[k]) for w in windows for k in ['start','end']]))
 if any(t<0 or t>T for t in events):raise ValueError('event outside horizon')
 times=np.array(times if times is not None else [T],float);out=np.zeros((len(times),7));y=np.zeros(7);pieces=[]
 for t0,t1 in zip(events[:-1],events[1:]):
  y[0]+=sum(d for t,d in pulses if abs(t-t0)<1e-10)
  strength=sum(w['strength'] for w in windows if w['start']<=(t0+t1)/2<w['end'])
  f=1/(1+strength)
  strength2=sum(w['strength'] for w in windows if w['start']<=(t0+t1)/2<w['end'] and w.get('site','site1')=='both')
  f2=1/(1+strength2)
  def rhs(t,y):
   D,C,F,B1,B2,A,L=y
   tr=vm*C/(km+C);a1=on1*f*F*(q1-B1)-off1*B1;a2=on2*f2*F*(q2-B2)-off2*B2
   return [-ka*D,ka*D-kel*C-tr+kr*F,tr-kr*F-a1-a2,a1-i1*B1,a2-i2*B2,B2/q2,kel*C+i1*B1+i2*B2]
  sol=solve_ivp(rhs,(t0,t1),y,rtol=2e-10 if precise else 2e-7,atol=2e-12 if precise else 2e-9,method=method,dense_output=True)
  if not sol.success:raise ValueError(sol.message)
  idx=np.where((times>=t0-1e-12)&(times<=t1+1e-12))[0]
  if len(idx):out[idx]=sol.sol(times[idx]).T
  pieces.append((t0,t1,sol.sol));y=sol.y[:,-1]
 # optional terminal dose affects depot only
 y[0]+=sum(d for t,d in pulses if abs(t-T)<1e-10)
 if not precise:return out
 maxF=-1.;timeF=0.;maxmass=0.;total=0.
 for t0,t1,fun in pieces:
  total+=sum(d for t,d in pulses if abs(t-t0)<1e-10)
  grid=np.linspace(t0,t1,max(9,int(np.ceil((t1-t0)/peak_step))+1));Y=fun(grid);values=Y[2]
  maxmass=max(maxmass,float(np.max(np.abs(Y[[0,1,2,3,4,6]].sum(axis=0)-total))))
  candidates=[(values[0],grid[0]),(values[-1],grid[-1])]
  for j in range(1,len(grid)-1):
   if values[j]>=values[j-1] and values[j]>=values[j+1]:
    r=minimize_scalar(lambda t:-fun(t)[2],bounds=(grid[j-1],grid[j+1]),method='bounded',options={'xatol':1e-10});candidates.append((-r.fun,r.x))
  v,t=max(candidates)
  if v>maxF:maxF=float(v);timeF=float(t)
 return {'states':out,'efficacy':float(y[5]/T),'peak_free':maxF,'peak_time':timeF,'mass_error':maxmass}
