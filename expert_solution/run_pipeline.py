"""Offline persistent-cycle inference and certified finite-family optimization."""
import os
import sys
sys.dont_write_bytecode = True
for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']: os.environ[variable] = '1'
import argparse
import hashlib
import importlib.metadata
import json
import platform
import runpy
import time
from pathlib import Path
import jsonschema
from expert_solution import analyse
from artifacts import write_outputs


def main():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True); p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--config', type=Path, default=here/'config/parameters.yaml'); a = p.parse_args()
    start = time.monotonic()
    runpy.run_path(str(a.data/'validate_dataset.py'))['validate'](a.data)
    config = json.loads(a.config.read_text())
    answer, D, telemetry = analyse(a.data, config)
    answer = write_outputs(answer, D, a.output_dir)
    jsonschema.validate(answer, json.loads((a.data/'output_schema.json').read_text()))
    record = dict(case_id=answer['case_id'], status='success', exit_code=0,
                  role='expert_execution_metadata_outside_solver_slots', seconds=round(time.monotonic()-start, 3),
                  python=platform.python_version(), dependencies={p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'jsonschema']},
                  required_deliverables=config['required_deliverables'], configuration=config, telemetry=telemetry,
                  answer_sha256=hashlib.sha256((a.output_dir/'final_answer.json').read_bytes()).hexdigest(),
                  data_manifest_sha256=hashlib.sha256((a.data/'data_manifest.json').read_bytes()).hexdigest())
    (a.output_dir/'run_summary.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': 'success', 'seconds': record['seconds'], 'preparations': len(answer['preparations'])}))


if __name__ == '__main__': main()
