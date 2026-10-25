"""Offline, observation-dependent oracle entry point."""
import argparse,json,time,subprocess,sys
from pathlib import Path
import jsonschema
from expert_solution import analyse,load
from artifacts import add_witness,write_outputs
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,default=HERE/'results');p.add_argument('--config',type=Path,default=HERE/'config/parameters.yaml');a=p.parse_args()
 config=json.loads(a.config.read_text());assert config['case_id']=='ALS_TMDD_PULSE_002'
 t=time.monotonic();subprocess.run([sys.executable,str(a.data/'validate_dataset.py'),'--data',str(a.data)],check=True)
 answer=analyse(a.data);D=load(a.data);add_witness(answer,D);jsonschema.validate(answer,json.loads((a.data/'output_schema.json').read_text()));write_outputs(answer,D,a.data,a.output_dir,time.monotonic()-t)
 print(json.dumps({'status':'success','chips':len(answer['chips']),'courses':len(answer['courses']),'seconds':round(time.monotonic()-t,2)}))
if __name__=='__main__':main()
