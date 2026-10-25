# Scientific validation workflow

Run `python expert_solution/robustness_checks/run_checks.py` from the package root. It checks independently assembled conditional bounds using bisection, evaluates a compatible point-law decision and an independent-world approximation, audits separate-extrema ratio enclosures, verifies reference gate clearance and presentation recovery, and checks the exact three-slot contract.

The wrong-method controls reproduce factual information yet can miss the target paired-clone quantity. They are not Meta Muse or other solver-model trials. Approximations that fall within the public numeric tolerance are not counted as demonstrated scientific failures. Recorded result fields explicitly distinguish these cases.

Use the full verifier separately for actual submitted-code isolation and regenerated-input checks. Its completed evidence is stored under `../results/verification_result.json`.
