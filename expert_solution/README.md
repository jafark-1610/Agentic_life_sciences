# Population kinetics and sharp policy envelopes

The pipeline separates the persistent subtype distributions, reconstructs all locally compatible continuous-time cycles, applies the shared bulk turnover calibration, and computes conditional intervention envelopes over the surviving joint models.

    python run_pipeline.py --data ../task/data --output-dir results --config config/parameters.yaml

`kinetics.py` handles the state model, observation law, and competing first passage. `envelopes.py` filters joint microscopic models and computes sharp extrema. `expert_solution.py` builds the answer. `artifacts.py` computes the witness diagnostics. The configuration file is JSON-compatible YAML and is consumed at runtime. `results/run_summary.json` records the expert execution, hashes, versions, and candidate telemetry; it is outside the solver slots.

`private/truth.json` stores the simulation invariants. `private/expected_answer.json` is independently computed from them by `compute_truth.py`. The inference pipeline does not read either file. `build_rubric_md.py` generates the machine rubric, explicit numerical comparison items, and human rubric. `score_rubric.py` accepts any method meeting the public limits and checks arbitrary attaining witnesses.

    PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
    python robustness_checks/run_checks.py
    python validate_package.py
    python freeze_package.py --check

`tests/independent_oracle.py` checks tensor recovery and the filtered uncertainty set by a different numerical route. `source_archive/generate_data.py` recreates the simulated observations and protocols. `export_solver.py` produces a temporary self-contained computational entry point for `verify_submission.py`, which executes original and regenerated inputs with private files and network access unavailable. `evaluation_status.json` records external model evaluation status.
