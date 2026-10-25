# ALS_FLUX_RESCUE_001

## Rescue design under isotope-constrained metabolic uncertainty

Eight independent synthetic cultures represent steady-state metabolic stress environments. Choose one three-module rescue design to use unchanged in every environment. Your deliverable is a robust decision and a quantitative account of what the assays do and do not identify. These are simulated microbial methods-study data, not clinical observations.

### Supplied model and measurements

All inputs are in `data/`. `network.json` defines the order of 32 irreversible flux coordinates, nine intracellular balance equations, and their stoichiometric matrix S. A feasible flux v satisfies S v = 0 and the culture-specific inclusive lower and upper capacity bounds in `cultures.json`. Carbon pools are carbon-equivalent amounts; cofactor rows have their stated model units. Carbon losses at PDH represent unmodelled external CO2. The network is the complete stipulated reduced model; do not replace its coefficients using external pathways or atom maps.

`assay_panel.json` supplies channels, a calibrated matrix H, and a group index for every channel. The assay is a linear tracer-flux fingerprint. It is NOT a raw isotope mass-isotopomer distribution and its entries need not be positive or sum to one. In culture s, channel j has a reported value y_j and a deterministic absolute error bound e_j:

    abs(H[j] @ v + b[group[j]] - y_j) <= e_j.

The four additive calibration offsets b are unknown. All channels in the same group share that offset. Every supplied standard with known level k, observed level z, group g and halfwidth e imposes

    abs(k + b[g] - z) <= e.

The explicit offset bounds also apply. Each culture has its own four offsets; no offset is shared across cultures. Every observation and standard participates. Bounds represent simultaneous admissible errors, not standard deviations or independent statistical confidence intervals. No probability distribution over feasible states is specified. Denote the JOINT feasible flux/offset set in culture s by P_s. Uncertainty in b must be retained when projecting P_s onto flux space.

### Intervention model

`design_rules.json` lists module IDs, groups, costs, a budget and incompatible pairs. A legal design contains exactly one module from each of the uptake, redox and export groups, costs no more than the budget, and contains neither full incompatible pair. Module order has no scientific meaning. The design menu is the complete set satisfying these rules; it must be enumerated from the input.

Each culture supplies a baseline intercept and flux coefficients, plus an intercept and coefficient vector for each module. Under the stipulated first-order response model, rescue utility is

    U_s(p,v) = baseline_intercept_s + baseline_coefficients_s @ v
               + sum(intercept_s[m] + coefficients_s[m] @ v for m in p).

Utility is dimensionless, can be negative, and depends on flux but not directly on assay offsets. These response coefficients are exact for this task. They describe utility conditional on the pre-intervention steady state. They do not alter S, H, capacities or P_s, and no post-intervention flux-balance reoptimization is requested.

### Decision

For every legal design p, determine the lower utility envelope and maximum opportunity regret:

    L_s(p) = min_{(v,b) in P_s} U_s(p,v)
    R_s(p) = max_{(v,b) in P_s} [max_{q legal} U_s(q,v) - U_s(p,v)]
    L(p)   = min_s L_s(p)
    R(p)   = max_s R_s(p).

Both terms in a utility difference refer to the SAME feasible flux state in the SAME culture. The challenger q ranges over the entire legal menu, including designs whose global safety floor fails. A safety-ineligible challenger remains a legitimate per-state opportunity benchmark. There is no distribution or averaging over cultures. The empty design is not in the menu. R_s is nonnegative because q=p is allowed.

A design is safe when L(p) >= `design_rules.json -> safety_floor`. Select a safe design minimizing R(p). If none is safe, return `no_robust_rescue`. When exact minimizers tie within `study_metadata.json -> tie_tolerance`, a lexicographically smallest sorted module tuple is a convenient canonical choice. Evaluation accepts any legal safe design within `selection_regret_slack` of the smallest achievable safe regret; that numerical slack does not relax the safety rule. Safety comparisons use `tie_tolerance` only for floating-point equality at the boundary.

### Deliverables

Create `run_pipeline.py` and `requirements.txt` in your working `solver_solution/` directory, with `task/` as a read-only sibling. The pipeline must derive its outputs from the staged inputs at runtime, work offline, and accept arbitrary paths:

    python run_pipeline.py --data ../task/data --output-dir results

Write `results/final_answer.json` and `results/analysis.md`. Do not read evaluator files, use external data, embed calculated outputs in executable code, or install packages during execution. Python 3.11+, numpy, scipy and jsonschema are available. Additional packages are unnecessary. Validate the input before analysis:

    python ../task/data/validate_dataset.py --data ../task/data

`data/output_schema.json` defines the complete output structure. Output strict finite JSON with no duplicate keys. Each supplied culture, reaction and legal design must occur exactly once; every design must contain each culture once. Match by IDs, not input or output row order. Module arrays can be in any order.

Top-level fields:

* `schema`: `flux_rescue/1`.
* `case_id`: `ALS_FLUX_RESCUE_001`.
* `cultures`: eight objects, each with `id` and `flux_ranges`. For every reaction, report `reaction`, `lower`, `upper`, and `identifiable`. The endpoints are the minimum and maximum of that individual flux over P_s. `identifiable` is true exactly when upper minus lower is at most `acceptance.identifiable_width`. This is an operational width criterion, not a claim of statistical confidence or of point identification. Do not constrain one reaction to the midpoint of another's range.
* `designs`: one object for EVERY legal design, with `modules`, global `floor` L(p), global `regret` R(p), and `by_culture`. Each `by_culture` object has `culture`, `floor` L_s(p), and `regret` R_s(p). Report unrounded scientific quantities; JSON decimal precision is otherwise unrestricted.
* `selection`: `status`, `modules`, `witness`. With a selected design, status is `selected`, modules are that design, and witness is the object described next. With no safe design, status is `no_robust_rescue`, modules is an empty list and witness is null.

### Adversarial witness

For a selected design p, supply one feasible state and legal challenger attaining R(p), not a separate state per utility term. `witness` contains `culture` (a supplied ID), `challenger` (three module IDs), `flux` (32 numbers in network reaction order), `offsets` (four numbers in offset-group order), and `regret` (the utility gap U_s(q,v)-U_s(p,v) at that state). Degenerate optima may use any feasible maximizing state. Do not report a box corner assembled from marginal flux ranges unless it is jointly feasible.

### Acceptance and analysis

All acceptance tolerances are published in `study_metadata.json -> acceptance`. Every flux endpoint and every per-culture and global floor/regret must agree with the scientific optimum within `numeric_abs`, an absolute tolerance. Identifiability flags must match the width definition. Selection must satisfy the decision criterion above. Witness inequalities, bounds and mass balance must hold within `witness_feasibility_abs`; both its actual utility gap and reported regret must attain the selected design's true global regret within `witness_objective_abs` (the reported regret must also agree with its recomputed gap within `numeric_abs`). Every scientific group is required for acceptance. Any computational method producing these quantities is accepted.

In `analysis.md`, describe your uncertainty representation, how the design menu and decision were computed, at least one numerical identifiability diagnostic and one numerical decision diagnostic, and the biological/model limitations. Claims based only on fitting residuals do not establish that a decision is robust. This report and runtime provenance are reviewed alongside the numerical rubric; the executable numeric grader does not award points for unverified textual claims.

Missing or malformed numerical content fails the corresponding scientific group. An unreadable answer, nonfinite JSON or duplicate-key JSON cannot be graded and receives zero. Other schema deviations incur one presentation deduction and leave scientific calculations unchanged where the fields remain readable. No required numerical field is silently inferred from an explanation. Presentation alone does not create a scientific failure.
