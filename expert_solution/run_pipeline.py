"""Offline oracle; writes exactly the two configured output artifacts."""
import argparse,json,time,subprocess,sys
from pathlib import Path
import jsonschema
from expert_solution import load,analyse
from artifacts import stable,write_outputs
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=HERE.parent/'task/data');p.add_argument('--output-dir',type=Path,default=HERE/'results');p.add_argument('--config',type=Path,default=HERE/'config/parameters.yaml');a=p.parse_args();t=time.monotonic();config=json.loads(a.config.read_text());assert config['case_id']=='ALS_PAIRED_IMMUNITY_003'
 subprocess.run([sys.executable,str(a.data/'validate_dataset.py'),'--data',str(a.data)],check=True)
 D=load(a.data);answer=stable(analyse(a.data));jsonschema.validate(answer,json.loads((a.data/'output_schema.json').read_text()));write_outputs(answer,D,a.output_dir)
 print(json.dumps({'status':'success','case_id':answer['case_id'],'elapsed_seconds':round(time.monotonic()-t,3),'outputs':['final_answer.json','analysis.md']}))
