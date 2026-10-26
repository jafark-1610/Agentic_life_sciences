# ALS_HIDDEN_CYCLE_005

Required deliverables: run_pipeline.py, final_answer.json, analysis.md

## Persistent enzyme subtypes and intervention design

For each of eight simulated enzyme preparations, recover the compatible microscopic kinetics from the supplied population observations, quantify the requested ranges, and choose an observation-dependent intervention. The experiments are synthetic and nonclinical. Use only `data/`.

## Microscopic family

There are six modules and three phases per module, giving 18 resolved physical states. State i = 3*g+p has module g and phase p, both zero-based. Each preparation is a mixture of three immutable molecular subtypes with unknown positive weights summing to one. A molecule keeps its subtype throughout every reset experiment, screen, observation, intervention, and follow-up. Conditional on that subtype, its physical state follows a continuous-time Markov chain.

For subtype h, module exchange has a six-by-six generator R_h. For g != d, R_h[g,d] is positive; its diagonal is minus the row's off-diagonal sum. From any phase of g, exchange to each of the three phases of d occurs at rate R_h[g,d]/3.

Within module g, clockwise transitions p -> (p+1) mod 3 occur at unknown rate f_h,g, and counterclockwise transitions p -> (p-1) mod 3 at unknown rate b_h,g. These rates do not depend on phase. The microscopic generator Q_h has no other transitions, and its diagonal makes every row sum zero. Row probability vectors evolve as rho*exp(Q_h*t).

All candidate microscopic models must satisfy the public `rate_bounds`: individual cycle-rate bounds, their sum bounds, positive exchange bounds, and the maximum total exchange exit rate per module. Time is measured in acquisition-frame units. The common frame interval is `frame_time`.

## Reset observations

Each `<preparation>_moments.npz` contains `response`, `moment1`, `moment2`, and `moment3`, loaded with `numpy.load(..., allow_pickle=False)`. `response` is a known row-stochastic 18-by-18 classification matrix C: row i gives the distribution of the observed class when the true endpoint state is i. It applies only to these reset experiments.

In one reset experiment, choose module G uniformly from 0 through 5, clamp the molecule to phase 0 of that module, release it for one frame, and classify its endpoint O through C. Record U = 18*G+O, an outcome from 0 through 107. The clamp and wash preserve subtype.

Perform three independent reset experiments on the same persistent molecular subtype. Conditional on subtype h, the three outcomes are independent and have one common distribution a_h. The released population arrays are

    moment1[u]       = P(U1=u)
    moment2[u,v]     = P(U1=u, U2=v)
    moment3[u,v,w]   = P(U1=u, U2=v, U3=w).

They are exact population probabilities up to float64 storage rounding, not empirical frequencies or independent draws of subtype between replicates. The source family has three linearly independent subtype outcome distributions. No generator, subtype distribution, or mixture weight is provided. No smaller time-interval observations are provided. Do not interpret binary storage rounding as an additional statistical confidence set. Accuracy is judged with the published tolerances.

To name identifiable subtypes consistently, order them by increasing probability that a reset experiment's observed class is in {0,1,2}, averaging over its randomized initial module. These three ordering scores are distinct. This convention applies to every subtype-indexed output.

## Bulk turnover calibration

`protocols.json` also gives one `bulk_turnover` closed interval for each preparation. This is a constraint on the same, unselected preparation measured at unperturbed steady state. It is not a separate rate fit for each subtype.

Let pi_h be the stationary row distribution of Q_h. The subtype's signed turnover reporter is the sum, over modules, of the stationary net current through the phase-0-to-phase-1 edge:

    J_h = sum_g [pi_h[3*g]*f_h,g - pi_h[3*g+1]*b_h,g].

The weighted preparation value sum_h weight_h*J_h must lie in that preparation's supplied interval. The admissible set consists of all subtype weights and microscopic generators that reproduce all reset population observations and satisfy this calibration and all rate bounds. This is the common admissible set for every requested result.

## Screening and intervention

The remaining protocol arrays specify the following experiment, separately for each preparation.

1. Draw a molecule with the preparation's original subtype weights and the given `initial_distribution` over physical states. Evolve its unperturbed Q_h for `screen_time`, with competing irreversible loss at `pre_loss_rate[i]` in state i. A lost molecule does not enter the screen.
2. At the screen, a surviving molecule passes with the given `selection_probability[i]`. The screen does not change its state. Among passing molecules, draw one observation Y in {0,1,2} using row i of `observation`. This sensor has the specified state-dependent error and is distinct from the reset classifier C.
3. A supplied policy assigns one action to each Y. Apply that action for `followup_time`. For off-diagonal entries, its kinetic generator is Q_action[i,j] = Q_h[i,j]*multiplier[i,j]; rebuild its diagonal from the modified off-diagonal row sum. Its irreversible competing loss rates are `loss_rate`. The molecule's subtype does not change.
4. Success is the first entry into any `target_states` during follow-up, before irreversible loss and by the deadline. A molecule already in a target state at follow-up time zero succeeds immediately. Success and loss are absorbing competing events. A molecule that reaches neither by the deadline is censored. Resource cost is the action's `resource_cost`, charged to every passing molecule assigned that action, including an immediate success.

All probabilities and expected costs below are conditional on passing this screen. Recompute the retained subtype distribution under each admissible model. The benchmark uses action 0 for all observations on the same selected population. Policy actions are listed in observation order in `study_metadata.json -> policies`; every listed policy is eligible.

For an admissible model and policy p, define

    S_p = probability of success
    L_p = probability of follow-up loss
    C_p = mean resource cost
    G_p = (S_p - S_benchmark) - loss_penalty*(L_p - L_benchmark)
    N_p = G_p - resource_penalty*C_p.

The benchmark and intervention in these differences use the same microscopic model, initial population, and screen. For each model, a subtype's one generator is fixed throughout the entire protocol, including every observation branch. Different extrema may be attained by different admissible models.

For every policy, report the sharp lower and upper bounds of S_p, L_p, C_p, G_p, and N_p over that common admissible set. A conservative outer interval is not a sharp bound. Choose a policy maximizing the sharp lower bound of N_p, accepting the published `choice_regret` slack. There is no additional resource-budget feasibility threshold.

## Retention, rate, and entropy ranges

Report the sharp unconditional probability of passing the screen, over the same admissible set. For every subtype and module, report the sharp ranges of its forward and backward rates among models that can be extended to a complete admissible preparation.

Also report `candidate_counts`: the number of distinct unperturbed microscopic generators per subtype compatible with the reset data and local rate bounds BEFORE applying the bulk turnover constraint. This counts generators, not observed transition matrices or label permutations. Subtype ordering above fixes labels.

For a subtype with unperturbed stationary distribution pi_h, its entropy-production rate is

    sigma_h = sum_{i<j} (pi_h[i]*Q_h[i,j] - pi_h[j]*Q_h[j,i])
                       * log((pi_h[i]*Q_h[i,j])/(pi_h[j]*Q_h[j,i])).

Rates are positive on every edge in the stated family. The requested `retained_epr_bounds` describe the sharp range of the average unperturbed stationary sigma_h under the subtype weights AFTER the screen. This corresponds to retaining the selected subtypes, then letting their unperturbed processes reach steady state. It is not the entropy production of an averaged generator or of the drug-modified dynamics.

## Answer structure and attaining witnesses

Write finite JSON with `schema` = `persistent_cycle/1`, `case_id` = `ALS_HIDDEN_CYCLE_005`, and `preparations`. Include each preparation once. Object order is immaterial. In each preparation report:

- `id`.
- `mixture_weights`: three numbers in the subtype order defined above.
- `exchange_generators`: three six-by-six R_h matrices, including their negative diagonals.
- `forward_bounds`, `backward_bounds`: arrays of shape [3,6,2], subtype, module, lower/upper endpoint.
- `candidate_counts`: three positive integers with the local meaning above.
- `retention_bounds`, `retained_epr_bounds`: lower/upper pairs.
- `policies`: one object per policy, with `id` and five endpoint pairs: `success_bounds`, `loss_bounds`, `cost_bounds`, `gain_bounds`, `net_bounds`.
- `selected_policy`: an eligible policy identifier within `choice_regret` of the best sharp lower net value.
- `net_witnesses`: `lower` and `upper`, each an array of shape [3,6,2]. For the selected policy, each entry is a subtype/module's forward and backward rates in that endpoint's attaining model. These are physical rates, not a stochastic matrix or integer branch labels.

Witnesses must match compatible local generators within `witness_rates`. The grader snaps each subtype to its uniquely nearest compatible generator, then checks that the joint model satisfies the bulk interval within `witness_turnover` and attains the selected net endpoint within `witness_endpoint`. This permits numerical approximations while requiring attainable sharp endpoints. Any attaining model is accepted.

All scalar and endpoint tolerances are in `study_metadata.json -> tolerances`. The weights, R_h, rate intervals, retention, entropy, all policy intervals, choice, and both attaining witnesses are scientific requirements in every preparation. Every failed scientific requirement caps the score at 79; passing requires at least 80. The public grading contract maps fields to criteria. Any correct method is accepted. Do not submit a single fitted generator's output as a population uncertainty range unless the data actually identify it uniquely.

## Calculated report

Write `results/analysis.md` describing subtype inference, compatible kinetics, bulk calibration, first passage, conditional optimization, and limitations. Include exactly one fenced `json` block with `{"preparations": [...]}`. For each preparation include its `id` and these calculations from your serialized answer:

- `moment2_max_abs_error`, `moment3_max_abs_error`: rebuild the reset outcome distributions from the LOWER net witness rates, reported exchange generators and weights; report the maximum absolute differences of the reconstructed population arrays from the supplied arrays.
- `lower_net_witness_value`, `upper_net_witness_value`: evaluate the selected policy's conditional N_p under the corresponding reported physical witness, reported weights and R_h, and public protocol. Use those physical rates without snapping for these diagnostics.
- `lower_selection_probability`, `upper_selection_probability`: unconditional screen-pass probabilities under those same two physical witnesses.

Report tolerances are in `report_tolerances`. The five report points require the complete, consistent computed block; otherwise those points are withheld. Report evidence never activates the scientific cap. No unobserved correctness claim is required.

## Execution and delivery

Work in your own directory, with `task/` as a read-only sibling. First run

    python ../task/data/validate_dataset.py

Your submitted code is one self-contained `run_pipeline.py`. Run

    python run_pipeline.py --data ../task/data --output-dir results

Accept arbitrary input and output paths. Write `results/final_answer.json` and `results/analysis.md`. Submit exactly the three configured slots: `run_pipeline.py`, `final_answer.json`, `analysis.md`. No helper-code slots or additional solver deliverables are required. Python 3.11 or newer supplies numpy, pandas, scipy, scikit-learn, statsmodels, and jsonschema. No network or installation is available. Compute from the supplied inputs at runtime. The source is rerun in isolation on the published inputs and a freshly generated experiment from the same family; private expert files are unavailable. Stored-answer substitution and demonstrated external evidence receive zero. Infrastructure failures are recorded as blocked checks, not model failures.

Missing or unreadable JSON and a missing or non-running pipeline receive zero. Unreadable numeric blocks fail their preparation's scientific requirements. Recoverable presentation deviations cost five points once and never activate the scientific cap: a one-object list wrapper, numeric strings, missing or incorrect schema/case_id, extra metadata, duplicate keys (last value used), repeated preparation or policy identifiers (first occurrence used), and a consistent subtype permutation uniquely recoverable by matching the reported exchange generators. All subtype-indexed fields and witnesses are reordered together when recovering that permutation. Fixed field names and published array shapes are authoritative. Decimal precision is unrestricted. A missing report costs only its report points.
