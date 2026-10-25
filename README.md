# Metabolic rescue design pipeline

The pipeline combines steady-state flux constraints, bounded tracer fingerprints and shared calibration standards to select a safe intervention with minimum worst-case opportunity regret.

`task/` contains the problem, data, schema and input validator. `expert_solution/` contains the executable analysis, canonical output, grader, generated rubric, tests and robustness workflow.

Run from the package root with Python 3.11 or newer and numpy, scipy and jsonschema available:

```bash
python task/data/validate_dataset.py
python expert_solution/run_pipeline.py --data task/data --output-dir expert_solution/results
python expert_solution/score_rubric.py --answer expert_solution/results/final_answer.json
python -m unittest discover -s expert_solution/tests -v
python expert_solution/robustness_checks/run_checks.py
python expert_solution/build_rubric_md.py --check
python expert_solution/freeze_package.py --check
```

The analysis writes `final_answer.json`, `analysis.md` and `run_summary.json` in the requested output directory. The grader accepts an answer path and optionally an output path for its numerical evaluation. Tests verify scientific calculations, schema behavior, grading and integrity. The robustness workflow exercises changes of ordering, calibration origin and flux units, and evaluates alternative decision procedures.
