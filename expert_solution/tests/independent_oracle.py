"""Independent matrix-pencil subtype recovery and a differently ordered global join."""
import os
import sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
from scipy.linalg import eigh,eig


def pencil_decomposition(arrays,rank,contraction):
    _,U=eigh(arrays['moment2']);U=U[:,-rank:]
    direction=np.cos(np.arange(len(U))*.719)+np.sin(np.arange(len(U))*.317)
    contracted=np.tensordot(arrays['moment3'],direction,axes=([2],[0]))
    G=U.T@contracted@U;B=U.T@arrays['moment2']@U
    _,vectors=eig(G@np.linalg.inv(B));vectors=np.real_if_close(vectors).real
    raw=U@vectors;A=raw/raw.sum(axis=0)
    weights=np.linalg.lstsq(A,arrays['moment1'],rcond=None)[0]
    n=len(arrays['response']);m=n//3
    order=np.argsort(A.reshape(m,n,rank)[:,:3,:].sum(axis=(0,1)))
    return weights[order],A[:,order]


def independent_join(statistics,weights,calibration):
    flux=[w*s['flux'] for w,s in zip(weights,statistics)]
    pair=(flux[1][:,None]+flux[2][None,:]).ravel();order=np.argsort(pair);pair=pair[order]
    second=np.repeat(np.arange(len(flux[1])),len(flux[2]))[order]
    third=np.tile(np.arange(len(flux[2])),len(flux[1]))[order]
    rows=[]
    for i,value in enumerate(flux[0]):
        start=np.searchsorted(pair,calibration['lower']-value,side='left')
        end=np.searchsorted(pair,calibration['upper']-value,side='right')
        if end>start:rows.append(np.column_stack([np.full(end-start,i),second[start:end],third[start:end]]))
    assert rows
    return np.concatenate(rows).astype(np.int32)


def independent_bounds(statistics,weights,metric,tolerance=1e-12,joint=None):
    d=np.sum([w*s['d'][joint[:,h]] for h,(w,s) in enumerate(zip(weights,statistics))],axis=0)
    width=1 if metric=='retention' else statistics[0][metric].shape[1]
    values=[];lower=[];upper=[]
    for column in range(width):
        if metric=='retention':v=d
        else:
            n=np.sum([w*s[metric][joint[:,h],column] for h,(w,s) in enumerate(zip(weights,statistics))],axis=0)
            v=n/d
        i,j=int(np.argmin(v)),int(np.argmax(v));values.append([float(v[i]),float(v[j])]);lower.append(joint[i]);upper.append(joint[j])
    return np.array(values),np.array(lower),np.array(upper)


if __name__=='__main__':
    import argparse
    from expert_solution import analyse
    from artifacts import write_outputs
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    cfg=json.loads((Path(__file__).resolve().parents[1]/'config/parameters.yaml').read_text())
    answer,D,telemetry=analyse(a.data,cfg,decomposition=pencil_decomposition,bound_function=independent_bounds,joint_builder=independent_join)
    write_outputs(answer,D,a.output_dir,'Subtype distributions use a matrix-pencil decomposition. Joint calibration is imposed by a reversed pairwise search, and every conditional endpoint is computed by an independent column-wise enumeration of the surviving finite models.')
    (a.output_dir/'independent_diagnostics.json').write_text(json.dumps(telemetry,indent=2)+'\n')
