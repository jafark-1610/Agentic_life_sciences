import os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import json,tempfile
from analysis_engine import analyse,load
from artifacts import write_outputs
from score_rubric import assess
m,D=load(HERE.parent/'task/data');expected=json.loads((HERE/'final_answer.json').read_text());checks=[]
for name,option in [('omit_cell_dilution','no_growth'),('assume_complete_transcription_block','no_source'),('treat_fractions_as_pure','no_mixing')]:
 config=json.loads((HERE/'config/parameters.yaml').read_text());config[option]=True;a,d=analyse(HERE.parent/'task/data',config)
 with tempfile.TemporaryDirectory() as tmp:
  write_outputs(a,tmp);r=assess(a,expected,m,(Path(tmp)/'analysis.md').read_text());checks.append({'name':name,'passed':not r['passed'],'score':r['final_score'],'failed_gates':r['failed_gates']})
result={'status':'success' if all(x['passed'] for x in checks) else 'fail','checks':checks,'scope':'Wrong-method numerical controls, not external model attempts.'};(HERE/'robustness_checks/result.json').write_text(json.dumps(result,indent=2)+'\n');(HERE/'robustness_checks/result.md').write_text('# Scientific controls\n\n'+json.dumps(result,indent=2)+'\n');print(result)
