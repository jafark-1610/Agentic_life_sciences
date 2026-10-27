"""Reserved-seed population effect coverage, separate from model qualification."""
import os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'source_archive'))
import json,tempfile,numpy as np
from generate_data import generate
from analysis_engine import analyse
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 records=[]
 for seed in range(48040,48045):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);generate(root,seed);a,_=analyse(root/'task/data',{'iterations':65});truth=np.load(root/'expert_solution/private/truth.npz')['effects'];out={}
   for k,p in enumerate(['export','nuclear_decay','cytoplasmic_decay']):
    rows=a['analyses']['base']['genes'];errors=[abs(g['effects'][p]['log2_ratio']-truth[j,k]) for j,g in enumerate(rows)];covered=[g['effects'][p]['interval'][0]<=truth[j,k]<=g['effects'][p]['interval'][1] for j,g in enumerate(rows)];out[p]={'median_absolute_effect_error':float(np.median(errors)),'population_effect_interval_coverage':float(np.mean(covered))}
   records.append({'seed':seed,'results':out});print(seed,flush=True)
 (HERE/'results/reserved_seed_calibration.json').write_text(json.dumps({'role':'simulation accuracy checks, not model runs','records':records},indent=2)+'\n')
