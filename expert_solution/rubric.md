# Persistent-cycle intervention rubric

Generated from `rubric.json`, public metadata, and exact simulation-derived targets.

8 preparations; 64 policies per preparation. Every scientific requirement is mandatory.

| Group | Package points | Fields |
|---|---:|---|
|identification|10|mixture_weights, exchange_generators, forward_bounds, backward_bounds, candidate_counts, retention_bounds|
|retained_entropy|10|retained_epr_bounds|
|policy_probabilities|15|policies[].success_bounds, policies[].loss_bounds, policies[].cost_bounds|
|joint_gain_and_net|25|policies[].gain_bounds, policies[].net_bounds|
|robust_choice|30|selected_policy|
|attaining_witnesses|5|net_witnesses|

Each group is divided equally across preparations and earns credit when all its requirements pass. The calculated report earns 5 further points.

A scientific failure caps the score at 79. Passing is 80 or greater. Recoverable presentation deviations cost 5 once after any cap and never activate a scientific cap.

| Quantity | Absolute tolerance |
|---|---:|
|mixture|5e-05|
|exchange|5e-05|
|cycle_bounds|0.003|
|retention|0.0015|
|epr|0.02|
|probability_bounds|0.0015|
|gain_bounds|0.002|
|net_bounds|0.002|
|choice_regret|0.003|
|witness_rates|0.003|
|witness_endpoint|0.003|
|witness_turnover|1e-05|

`comparison_items` contains every fixed expected value, field path, group and tolerance. Policy choices are accepted from computed regret sets, rather than one canonical identifier. Witnesses are checked physically and may differ from the canonical witnesses. Candidate counts are exact integers.

The report evidence is recomputed from submitted physical rates and public arrays. Artifact grading does not establish execution. The isolated verifier runs original and regenerated experiments with private files inaccessible. Missing/non-running code, unreadable answers, or demonstrated stored/external answers receive zero; infrastructure failures are BLOCKED.
