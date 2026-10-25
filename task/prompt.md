# ALS_TMDD_PULSE_002: Chemical-site identifiability and pulse-course design

Six synthetic organ-chip systems were studied using three dosing protocols and two optical readouts. Infer the full set of observationally compatible mechanistic models, then choose a course meeting an efficacy floor and a continuous-time safety limit in every chip, compatible model and specified physiological scenario. These are simulated mechanistic experiments, not patient measurements or clinical recommendations.

## State model

For each chip, use seven states initially zero: depot amount D, circulating amount C, free tissue amount F, amounts B1 and B2 bound to chemical sites 1 and 2, cumulative target occupancy A, and eliminated amount L. Compartments have equal normalized reference volume; amounts and concentrations share the declared numerical units. Time is hours. Positive parameters, in `model_spec.json` order, are ka, kel, vmax, km, kon1, koff1, q1, kon2, koff2, q2. Site capacities are q1 and q2. Three known rate constants are supplied per chip. Equations between input events are

    transport = vmax*C/(km+C)
    net1 = kon1*f1(t)*F*(q1-B1) - koff1*B1
    net2 = kon2*f2(t)*F*(q2-B2) - koff2*B2
    D'  = -ka*D
    C'  = ka*D - kel*C - transport + kreturn*F
    F'  = transport - kreturn*F - net1 - net2
    B1' = net1 - kint1*B1
    B2' = net2 - kint2*B2
    A'  = B2/q2
    L'  = kel*C + kint1*B1 + kint2*B2.

At each pulse time, add its dose to D and change no other state. Blockade windows are half-open [start,end). For each site i, fi(t) is 1/(1 + sum of strengths of active windows that affect site i). A `both` window affects both sites; a `site1` window affects chemical site 1 only. At a window boundary states remain continuous. Blockade changes association rates, not dissociation, internalization or capacity. Every experiment and candidate course starts from zero, not from the final state of another experiment. The conservation identity is D+C+F+B1+B2+L = cumulative administered amount.

## Measurements and inference target

`chips.json` provides standards and observations. The true concentration represented by channel `plasma` is C; by `tissue_total`, F+B1+B2. Each chip and channel has its own unknown gain g, sensor kd h and offset o:

    signal = o + g*x/(h+x).

`standards` supplies x and signal for calibration. The signal generator rounds to 12 decimal places; there is no additional stochastic noise. Treat calibration and mechanistic estimation as deterministic inverse problems with the parameter bounds in `model_spec.json`. Do not mistake sensor kd for the mechanistic transport km. Protocols are in `protocols.json`. All observations, including the wash protocol, participate.

The inference target is the complete set of globally optimal parameter vectors for the joint calibration and concentration-observation fit, not merely a full-rank local optimum. Rounding and numerical integration errors are covered by the published acceptance tolerances. A fitted vector's local differential rank does not define global identification. Chemical-site labels carry physical meaning for the candidate interventions and target efficacy. Do not impose an unreported rate-ordering constraint on chemical names. Return every distinct compatible mechanistic solution within the declared parameter domain; do not repeat numerically equivalent solutions. The supplied deterministic experiments identify isolated solutions rather than a continuous parameter family. Distinct solutions differ beyond the published parameter comparison tolerances. The fitted sensor parameters are shared across protocols of their chip.

For each chip report `calibration`, `models` (one ten-number vector per distinct solution in model-spec order), `target_capacity_interval` (minimum and maximum q2 across that set), and `target_capacity_point_identified` (true iff its interval width is at most `parameter_absolute`). Report `local_rank` of the concentration-observation Jacobian at any one returned solution: rows are protocol/time/channel observations, columns are derivatives with respect to log parameters, rank uses singular values greater than largest singular value times `local_rank_relative_cutoff`. Sensor parameters are held at their fitted values for this rank. Report `fit_rmse`, the root mean square concentration residual over all protocol/time/channel rows for that same solution. Invert the fitted sensor response to obtain observed concentrations. Any compatible solution gives the same residual/rank within tolerances. Parameter bounds, units and all numerical thresholds are public in `model_spec.json`.

## Counterfactual courses

`courses.json` is the entire candidate menu. Each record gives its pulses, blockade, horizon and resource cost. `scenarios.json` supplies physiological multipliers. Multiply each named mechanistic parameter before simulating the course. The same multiplier applies to that chemical parameter in each compatible model; it does not relabel sites or refit observations. Known constants are unchanged. In particular, a scenario may act differently on the two chemical sites. All scenarios apply to all chips.

For every chip, compatible model and scenario, compute

    efficacy = A(horizon)/horizon
    peak_free = max_{0 <= t <= horizon} F(t).

Efficacy is target-site-2 occupancy averaged continuously over time. Safety is a continuous-time extremum, including event endpoints, not the largest sampled assay value. For each course give all case rows and their minimum efficacy and maximum peak_free. Acceptable courses satisfy both `decision.efficacy_floor` and `decision.peak_ceiling` simultaneously in every case. Select a qualifying course of minimum supplied cost. Any qualifying course within `cost_slack` of the smallest qualifying cost is accepted; course-ID lexical order is only a convenient tie convention. If no course qualifies, report `no_qualifying_course` with null course and witness.

For a selected course supply a `peak_witness`: chip ID, zero-based index into that chip's returned models, scenario ID, time, and free-tissue value. At that time the physical model must attain the course's maximum peak_free within `witness_value_absolute`. Any near-maximizing time is valid; tied peaks need not use a fixed time. There is no requirement to reproduce an evaluator's particular peak-time coordinate.

## Required deliverables

The machine-readable contract is `../task/deliverables.json`. Work in `solver_solution/`, with read-only `task/` as a sibling. Supply these five files:

1. `solver_solution/run_pipeline.py`
2. `solver_solution/requirements.txt`
3. `solver_solution/results/final_answer.json`
4. `solver_solution/results/analysis.md`
5. `solver_solution/results/run_summary.json`

Run the validator and the pipeline offline with Python 3.11+ and numpy, scipy and jsonschema available:

    python ../task/data/validate_dataset.py --data ../task/data
    python run_pipeline.py --data ../task/data --output-dir results

Accept arbitrary input and output paths. Treat task files as immutable. Do not download data, install packages, read evaluator/private paths, copy stored answers, or embed outputs in code. The evaluator reruns the submitted pipeline against a regenerated, physically consistent instrument dataset; results must depend on the actual staged observations. Module helpers in your submission directory are permitted. Submit regular files and directories; symbolic links are not supported by the isolated staging contract. Both initial and regenerated executions use the same model and command contract.

`final_answer.json` follows `data/output_schema.json`. All IDs and model indices must resolve; include each chip, course and chip/model/scenario case exactly once. Order is irrelevant except parameter-vector order and the meaning of model_index. Use finite JSON numbers, never NaN or infinity.

`run_summary.json` follows `data/run_summary_schema.json`. Record case_id, status `success`, input_sha256, answer_sha256 and nonnegative elapsed_seconds. Compute input_sha256 as SHA-256 of UTF-8 `json.dumps({filename: sha256(raw_file_bytes) for filename in data_manifest['files']}, sort_keys=True, separators=(',', ':'))`. Hash only the files named in the manifest, by basename. answer_sha256 hashes the exact written final_answer.json bytes. A self-written success status is not proof of execution; rerun evidence is generated independently.

## Diagnostic evidence

`analysis.md` must contain exactly one fenced `json` block whose object contains `case_id`, `chip_diagnostics`, `selection`, `decision_limits`, and `limitations`. `chip_diagnostics` lists each chip's id, fit_rmse, local_rank, target_capacity_interval and target_capacity_point_identified from the computed answer. `selection` repeats the computed selection object, including witness. `decision_limits` repeats the two public decision limits. `limitations` must list these applicable model qualifications: `synthetic_reduced_system`, `rounded_deterministic_signals`, `counterfactuals_depend_on_model`. Other narrative is optional and not numerically scored. This structured evidence, the summary hashes, and the actual runtime are checked by the executable verifier; they are not deferred to an unspecified prose review.

## Acceptance and presentation

All reported compatible parameter solutions are checked modulo their output ordering against the full model-equivalence set, using `parameter_absolute + parameter_relative*abs(expected)` per coordinate. Sensor coefficients use calibration_absolute. Every returned model must fit the observations with RMSE no greater than fit_rmse_max; the reported fit_rmse for the representative solution must agree with recomputation within fit_rmse_max. Interval endpoints use parameter tolerances, flags are Boolean, and local_rank must agree with the stated rank definition. Every efficacy and continuous peak uses its respective absolute tolerance. Witness time must be in the course horizon and its recomputed value must match the reported value and global maximum within witness_value_absolute. Conservation error in independent forward checks must not exceed mass_balance_max.

Every scientific group and the input-dependent rerun are required for acceptance. A single readable answer object inside a one-element array is unwrapped for all scientific calculations; numeric strings in numeric fields are recovered. These, extra fields, and incorrect/missing schema metadata incur one presentation deduction, never a scientific failure by themselves. Structural omissions of scientific fields fail their group. Unreadable, absent, duplicate-key or nonfinite JSON receives zero. Missing report/summary/dependency artifacts receive the published delivery deductions; a missing or non-running pipeline cannot satisfy execution. The grader documents numeric scoring separately; no unlisted formatting rule affects science.
