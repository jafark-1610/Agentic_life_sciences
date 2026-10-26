"""Scientific wrong-method controls and convexification audit."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from envelopes import joint_bounds


def single_compatible_model(statistics,weights,metric,tolerance=1e-12,joint=None):
    # Regularize an exactly fitting preparation toward minimum retained dissipation.
    _,indices,_=joint_bounds(statistics,weights,'retained_epr',joint=joint)
    point=indices[0]
    width=1 if metric=='retention' else statistics[0][metric].shape[1]
    denominator=sum(w*s['d'][point[h]] for h,(w,s) in enumerate(zip(weights,statistics)))
    if metric=='retention':values=np.array([denominator])
    else:values=sum(w*s[metric][point[h]] for h,(w,s) in enumerate(zip(weights,statistics)))/denominator
    witnesses=np.repeat(point[None,:],width,axis=0)
    return np.column_stack([values,values]),witnesses,witnesses


def separate_endpoint_extrema(statistics,weights,metric,tolerance=1e-12,joint=None):
    exact,lo,hi=joint_bounds(statistics,weights,metric,joint=joint)
    if metric not in ['gain','net']:return exact,lo,hi
    success,_,_=joint_bounds(statistics,weights,'success',joint=joint)
    loss,_,_=joint_bounds(statistics,weights,'loss',joint=joint)
    cost,_,_=joint_bounds(statistics,weights,'cost',joint=joint)
    eta=separate_endpoint_extrema.loss_penalty;lam=separate_endpoint_extrema.resource_penalty
    lower=success[:,0]-success[0,1]-eta*(loss[:,1]-loss[0,0])
    upper=success[:,1]-success[0,0]-eta*(loss[:,0]-loss[0,1])
    if metric=='net':lower-=lam*cost[:,1];upper-=lam*cost[:,0]
    return np.column_stack([lower,upper]),lo,hi


def convexified_endpoint(statistics,weights,calibration,metric,column,minimize=True):
    sizes=[len(s['d']) for s in statistics];offset=np.cumsum([0,*sizes]);count=int(offset[-1]);t=count
    eq=lil_matrix((len(sizes)+1,count+1));rhs=np.zeros(len(sizes)+1)
    objective=np.zeros(count+1);flux=np.zeros(count+1)
    for h,(s,w) in enumerate(zip(statistics,weights)):
        sl=slice(offset[h],offset[h+1]);eq[h,sl]=1;eq[h,t]=-1
        eq[-1,sl]=w*s['d'];objective[sl]=w*s[metric][:,column];flux[sl]=w*s['flux']
    rhs[-1]=1
    inequalities=np.vstack([flux,-flux]);inequalities[0,t]=-calibration['upper'];inequalities[1,t]=calibration['lower']
    fit=linprog(objective if minimize else -objective,A_ub=inequalities,b_ub=np.zeros(2),A_eq=eq.tocsr(),b_eq=rhs,bounds=(0,None),method='highs')
    assert fit.success,fit.message
    value=float(fit.fun if minimize else -fit.fun)
    proportions=[fit.x[offset[h]:offset[h+1]]/fit.x[t] for h in range(len(sizes))]
    return value,[int(np.sum(p>1e-6)) for p in proportions]
