"""Pin task inputs, computational code, oracle artifacts, and grading definitions."""
import argparse
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent


def snapshot():
    root = HERE.parent
    exclude = {'expert_solution/freeze_manifest.json', 'expert_solution/rubric_results.json',
               'expert_solution/rubric_results.md', 'expert_solution/evaluation_status.json',
               'expert_solution/tests/result.json', 'expert_solution/robustness_checks/result.json',
               'expert_solution/robustness_checks/result.md'}
    files = {}
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or '.git' in p.parts or rel in exclude or rel.startswith('expert_solution/results/'):
            continue
        assert '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.pyo']
        files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(case_id='ALS_THERMODYNAMIC_DESIGN_004', role='scientific_snapshot_before_external_model_runs',
                files=files, excluded_generated_records='results/, test results, robustness results, rubric results, evaluation status; these do not define science or grading')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--check', action='store_true'); a = p.parse_args()
    path = HERE/'freeze_manifest.json'; current = snapshot()
    if a.check: assert json.loads(path.read_text()) == current, 'Scientific snapshot differs from frozen manifest'
    else: path.write_text(json.dumps(current, indent=2)+'\n')
    print(json.dumps({'status': 'success', 'scientific_files': len(current['files'])}))
