# Thermodynamic inference pipeline

The pipeline calibrates capture background and ceiling, jointly estimates quadratic sequence energies by count likelihood, evaluates the four-state partition sum, and maximizes the manufacturing and occupancy utility.

    python run_pipeline.py --data ../task/data --output-dir results
    python run_pipeline.py --data ../task/data --output-dir results --config config/parameters.yaml

`config/parameters.yaml` is JSON-compatible YAML and is consumed by the optimizer. `model.py` implements inputs and physical probabilities; `expert_solution.py` fits the landscapes; `artifacts.py` serializes predictions and computes the report evidence. `results/run_summary.json` records the expert execution, configuration, hashes, optimizer traces, and runtime. This is expert metadata and is outside the three solver submission slots.

`score_rubric.py` evaluates predictions against `private/truth.json`. `build_rubric_md.py` generates both rubric files using the public grading contract, metadata, and canonical answer. `source_archive/generate_data.py` deterministically regenerates the experiments. The inference code never reads the simulation coefficients.

`analysis.md` contains the calculated output evidence; `method_notes.md` explains identifiability, optimization, sequence extrapolation, and the statistical controls.

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
    python robustness_checks/run_checks.py
    python validate_package.py
    python freeze_package.py --check

`tests/independent_oracle.py` checks the inference by an independent transformed-count route. `export_solver.py` bundles the computational implementation into a temporary single entry point for the isolated-execution verifier. `verify_submission.py` accepts a submitted directory, executes it with only read-only task inputs and runtime libraries mounted, and reruns it on freshly generated measurements. Its results include source hashes and isolation probes. `evaluation_status.json` records which external evaluations remain outstanding.
