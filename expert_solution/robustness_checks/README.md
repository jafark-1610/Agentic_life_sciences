# Scientific controls

Run `python robustness_checks/run_checks.py` from `expert_solution/`. The workflow checks numerical clearance, the binding-equivalent baseline energy reflection, two-stage latent-energy extrapolation, evidence calculations, presentation recovery, and an independent transformed-energy estimator. Denaturant conditions are signed offsets from a positive baseline concentration.

`baselines.py` implements the two-stage control. The measured-variant diagnostics are recorded before sequence projection; the final projected outputs are graded separately. `result.json` records metrics and interpretations, and `result.md` indexes the check outcomes.

The isolated runtime and regenerated-input experiment is executed by `verify_submission.py`. Artifact grading, scientific controls, and isolated execution have distinct records.
