import itertools
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
M=np.array([(0,0),(0,1),(1,1)],dtype=np.int8)
S=np.array([v for v in itertools.product([0,1],repeat=4) if v[0]<=v[1] and v[0]<=v[2] and v[1]<=v[3] and v[2]<=v[3]],dtype=np.int8).reshape(-1,2,2)
Y=np.array([v for v in itertools.product([0,1],repeat=4) if v[0]<=v[1] and v[2]<=v[3]],dtype=np.int8).reshape(-1,2,2)
B=np.array(list(itertools.product([0,1],repeat=2)),dtype=np.int8)
T=np.array(list(itertools.product(range(3),range(6),range(9),range(2),range(4))),dtype=np.int16);N=len(T);I=np.arange(N)
mp=M[T[:,0]];sp=S[T[:,1]];yp=Y[T[:,2]];ao=T[:,3];bo=B[T[:,4]]

def pz(c,x,z):
 p=c['z_false_positive'] if x==0 else 1-c['z_false_negative']
 return p if z else 1-p

def observation(c,lab,protocol):
 rows=[];cols=[];vals=[]
 for x,z,e in itertools.product(range(2),repeat=3):
  weight=(lab['x1'] if x else 1-lab['x1'])*pz(c,x,z)*(c['image_flip'] if e else 1-c['image_flip'])
  assignments=[(ao,np.ones(N))] if protocol in ['natural','rescue_trial'] else [(np.full(N,a),np.full(N,p)) for a,p in [(0,.55),(1,.45)]]
  for a,pa in assignments:
   m=mp[I,a];w=m^e
   rescues=[(bo[I,w],np.ones(N))] if protocol in ['natural','priming_trial'] else [(np.full(N,b),np.where(w==0,.7 if b else .3,.35 if b else .65)) for b in range(2)]
   for b,pb in rescues:
    s=sp[I,m,b];y=yp[I,m,b];out=np.where(s==0,0,1+y);cell=(((z*2+a)*2+w)*2+b)*3+out
    rows.extend(cell);cols.extend(I+x*N);vals.extend(weight*pa*pb)
 return sparse.coo_matrix((vals,(rows,cols)),shape=(48,2*N)).tocsr()

REF={'a':[1,1],'b':[[0,1],[0,1]]}
def coefficients(c,policy):
 names=['eligibility','benefit','harm','gain','survival','cost'];out={k:np.zeros(2*N) for k in names}
 for x,z,e in itertools.product(range(2),repeat=3):
  wt=(c['target_x1'] if x else 1-c['target_x1'])*pz(c,x,z)*(c['image_flip'] if e else 1-c['image_flip'])
  def world(p):
   a=p['a'][z];m=mp[:,a];w=m^e;b=np.asarray(p['b'][z])[w];s=sp[I,m,b];y=yp[I,m,b]
   return s,y,a+c['rescue_cost']*b
  s,y,cost=world(policy);sr,yr,_=world(REF);g=s*sr;section=slice(x*N,(x+1)*N)
  for key,value in zip(names,[g,g*y*(1-yr),g*(1-y)*yr,g*(y-yr),s,cost]):out[key][section]+=wt*value
 return out

def poly(c,tables):
 A=sparse.vstack([observation(c,lab,p) for lab in c['labs'] for p in ['natural','priming_trial','rescue_trial','sequential_trial']],format='csr');target=np.array(tables);eps=c['probability_band'];E=sparse.csr_matrix((np.ones(2*N),(np.repeat([0,1],N),np.arange(2*N))),shape=(2,2*N))
 return {'A_ub':sparse.vstack([A,-A],format='csr'),'b_ub':np.r_[target+eps,-target+eps],'A_eq':E,'b_eq':np.ones(2),'bounds':(0,None)}

def solve(P,c):
 r=linprog(c,**P,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
 if not r.success:raise ValueError(r.message)
 return float(r.fun),r.x

def ratio(P,n,d,maximum=False):
 A=P['A_ub'];E=P['A_eq'];b=P['b_ub'];f=P['b_eq']
 kwargs={'A_ub':sparse.hstack([A,-b[:,None]],format='csr'),'b_ub':np.zeros(len(b)),'A_eq':sparse.vstack([sparse.hstack([E,-f[:,None]],format='csr'),sparse.csr_matrix(np.r_[d,0][None,:])],format='csr'),'b_eq':np.r_[np.zeros(len(f)),1.],'bounds':(0,None)}
 obj=np.r_[-n if maximum else n,0];value,z=solve(kwargs,obj);return -value if maximum else value

def prior(c,seed=0):
 rng=np.random.default_rng(seed);w=[]
 for x in range(2):
  pm=np.array([.2,.65,.15])
  ps=np.array([.005,.01,.025,.015,.035,.91]) # S order is lexicographic monotone
  py=np.full(9,.01)
  patterns=[((0,0,0,0),.03),((0,1,0,1),.49),((1,1,1,1),.03),((1,1,0,0),.36 if x==0 else .03),((0,0,1,1),.03 if x==0 else .36)]
  for pat,val in patterns:py[next(i for i,v in enumerate(Y.reshape(9,4)) if tuple(v)==pat)]=val
  py/=py.sum();base=pm[T[:,0]]*ps[T[:,1]]*py[T[:,2]]
  lack=yp[:,0,0]==0;pa=np.where(lack,.8,.2);base*=np.where(ao==1,pa,1-pa)
  pb=np.array([.1,.25,.2,.45]);base*=pb[T[:,4]]
  base*=np.exp(rng.normal(0,.15,N));base/=base.sum();w.extend(base)
 return np.array(w)

def policies():
 bs=[[[0,0],[0,0]],[[1,1],[1,1]],[[0,1],[0,1]],[[1,0],[1,0]],[[1,1],[0,0]],[[0,0],[1,1]]]
 return [{'id':f'policy_{i+1:02d}','a':list(a),'b':b} for i,(a,b) in enumerate(itertools.product(itertools.product(range(2),repeat=2),bs))]
