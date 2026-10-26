# Thermodynamic protein design rubric

Generated from `rubric.json`, the public contract, metadata, and canonical answer.

The answer covers 6 binders and 16384 variants per binder, with 1400 measured variants, 12 screen conditions, and 4 competitive challenges. Arrays follow the staged variant order.

Each scientific group is divided equally among binders. Every validity and accuracy requirement is mandatory. An invalid binder block earns no scientific credit for that binder. Any failed scientific gate caps the score at 79. Passing requires 80 points, inclusive.

| Metric | Answer field | Package points | Maximum error |
|---|---|---:|---:|
|energy_rmse|`proteins[].energy`|10|0.3|
|energy_p95|`proteins[].energy`|10|0.6|
|apo_rmse|`proteins[].apo_folded`|20|0.025|
|challenge_rmse|`proteins[].challenge_a`|15|0.02|
|challenge_max_abs|`proteins[].challenge_a`|10|0.12|
|design_regret|`proteins[].selected_variant`|30|0.03|

Error definitions and utility are in the public prompt. The private simulation coefficients generate the scoring truth. A selection within the regret limit receives full decision credit, regardless of tie order or estimator.

The 5 report points require the complete calculated JSON evidence block. An absent or inconsistent block withholds those points and never activates the scientific cap.

| Computed report field | Absolute comparison tolerance |
|---|---:|
|capture_deviance_per_observation|0.05|
|capture_rmse|1e-06|
|mean_apo_folded|1e-06|
|mean_worst_a|1e-06|

Recoverable presentation deviations listed in the public Execution section cost 5 points once, after any scientific cap. They never activate the cap. Missing or unreadable answers and missing or non-running pipelines receive zero. Stored answers and external evidence require documented isolated-execution evidence.

Artifact grading establishes numerical results only. `verify_submission.py` executes the single source file against the published and regenerated inputs with private files inaccessible. Infrastructure failures are blocked checks, not model failures. The generic numeric comparison tolerance is 0.0001; the named scientific limits above are the authoritative accuracy gates.

Canonical answer SHA-256: `9e3b8f9b13b82bb27f84bedee9af893f7c04fc01272715b913b900e3e0cc0cf1`.
