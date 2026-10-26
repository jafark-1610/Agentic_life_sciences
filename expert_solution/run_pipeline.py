"""Offline entry point for joint thermodynamic inference."""
import os
import sys
sys.dont_write_bytecode = True
for variable in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[variable] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=here/'config/parameters.yaml')
    args = parser.parse_args()
    started = time.monotonic()
    runpy.run_path(str(args.data/'validate_dataset.py'))['validate'](args.data)
    config = json.loads(args.config.read_text())
    answer, diagnostics, D = analyse(args.data, config)
    answer = write_outputs(answer, D, args.output_dir)
    jsonschema.validate(answer, json.loads((args.data/'output_schema.json').read_text()))
    record = dict(case_id=answer['case_id'], status='success', exit_code=0,
                  role='expert_execution_metadata', seconds=round(time.monotonic()-started, 3),
                  python=platform.python_version(),
                  dependencies={p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'jsonschema']},
                  required_deliverables=config['required_deliverables'],
                  answer_sha256=hashlib.sha256((args.output_dir/'final_answer.json').read_bytes()).hexdigest(),
                  data_manifest_sha256=hashlib.sha256((args.data/'data_manifest.json').read_bytes()).hexdigest(),
                  configuration=config, diagnostics=diagnostics)
    # This record belongs only to the expert package, outside the three solver slots.
    (args.output_dir/'run_summary.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': 'success', 'seconds': record['seconds'], 'proteins': len(answer['proteins'])}))


if __name__ == '__main__':
    main()
