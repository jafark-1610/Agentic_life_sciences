from pathlib import Path
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parent.parent
EXCLUDED={'expert_solution/freeze_manifest.json','expert_solution/evaluation_status.json','expert_solution/rubric_results.json','expert_solution/rubric_results.md','expert_solution/tests/result.json','expert_solution/robustness_checks/result.json','expert_solution/robustness_checks/result.md'}
def snapshot():
 out={}
 for d in ['task','expert_solution']:
  for p in sorted((ROOT/d).rglob('*')):
   if not p.is_file():continue
   name=p.relative_to(ROOT).as_posix()
   if name in EXCLUDED or name.startswith('expert_solution/results/') or '__pycache__' in p.parts or p.suffix in ['.pyc','.pyo']:continue
   out[name]=hashlib.sha256(p.read_bytes()).hexdigest()
 out['README.md']=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest();return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();path=ROOT/'expert_solution/freeze_manifest.json';now=snapshot()
 if a.check:assert json.loads(path.read_text())['sha256']==now,'scientific package changed'
 else:path.write_text(json.dumps({'policy':'Scientific content frozen; generated execution evidence excluded','sha256':now},indent=2)+'\n')
 print('freeze verified' if a.check else 'freeze created',len(now),'files')
