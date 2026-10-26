"""Construct the target from exact simulation invariants, bypassing tensor inference."""
import os
import sys
sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS'] = '1'
from itertools import product
from pathlib import Path
import json
import numpy as np
from kinetics import read_json, generator, observable
from expert_solution import analyse
from artifacts import round_values
HERE = Path(__file__).resolve().parent


def exact_families(panel, meta, truth):
    info = truth['preparations'][panel['id']]
    families, scores = [], []
    lower, upper = meta['rate_bounds']['cycle_rate']; dt = meta['frame_time']
    for h, weight in enumerate(info['weights']):
        R = np.array(info['exchange'][h]); sums = np.array(info['sums'][h]); phases = np.array(info['phases'][h])
        options = []
        limit = int(np.ceil(dt*np.sqrt(3)/2*(upper-lower)/(2*np.pi)))+2
        for s, phase in zip(sums, phases):
            possible=[]
            for k in range(-limit, limit+1):
                diff=(phase+2*np.pi*k)/(dt*np.sqrt(3)/2); f,b=(s+diff)/2,(s-diff)/2
                if lower <= min(f,b) and max(f,b) <= upper: possible.append(k)
            options.append(possible)
        models, codes = [], []
        for code in product(*options):
            difference=(phases+2*np.pi*np.array(code))/(dt*np.sqrt(3)/2)
            models.append(np.column_stack([(sums+difference)/2,(sums-difference)/2])); codes.append(list(code))
        family = dict(weight=weight, exchange=R, sums=sums, phases=phases, models=np.array(models), codes=codes)
        Q=generator(R,models[0]);a=observable(Q,panel['arrays']['response'],dt)
        scores.append(a.reshape(meta['modules'],meta['states'])[:,:3].sum());families.append(family)
    order=np.argsort(scores)
    families=[families[i] for i in order]
    return np.array([f['weight'] for f in families]),families


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--truth',type=Path,default=HERE/'private/truth.json');p.add_argument('--output',type=Path,default=HERE/'private/expected_answer.json');a=p.parse_args()
    truth=read_json(a.truth);config=read_json(HERE/'config/parameters.yaml')
    answer,_,telemetry=analyse(a.data,config,family_override=lambda panel,meta:exact_families(panel,meta,truth))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(round_values(answer),separators=(',',':'))+'\n')
    print(json.dumps({'status':'success','role':'exact_simulation_invariants','preparations':len(telemetry)}))
