"""Preflight exact ALS paths, slots, schema, hashes, and source syntax."""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import jsonschema
HERE = Path(__file__).resolve().parent


def validate(root):
    root = Path(root); expert = root/'expert_solution'; task = root/'task'
    assert {p.name for p in root.iterdir() if p.name != '.git'} == {'task', 'expert_solution', 'README.md'}
    slots = ['run_pipeline.py', 'final_answer.json', 'analysis.md']
    for name in ['deliverables.json', 'required_deliverables.json']:
        assert json.loads((task/name).read_text()) == slots
    assert 'Required deliverables: '+', '.join(slots) in (task/'prompt.md').read_text()
    assert not any('run_summary' in p.read_text() for p in task.rglob('*') if p.is_file() and p.suffix != '.npz')
    required = ['run_pipeline.py', 'expert_solution.py', 'final_answer.json', 'rubric.json', 'rubric.md',
                'score_rubric.py', 'config/parameters.yaml', 'results/run_summary.json', 'results/final_answer.json',
                'results/analysis.md', 'tests/test_package.py', 'robustness_checks/run_checks.py']
    for name in required: assert (expert/name).is_file(), 'Missing exact path: expert_solution/'+name
    cfg = json.loads((expert/'config/parameters.yaml').read_text())
    assert cfg['required_deliverables'] == slots
    summary = json.loads((expert/'results/run_summary.json').read_text())
    assert summary['status'] == 'success' and summary['exit_code'] == 0 and summary['case_id'] == cfg['case_id']
    assert summary['required_deliverables'] == slots
    assert summary['answer_sha256'] == hashlib.sha256((expert/'final_answer.json').read_bytes()).hexdigest()
    assert summary['data_manifest_sha256'] == hashlib.sha256((task/'data/data_manifest.json').read_bytes()).hexdigest()
    assert (expert/'final_answer.json').read_bytes() == (expert/'results/final_answer.json').read_bytes()
    jsonschema.validate(json.loads((expert/'final_answer.json').read_text()), json.loads((task/'data/output_schema.json').read_text()))
    for p in root.rglob('*'):
        if '.git' in p.parts: continue
        assert not p.is_symlink(), str(p)
        assert p.name not in ['.DS_Store', '__pycache__'] and p.suffix not in ['.pyc', '.pyo'], str(p)
        if p.suffix == '.py': ast.parse(p.read_text(), filename=str(p.relative_to(root)))
        if p.name == 'README.md':
            lower = p.read_text().lower()
            assert all(token not in lower for token in ['reference task', 'sample task', 'pipeline size', '100 mb', '100mb'])
    return {'status': 'success', 'required_solver_slots': slots, 'required_expert_paths_checked': required,
            'platform_import_status': 'requires upload and platform validation; package preflight does not inspect UI state'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, default=HERE.parent); a = p.parse_args()
    print(json.dumps(validate(a.root), indent=2))
