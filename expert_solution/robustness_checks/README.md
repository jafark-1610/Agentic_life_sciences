# Robustness pipeline

Run `python expert_solution/robustness_checks/run_checks.py` from the package root. Checks independently rebuild support functions after reversing input order, shifting the calibration origin and rescaling the flux unit. They also compare feasible-point and marginal-box decision procedures to the joint-state decision, verify gate margins and reject scientifically changed answers with the frozen grader. Results distinguish validation checks from baseline procedures; they are not solver model trials.

Each record includes status, observed values and a criterion. A failed baseline is expected when its scientific method does not satisfy the decision problem; a failed invariance or oracle check requires investigation.
