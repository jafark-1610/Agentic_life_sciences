# Robustness workflow

Run `python expert_solution/robustness_checks/run_checks.py` from the package root. The workflow checks hidden generation-truth recovery, an independent Radau implementation and finer peak search, reference gate margins, and presentation recovery. It evaluates single-fit and sampled-peak methods as scientific baselines. Those baselines are not model trials. Result files record observations, criteria and pass/fail status.

Runtime isolation, regenerated-measurement input dependence, and stored-answer replay are exercised separately by `verify_submission.py --replay-control`. Their completed evidence is stored in `../results/verification_result.json` when generated.
