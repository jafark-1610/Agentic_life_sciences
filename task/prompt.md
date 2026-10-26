# ALS_THERMODYNAMIC_DESIGN_004

Required deliverables: run_pipeline.py, final_answer.json, analysis.md

## Protein engineering from selection assays

Recover the thermodynamic landscapes of six synthetic protein binders and select a variant for each binder that retains useful binding in competition. The supplied mutation library contains 20 binary mutation positions and 16,384 variants. Only variants labelled `screen` have capture measurements. Predict every supplied variant, including those with no capture measurements. Every supplied variant is eligible for selection.

The files under `data/` are the complete experimental inputs. These are simulated equilibrium experiments, not clinical observations. The six binders have different unknown landscapes. The capture apparatus calibration is shared across binders at each screen condition. Do not transfer a binder's sequence coefficients to another binder.

## Physical model

A variant is the binary vector x in the `mutations` column of `variants.csv`. Character i is position i in `study_metadata.json -> positions`; the first character is the first position. The mutation labels have no external sequence or structural annotation.

At the baseline denaturant concentration of 1.0 M, its folding free energy F(x), ligand-A binding free energy A(x), and ligand-B binding free energy B(x) each belong to the full quadratic family

    E(x) = beta_0 + sum_i beta_i*x_i + sum_{i<j} beta_ij*x_i*x_j.

All coefficients are unknown, real, and binder-specific. No sparsity, sign restriction, common contact graph, or higher order terms are assumed. Energies are dimensionless in units of kBT. This is a constraint on energies, not on occupancies or capture probabilities.

The denaturation slope is known from an independent characterization:

    m(x) = m0 + sum_i mutation_m_shift[i]*x_i
    F_u(x) = F(x) + m(x)*urea.

Use the binder's values in `study_metadata.json`. The condition field `urea` is the signed molar offset from `urea_baseline_molar`, not an absolute concentration: actual concentration is 1.0 M plus that field. Thus a challenge offset of -0.7 means 0.3 M absolute denaturant. Ligand activities a and b are dimensionless and share a fixed standard state. Binding energies do not change with denaturant. Both ligands bind only the folded state, competitively at the same site. There are four states with weights

    unfolded:                  1
    folded, unoccupied:        exp(-F_u)
    folded, bound to A:        a*exp(-F_u-A)
    folded, bound to B:        b*exp(-F_u-B).

Their sum is the partition function Z. Occupancy of A is its state weight divided by Z, and likewise for B. The apo folded fraction requested below is the probability of the folded state at offset urea=0 (the 1.0 M baseline) with neither ligand present. There are no kinetic, aggregation, multimerization, or direct unfolded-state binding effects.

## Measurements

`capture_counts.csv` has one row per binder, screen variant, and screen condition. The `trials` molecules in that row are independent Bernoulli trials; `captured` is their observed success count. The relevant true binding occupancy p is A or B according to the condition's `reporter`. Under that condition the success probability is

    q = background*(1-p) + ceiling*p.

`background` and `ceiling` are unknown and condition-specific, with 0 < background < ceiling < 1. They are shared across all variants and binders in that condition. `calibration_counts.csv` contains independent binomial measurements on controls with known exact `bound_fraction`, following the same q model. Control trials are independent of the protein measurements. Counts are draws, not rounded probabilities. All incubation activities, reporters, denaturant values, and challenge conditions are in the metadata. There are no other assay covariates or external calibrations.

## Design objective

For a variant, let p_A,j be its true A occupancy in challenge condition j. Its manufacturing and binding utility is

    U(x) = apo_folded(x) * min_j p_A,j(x) - mutation_cost * sum_i x_i.

The published `design.mutation_cost` applies to every binder. Select one supplied variant per binder. Design regret is the maximum true utility among the supplied variants minus the true utility of your selection. Any selection within the published regret tolerance is accepted; no particular tie-break is required.

## Answer contract

Write finite JSON to `results/final_answer.json`. Use `schema` = `thermodynamic_design/1`, `case_id` = `ALS_THERMODYNAMIC_DESIGN_004`, and the arrays `calibration` and `proteins`.

For each screen condition, `calibration` has one object with `id`, `background`, and `ceiling`. For each binder, `proteins` has one object with:

- `id`: its published binder identifier.
- `energy`: a 16,384 by 3 array in the exact row order of `variants.csv`; columns are F, A, B at the baseline denaturant concentration in that order. These are the latent physical energies, not apparent dissociation energies or capture logits.
- `apo_folded`: a 16,384-element array in that same variant order, containing the apo folded fractions.
- `challenge_a`: a 16,384 by 4 array in that same variant order; columns follow the published challenge-condition order and contain A occupancies in the simultaneous presence of both ligands.
- `selected_variant`: one supplied variant identifier.

Binder and calibration object order is immaterial. Probabilities must be between 0 and 1. The output schema is `data/output_schema.json`. Coefficients are not required and no particular estimation method is required. Decimal precision is unrestricted.

## Scientific acceptance

Each binder must satisfy all six error requirements in `study_metadata.json -> acceptance_thresholds`, measured against the generating physical system:

- `energy_rmse_max`: root mean squared error over all entries of `energy`.
- `energy_p95_max`: 95th percentile of absolute error over all entries of `energy`, using linear interpolation between order statistics.
- `apo_rmse_max`: root mean squared error of `apo_folded` over all variants.
- `challenge_rmse_max`: root mean squared error over all entries of `challenge_a`.
- `challenge_max_abs_max`: maximum absolute error over all entries of `challenge_a`.
- `design_regret_max`: the design regret defined above.

The simulation coefficients are withheld. They are used for evaluation and never available during solver execution. The energy family, observation model, candidate panel, conditions, objective, error definitions, and tolerances given here fully specify the inference problem. A capture residual is a diagnostic and is not a replacement for latent-energy or design accuracy.

Every binder must have finite energies, valid probability arrays, and a supplied selection. An invalid or unreadable binder block earns no scientific credit for that binder. Each calibration must satisfy 0 <= background < ceiling <= 1. Any failed scientific requirement caps the score at 79; passing requires at least 80. `data/grading_contract.json` publishes weights and the field-to-requirement mapping. A correct alternative estimator receives the same credit.

## Computed analysis evidence

Write `results/analysis.md` describing the calibration, inference, variant extrapolation, selection, and limitations. Include exactly one fenced block labelled `json` containing `{"proteins": [...]}`. Each binder object in that block has `id` and four numbers computed from the answer you actually serialized:

- `capture_deviance_per_observation`: mean binomial deviance over all its capture rows, using its reported screen-variant energies, known m(x), reported calibration, and the physical model above. Deviance for n trials, k successes, and predicted q is 2*[k*log((k/n)/q) + (n-k)*log((1-k/n)/(1-q))], with a zero-count term defined as zero. Clip q to [1e-15, 1-1e-15] only for this diagnostic.
- `capture_rmse`: root mean squared error between those predicted q values and observed k/n.
- `mean_apo_folded`: arithmetic mean of its reported `apo_folded` array.
- `mean_worst_a`: mean, over variants, of the minimum entry in each row of its reported `challenge_a` array.

Diagnostic tolerances are in `report_tolerances`. The five report points are awarded for a complete, numerically consistent calculated evidence block; otherwise they are withheld. Report evidence cannot activate the scientific cap. No claim about an unobserved truth metric is required. The report must describe computations actually performed.

## Execution

Work in your own directory with `task/` as a read-only sibling. Validate inputs using:

    python ../task/data/validate_dataset.py

Create one self-contained `run_pipeline.py` and run:

    python run_pipeline.py --data ../task/data --output-dir results

Accept arbitrary paths for both arguments. The entry point must contain all submitted computational code: there are no helper-code output slots. The three submission slots are `run_pipeline.py`, `final_answer.json`, and `analysis.md`; the last two are collected from `results/`. No extra solver deliverables are required. The environment supplies Python 3.11 or newer and numpy, pandas, scipy, scikit-learn, statsmodels, and jsonschema. No network access or package installation is available during execution. Derive results from the input files each time. Submitted code is rerun in isolation, with only task inputs visible, including a freshly simulated instance from the same model family. An input-dependent solution is required; cached answers do not meet the task.

Recoverable presentation deviations cost five points once, and do not activate the scientific cap: a one-object list wrapper, numeric strings, transposed or row-major flattened matrices, missing or incorrect schema/case_id, duplicate keys (last value used), repeated binder/condition ids (first occurrence used), or extra metadata. Standard field names and array shapes are authoritative; unrelated aliases are not guessed. Unreadable numeric blocks fail only their binder's scientific requirements. Missing/unparseable JSON or a missing/non-running pipeline receives zero. Invalid numeric values are scientific failures, never an exception in grading. External evidence and stored-answer substitution require documented isolated-execution evidence. Infrastructure failures are recorded as blocked, not counted as model failures.
