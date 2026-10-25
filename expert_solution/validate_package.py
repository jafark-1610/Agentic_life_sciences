"""Package-side slot and structure preflight, without claiming platform UI access."""
from pathlib import Path
import json,argparse,ast,hashlib
HERE=Path(__file__).resolve().parent

def validate(root):
 root=Path(root);expected=['run_pipeline.py','final_answer.json','analysis.md']
 assert {'task','expert_solution','README.md'}=={p.name for p in root.iterdir() if p.name!='.git'}
 for name in ['deliverables.json','required_deliverables.json']:assert json.loads((root/'task'/name).read_text())==expected
 assert json.loads((root/'expert_solution/config/parameters.yaml').read_text())['required_deliverables']==expected
 assert 'Required deliverables: '+', '.join(expected) in (root/'task/prompt.md').read_text()
 assert not any('run_summary' in p.read_text() for p in (root/'task').rglob('*') if p.is_file())
 for name in ['run_pipeline.py','expert_solution.py','final_answer.json','rubric.md','rubric.json','score_rubric.py','config/parameters.yaml','results/run_summary.json']:
  assert (root/'expert_solution'/name).is_file(),name
 summary=json.loads((root/'expert_solution/results/run_summary.json').read_text())
 assert summary['status']=='success' and summary['case_id']=='ALS_PAIRED_IMMUNITY_003'
 assert summary['required_deliverables']==expected
 assert summary['answer_sha256']==hashlib.sha256((root/'expert_solution/final_answer.json').read_bytes()).hexdigest()
 assert summary['data_manifest_sha256']==hashlib.sha256((root/'task/data/data_manifest.json').read_bytes()).hexdigest()
 for p in root.rglob('*.py'):ast.parse(p.read_text(),filename=str(p.relative_to(root)))
 assert not any(p.name in ['.DS_Store','__pycache__'] or p.suffix in ['.pyc','.pyo'] for p in root.rglob('*'))
 return {'status':'success','required_slots':expected,'checked_against':'user-reported existing three slots','platform_ingestion_and_UI_state':'not accessible from this package; not claimed verified'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=HERE.parent);a=p.parse_args();print(json.dumps(validate(a.root),indent=2))
