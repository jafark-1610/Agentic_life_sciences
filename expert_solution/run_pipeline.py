import os,sys
sys.dont_write_bytecode=True
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json,time,hashlib,platform
from pathlib import Path
import jsonschema
from analysis_engine import analyse
from artifacts import write_outputs
def main():
 here=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--config',type=Path,default=here/'config/parameters.yaml');a=p.parse_args();start=time.monotonic();config=json.loads(a.config.read_text());answer,d=analyse(a.data,config);write_outputs(answer,a.output_dir);jsonschema.validate(answer,json.loads((a.data/'output_schema.json').read_text()));record={'case_id':answer['case_id'],'status':'success','exit_code':0,'seconds':time.monotonic()-start,'python':platform.python_version(),'required_deliverables':config['required_deliverables'],'configuration':config,'diagnostics':d,'answer_sha256':hashlib.sha256((a.output_dir/'final_answer.json').read_bytes()).hexdigest(),'data_manifest_sha256':hashlib.sha256((a.data/'data_manifest.json').read_bytes()).hexdigest()};(a.output_dir/'run_summary.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':'success','seconds':record['seconds']}))
if __name__=='__main__':main()
