from pathlib import Path
import hashlib,json,argparse
ROOT=Path(__file__).resolve().parent.parent
EXCLUDED={'expert_solution/freeze_manifest.json','expert_solution/evaluation_status.json','expert_solution/tests/result.json','expert_solution/robustness_checks/result.json','expert_solution/robustness_checks/result.md','expert_solution/rubric_results.json','expert_solution/rubric_results.md'}
def snapshot():
 result={}
 for name in ['task','expert_solution']:
  for p in sorted((ROOT/name).rglob('*')):
   if not p.is_file():continue
   rel=p.relative_to(ROOT).as_posix()
   if rel in EXCLUDED or rel.startswith('expert_solution/results/') or '__pycache__' in p.parts or p.suffix in ['.pyc','.pyo']:continue
   result[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 result['README.md']=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest();return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();path=ROOT/'expert_solution/freeze_manifest.json';now=snapshot()
 if a.check:assert json.loads(path.read_text())['sha256']==now,'Frozen scientific content changed'
 else:path.write_text(json.dumps({'policy':'Scientific inputs, source, grading and canonical answer frozen; generated execution evidence excluded','sha256':now},indent=2)+'\n')
 print('freeze verified' if a.check else 'freeze created',len(now),'files')
