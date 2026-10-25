# Paired-clone immune policy pipeline

The pipeline infers sharp same-clone causal bounds from genotype-mixture assay tables, then selects a resource-adjusted immune rescue policy under viability and harm constraints.

`task/` contains the scientific model, population tables, policy menu, schemas, input validator and flat three-file submission contract. `expert_solution/` contains the executable oracle, canonical answer, grader, independent calculations, scientific controls and isolated submitted-code verifier.

From the package root with Python 3.11+, numpy, scipy and jsonschema available:

```bash
export PYTHONDONTWRITEBYTECODE=1
python task/data/validate_dataset.py
python expert_solution/validate_package.py
python expert_solution/run_pipeline.py --data task/data --output-dir expert_solution/results
python expert_solution/score_rubric.py --answer expert_solution/results/final_answer.json --artifacts-dir expert_solution/results
python -m unittest discover -s expert_solution/tests -v
python expert_solution/robustness_checks/run_checks.py
python expert_solution/build_rubric_md.py --check
python expert_solution/freeze_package.py --check
```

The solver submission slots are exactly `run_pipeline.py`, `final_answer.json` and `analysis.md`. The pipeline writes the latter two in its requested output directory. Task dependency files are provided inputs.

For complete source execution and regenerated-input verification on Linux with bubblewrap and user/network namespaces:

```bash
python expert_solution/verify_submission.py --solver expert_solution --data task/data --output-dir /tmp/paired-immunity-verification --replay-control
```

Replace the solver path to evaluate another submission. The verifier mounts only public task and submitted source files, checks private-file and network isolation, and evaluates original and physically regenerated population tables. Missing namespace capability is reported as blocked. The verifier records execution metadata separately from solver deliverables.
