"""Independent response-family assembly and bisection of fractional extrema."""
import itertools,json,csv
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix,vstack
from scipy.optimize import linprog

def build(data,cid,policy):
 d=Path(data);contexts=json.loads((d/'contexts.json').read_text());c=next(x for x in contexts if x['id']==cid);benchmark=json.loads((d/'benchmark.json').read_text())
 ms=[x for x in itertools.product([0,1],repeat=2) if x[0]<=x[1]]
 ss=[x for x in itertools.product([0,1],repeat=4) if x[0]<=x[1] and x[0]<=x[2] and x[1]<=x[3] and x[2]<=x[3]]
 ys=[x for x in itertools.product([0,1],repeat=4) if x[0]<=x[1] and x[2]<=x[3]]
 # Materialize the inner iterator before reuse, and use a different column order than the main oracle.
 types=list(itertools.product(ys,ms,ss,[0,1],list(itertools.product([0,1],repeat=2))))
 n=len(types)
 with (d/'tables.csv').open() as stream:rows=list(csv.DictReader(stream))
 protocols=['natural','priming_trial','rescue_trial','sequential_trial'];target=[]
 records={(r['lab'],r['protocol'],int(r['Z']),int(r['A']),int(r['W']),int(r['B']),int(r['S']),r['Y']):float(r['probability']) for r in rows if r['context']==cid}
 for lab in c['labs']:
  for design in protocols:
   for z,a,w,b in itertools.product([0,1],repeat=4):
    for s,y in [(0,'NA'),(1,'0'),(1,'1')]:target.append(records[(lab['id'],design,z,a,w,b,s,y)])
 rr=[];cc=[];vv=[];num=np.zeros(2*n);den=np.zeros(2*n)
 for x in [0,1]:
  for i,(Y,M,S,A,B) in enumerate(types):
   col=x*n+i
   for z,e in itertools.product([0,1],repeat=2):
    pr1=c['z_false_positive'] if x==0 else 1-c['z_false_negative'];pe=c['image_flip'] if e else 1-c['image_flip'];pz=pr1 if z else 1-pr1
    def world(p):
     a=p['a'][z];m=M[a];w=m^e;b=p['b'][z][w];return S[2*m+b],Y[2*m+b]
    s,y=world(policy);sb,yb=world(benchmark);weight=(c['target_x1'] if x else 1-c['target_x1'])*pz*pe;den[col]+=weight*s*sb;num[col]+=weight*s*sb*(y-yb)
    for lab_index,lab in enumerate(c['labs']):
     px=lab['x1'] if x else 1-lab['x1']
     for design_index,design in enumerate(protocols):
      aas=[(A,1.)] if design in ['natural','rescue_trial'] else [(0,.55),(1,.45)]
      for a,pa in aas:
       m=M[a];w=m^e;q=.7 if w==0 else .35;bs=[(B[w],1.)] if design in ['natural','priming_trial'] else [(0,1-q),(1,q)]
       for b,pb in bs:
        s=S[2*m+b];y=Y[2*m+b];out=0 if not s else 1+y;cell=(((z*2+a)*2+w)*2+b)*3+out;row=(lab_index*4+design_index)*48+cell;rr.append(row);cc.append(col);vv.append(px*pz*pe*pa*pb)
 A=coo_matrix((vv,(rr,cc)),shape=(384,2*n)).tocsr();target=np.array(target);band=c['probability_band'];E=coo_matrix((np.ones(2*n),(np.repeat([0,1],n),np.arange(2*n))),shape=(2,2*n)).tocsr()
 P={'A_ub':vstack([A,-A],format='csr'),'b_ub':np.r_[target+band,-target+band],'A_eq':E,'b_eq':np.ones(2),'bounds':(0,None)}
 return P,num,den

def support(P,obj):
 r=linprog(obj,**P,method='highs',options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
 if not r.success:raise ValueError(r.message)
 return float(r.fun)

def fractional_bisection(P,num,den,upper=False,iterations=21):
 lo,hi=-1.,1.
 for _ in range(iterations):
  middle=(lo+hi)/2
  value=-support(P,-num+middle*den) if upper else support(P,num-middle*den)
  if value>0:lo=middle
  else:hi=middle
 return (lo+hi)/2
