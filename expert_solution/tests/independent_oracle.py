"""Independent Radau dynamics, event handling, and continuous extrema."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

def integrate(p,k,course,scenario=None):
 p=np.array(p).copy();names=['ka','kel','vmax','km','kon1','koff1','q1','kon2','koff2','q2']
 for name,factor in (scenario or {}).items():p[names.index(name)]*=factor
 ka,ke,vm,km,a,b,Q,c,d,R=p;end=course['horizon'];events={0.,end}
 for t,v in course['pulses']:events.add(t)
 for w in course['blockade']:events.update([w['start'],w['end']])
 events=sorted(events);state=np.zeros(7);peak=0.;peak_time=0.;mass=0.;dose=0.
 for left,right in zip(events[:-1],events[1:]):
  bolus=sum(v for t,v in course['pulses'] if t==left);state[0]+=bolus;dose+=bolus
  middle=(left+right)/2;blocking=[w for w in course['blockade'] if w['start']<=middle<w['end']]
  h1=1/(1+sum(w['strength'] for w in blocking));h2=1/(1+sum(w['strength'] for w in blocking if w['site']=='both'))
  def rhs(t,z):
   depot,plasma,free,s1,s2,auc,lost=z;transport=vm*plasma/(km+plasma);bind1=a*h1*free*(Q-s1);bind2=c*h2*free*(R-s2);release1=b*s1;release2=d*s2
   d1=bind1-release1-k['kint1']*s1;d2=bind2-release2-k['kint2']*s2
   return np.array([-ka*depot,ka*depot-ke*plasma-transport+k['kreturn']*free,transport-k['kreturn']*free-bind1-bind2+release1+release2,d1,d2,s2/R,ke*plasma+k['kint1']*s1+k['kint2']*s2])
  sol=solve_ivp(rhs,[left,right],state,method='Radau',rtol=4e-10,atol=4e-12,dense_output=True);assert sol.success;state=sol.y[:,-1];grid=np.linspace(left,right,int(np.ceil((right-left)/.035))+1);Y=sol.sol(grid);mass=max(mass,float(np.max(np.abs(Y[[0,1,2,3,4,6]].sum(axis=0)-dose))))
  for j in range(len(grid)):
   v=Y[2,j];t=grid[j]
   if 0<j<len(grid)-1 and v>=Y[2,j-1] and v>=Y[2,j+1]:
    opt=minimize_scalar(lambda x:-sol.sol(x)[2],bounds=(grid[j-1],grid[j+1]),method='bounded',options={'xatol':1e-10});v=-opt.fun;t=opt.x
   if v>peak:peak=float(v);peak_time=float(t)
 return {'efficacy':float(state[5]/end),'peak_free':peak,'peak_time':peak_time,'mass_error':mass}
