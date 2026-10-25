# Chemical-site disposition and pulse-course pipeline

The pipeline calibrates saturable optical sensors, infers all compatible two-site disposition models, and evaluates pulse courses across physiological scenarios. The decision combines target-site occupancy with continuous free-tissue safety limits.

`task/` contains the problem, scientific inputs, schemas and explicit deliverable contract. `expert_solution/` contains the inverse analysis, canonical output, numerical grader, independent checks and isolated submission verifier.

From the package root, with Python 3.11+, numpy, scipy and jsonschema available:

```bash
python task/data/validate_dataset.py
python expert_solution/run_pipeline.py --data task/data --output-dir expert_solution/results
python expert_solution/score_rubric.py --answer expert_solution/results/final_answer.json --artifacts-dir expert_solution/results
python -m unittest discover -s expert_solution/tests -v
python expert_solution/robustness_checks/run_checks.py
python expert_solution/build_rubric_md.py --check
python expert_solution/freeze_package.py --check
```

For full runtime and input-dependence verification on a Linux host with bubblewrap and unprivileged namespaces:

```bash
python expert_solution/verify_submission.py --solver expert_solution --data task/data --output-dir /tmp/tmdd-verification --replay-control
```

A solver submission can replace the `--solver` path. The verifier stages public task files, hides evaluator files, disables network access, reruns the submitted code on original and physically regenerated measurements, and assesses structured diagnostic evidence and output hashes. An unavailable namespace capability is reported as blocked rather than a scientific failure. The numerical JSON grader reports its limited scope separately from complete submission verification.
