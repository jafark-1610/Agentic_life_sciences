import os,sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json
from pathlib import Path
from analysis_engine import analyse
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--truth');p.add_argument('--output',type=Path,required=True);a=p.parse_args();cfg=json.loads((Path(__file__).resolve().parent/'config/parameters.yaml').read_text());v,diagnostics=analyse(a.data,cfg);a.output.write_text(json.dumps(v,allow_nan=False));print('Computed data-derived statistical benchmark')
