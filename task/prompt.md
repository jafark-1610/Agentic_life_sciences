# Required deliverables

Required deliverables: run_pipeline.py, final_answer.json, analysis.md

These are the only three solver submission slots. `required_deliverables.json` and `deliverables.json` both contain this exact flat filename list. The dependency list in `task/requirements.txt` is supplied task input, not an additional solver submission.

# ALS_PAIRED_IMMUNITY_003

## Paired-clone immune rescue under viability-gated readout

Three synthetic immune-culture cohorts were assayed in two laboratory mixtures under four priming/rescue assignment designs. Choose one assay-adaptive policy for use in every target cohort. The scientific target is a paired-clone contrast among clones that would remain viable under both the proposed policy and the benchmark, with sharp bounds over the entire causal family compatible with the released tables. No patient or clinical efficacy claim is involved.

## Biological and measurement model

For one clone let X be its binary receptor genotype and U its latent biological state. The distribution of U conditional on X can differ between cohorts. Within a cohort it is identical in both laboratories and the target population. The known laboratory and target frequencies of X=1 are in `data/contexts.json`. No other population-transport restriction is imposed.

Z is a noisy baseline genotype assay: P(Z=1|X=0) is z_false_positive, and P(Z=0|X=1) is z_false_negative. Conditional on X, its measurement randomness is independent of U and the imaging variable E. E is Bernoulli(image_flip), independent of X,U,Z and assignment randomization. Z and E are clone attributes in the potential-world model below.

A is the initial priming assignment; M is the true early activation state; W is the recorded activation image; B is the later rescue assignment; S is viability; and Y is binary neutralization capacity. Each satisfies

    M = f_M(A,U)
    W = M XOR E
    S = f_S(M,B,U)
    Y = f_Y(M,B,U).

All arguments and outputs except U are binary. For each fixed U, f_M is nondecreasing in A. f_S is nondecreasing in each of M and B, holding its other argument fixed. For each fixed M,U, f_Y is nondecreasing in B. There is no monotonicity restriction on f_Y in M: early activation can also induce exhaustion. The joint distribution of all biological response functions and natural-assignment functions conditional on X is otherwise unrestricted.

Y is recorded only when S=1. When S=0 its table label is NA, and this cell aggregates both possible latent values of Y. S itself is always observed. NA is not a zero response and is not a separate biological outcome. There are no omitted table cells or finite-sample standard errors.

Natural assignment obeys A=g_A(U), B=g_B(W,U), with arbitrary binary natural-assignment functions. These functions remain properties of the clone in randomized designs even when assignment is overridden. There is no direct effect of laboratory or assignment-design labels on biological functions or measurement laws.

## Assignment designs and tables

In `data/protocols.json`:

* natural: both assignments use their natural functions.
* priming_trial: A is randomized with P(A=1)=0.45; B uses its natural function.
* rescue_trial: A uses its natural function; B is randomized with P(B=1|W=0)=0.7 and P(B=1|W=1)=0.35.
* sequential_trial: both stages use those randomized rules.

Each randomized coin is independent of the biological and assay attributes conditional on its stated design variables. All protocols draw from the same cohort/laboratory population law. Table entries are joint probabilities of (Z,A,W,B,S,Y_recorded), conditional on laboratory and protocol. Do not renormalize the table to viable cultures. Each group has 48 mutually exclusive cells, including zero-valued probabilities.

The supplied population probabilities are rounded to 12 decimal places. An admissible causal law must obey all structural, independence and transport assumptions and predict every released cell within the cohort's probability_band, inclusively. The same law must support every protocol and laboratory of its cohort simultaneously. All admissible laws, including those assigning probability to biological response functions not used by a chosen fitted representation, belong to the scientific uncertainty set. No distributional prior or parametric latent-family restriction is supplied.

## Policy worlds and target quantities

`data/policies.json` is the complete menu. Each policy has a two-entry array a indexed by Z and a 2-by-2 array b indexed first by Z and then W. Its counterfactual world sets A^p=a[Z], M^p=f_M(A^p,U), W^p=M^p XOR E, B^p=b[Z][W^p], followed by the biological S^p,Y^p equations. The benchmark in `data/benchmark.json` uses its own arrays in the same equations. In a paired-clone comparison, X,U,Z,E refer to that same clone in both worlds. The target expectations use target_x1 rather than either laboratory's genotype mixture. All policies start at the first assignment; no policy inherits states or natural assignment from another one.

For policy p, let G_p be the event S^p=1 AND S^benchmark=1. For an admissible target law Q define

    eligibility_p(Q) = P_Q(G_p)
    net_gain_p(Q) = E_Q[Y^p - Y^benchmark | G_p]
    harm_p(Q) = P_Q(Y^p=0, Y^benchmark=1 | G_p)
    cost_p(Q) = E_Q[A^p + rescue_cost*B^p].

The conditioning event belongs to the same paired-clone law as its numerator. The supplied data guarantee strictly positive lower eligibility for every menu policy, so these conditional quantities are defined throughout each admissible set.

For each cohort and policy, report the infimum and supremum of eligibility, the infimum and supremum of net_gain, the supremum of harm, and the supremum of cost over all admissible causal laws for that cohort. These are sharp population-model bounds. Every endpoint is optimized for its own stated quantity; a single fitted distribution is not the requested answer. `point_identified` is true iff the unrounded net-gain interval width is at most acceptance.identification_width. Any correct inference and optimization method is accepted.

For each policy across cohorts report worst_net_gain as the minimum cohort net_gain_lower; worst_harm as the maximum cohort harm_upper; worst_cost as the maximum cohort cost_upper; and minimum_eligibility as the minimum cohort eligibility_lower.

A policy qualifies when worst_harm <= decision.maximum_harm, worst_cost <= decision.maximum_cost, and minimum_eligibility >= decision.minimum_eligibility. The resource-adjusted policy score is worst_net_gain - decision.resource_penalty*worst_cost; report it as resource_adjusted_score. Among qualifying policies choose one maximizing this score. Any qualifying policy within acceptance.decision_slack of that maximum is accepted. A negative score does not permit abstention when a policy qualifies. Identifier order is only a convenient tie convention. If none qualifies, report no_qualifying_policy with null policy.

## Execution and output

Work in `solver_solution/` with `task/` available as a read-only sibling. Run offline with Python 3.11+, numpy, scipy and jsonschema available. Do not install packages or obtain external data. The exact command is

    python run_pipeline.py --data ../task/data --output-dir results

Accept arbitrary input and output directory paths. Validate input first:

    python ../task/data/validate_dataset.py --data ../task/data

The executable source is the run_pipeline.py submission. Write the final_answer.json and analysis.md submissions to the requested output directory. Recompute from staged scientific input on every execution; the evaluator also executes the submitted code on physically consistent regenerated population tables. Evaluator paths and stored answers are unavailable to the submitted runtime. Regular helper modules are permitted if they accompany the submitted source; symbolic links are unsupported. There is no required package-installation or additional dependency-declaration output.

`data/output_schema.json` defines the answer. Its metadata are schema=paired_immunity/1 and case_id=ALS_PAIRED_IMMUNITY_003. Include every supplied cohort and policy exactly once and each policy once per cohort. Match by IDs; all list orders are accepted. Every numeric endpoint and global envelope must match its scientific target within acceptance.numeric_absolute, except resource_adjusted_score, which uses acceptance.policy_score_absolute to allow propagation of upstream numerical errors. No decimal-place convention is graded. All scientific requirements and input-dependent execution are required for acceptance.

`analysis.md` must contain exactly one fenced json block with these fields: case_id; selected_policy (the selected ID or null); selected_policy_metrics (its global_policies object or null); decision_limits (the public decision object); interval_interpretation equal to sharp_bounds_over_compatible_causal_models; and context_diagnostics, listing each cohort's id, point_identified_policy_count, and largest_net_gain_width computed from its reported net-gain bounds. Narrative outside this block is optional. The executable grader validates these computed diagnostics; self-written success claims are not proof of scientific correctness.

Unreadable, absent, duplicate-key or nonfinite JSON receives zero. A readable answer object wrapped in a one-element array is recovered before numerical scoring. Numeric strings in numeric fields are recovered. Wrapper recovery, numeric strings, extra fields and missing/incorrect schema metadata incur only the single published presentation deduction; they do not cause a scientific failure by themselves. Missing scientific content fails its group. A missing report or inconsistent diagnostic block receives a delivery deduction. A missing or non-running pipeline cannot satisfy execution. The numeric rubric specifies all scores, caps and deductions; there are no hidden formatting or annotation rules.
