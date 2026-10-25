"""Freeze scientific inputs, executable policy and canonical answer before trials."""
from pathlib import Path
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'expert_solution/freeze_manifest.json'
# Execution evidence changes on reruns and is not an inference or scoring input.
EXCLUDED={'expert_solution/freeze_manifest.json','expert_solution/rubric_results.json','expert_solution/rubric_results.md','expert_solution/robustness_checks/result.json','expert_solution/robustness_checks/result.md','expert_solution/tests/result.json','expert_solution/evaluation_status.json'}
def files():
 result={}
 for parent in [ROOT/'task',ROOT/'expert_solution']:
  for p in sorted(parent.rglob('*')):
   if not p.is_file():continue
   name=p.relative_to(ROOT).as_posix()
   if name in EXCLUDED or name.startswith('expert_solution/results/') or '__pycache__' in p.parts or p.suffix in ['.pyc','.pyo']:continue
   result[name]=hashlib.sha256(p.read_bytes()).hexdigest()
 result['README.md']=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest()
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();current=files()
 if a.check:
  old=json.loads(MANIFEST.read_text());assert old['sha256']==current,'Frozen scientific content changed';print('freeze integrity passed:',len(current),'files')
 else:
  MANIFEST.write_text(json.dumps({'protocol':'sha256; inputs, executable science, grader, rubric, canonical answer and documentation; runtime evidence excluded','sha256':current},indent=2)+'\n');print('scientific package frozen:',len(current),'files')
