# RNA nuclear export and destruction after transcription attenuation

Required deliverables: run_pipeline.py, final_answer.json, analysis.md

## Research question

Which transcripts respond to depletion of a transport-associated factor through altered nuclear export, nuclear destruction, or cytoplasmic destruction? Does the stress-response transcript set differ from other transcripts? Infer these quantities from the compartment measurements, physical calibrators, residual transcription measurements, and growth observations in `data/`. All identifiers and observations are synthetic. No external annotations apply.

## Biology and evidence

Six independently grown parental populations were each split into vehicle and perturbed sibling cultures. Cultures equilibrated under their assigned condition before time zero. At time zero a separate transcription attenuator was applied. The factor perturbation and attenuation are distinct interventions. Each gene has one well-mixed nuclear RNA pool and one well-mixed cytoplasmic RNA pool per cell. RNA enters the nucleus by transcription, leaves it by export or nuclear destruction, and enters the cytoplasm only by nuclear export. Cytoplasmic RNA leaves by destruction. Export and destruction are first-order with constant rate coefficients within a culture and condition. Cell division dilutes both pools. Baseline pools at time zero were at steady state under the independently measured pre-attenuation growth rate. There is no cytoplasmic transcription, nuclear re-import, or condition-dependent probe chemistry.

The attenuator did not eliminate transcription. Its residual activity was held constant during each sampling interval. Independent run-on measurements give each interval's transcription rate divided by that culture's own pre-attenuation rate; the same fraction applies to all transcripts. Actual transcription amplitudes are not supplied. Cell numbers grow exponentially within each sampling interval. Neither post-attenuation growth nor residual transcription is assumed constant across intervals or shared across conditions.

Each time point was fractionated into two collected fractions. Neither fraction is pure. Two known-origin, distinguishable RNA standards were added before fractionation at known per-input-cell amounts. Each standard experiences the same recovery and exposure as endogenous RNA of its compartment. A two-by-two sample-specific nonnegative linear map sends nuclear/cytoplasmic abundances per cell to measured signals. Its rows are collected fractions, columns are physical origin compartments. The map includes recovery, cross-contamination and acquisition gain; its rows are not required to sum to one. Both origins contribute to both collected fractions. All endogenous probes have the calibrated common response scale.

Detected endogenous signals have independent normal log measurement errors with the supplied `log_sigma`, conditional on their true mean signals. An absent value means signal below that fraction's stated detection limit, not missing at random. Standard measurements are independent log-normal observations with log SD 0.0005; run-on observations are independent log-normal measurements with log SD 0.008. Each has two technical readings. Technical readings, time points, fractions and genes are not independent biological cultures.

`study_metadata.json` defines gene order, stress membership, physical time, arms, parental count, and material threshold. `hybridization.npz` stores only observed signals and calibration observations, with axes and units in the data dictionary. Array indices are fixed by metadata, never by sorting signal magnitudes. The input validator checks every array and file hash.

## Required analysis

Analyze all three settings separately: `base`, `early_window` (exclude the last two sampling times and refit the kinetic models), and `leave_parent_out` (exclude parental population index 5 and both sibling cultures, rerunning biological inference). All settings must contain every gene. For each gene and each parameter `export`, `nuclear_decay`, `cytoplasmic_decay`, report:

- `vehicle_rate` and `perturbed_rate`: geometric mean culture rates, inverse hours.
- `log2_ratio`: the mean paired parental log2 perturbed/vehicle rate contrast.
- `interval`: a 95% interval for that contrast.
- `equivalence_interval`: a 90% interval.
- `class`: `INCREASED`, `DECREASED`, `EQUIVALENT`, `UNRESOLVED`, or `NOT_ESTIMABLE`.

An increased or decreased assertion concerns a contrast beyond plus or minus `material_log2` (log2 of 1.5). Use one-sided tests in the estimated direction against that material boundary. Control FDR at 0.05 over the combined family of all estimable gene-by-parameter contrasts, with increases and decreases together. An equivalence assertion requires the 90% interval to lie strictly within the two material boundaries; absence of a significant effect is not evidence of equivalence. A directional discovery takes precedence over equivalence. Otherwise report UNRESOLVED. A defensible non-estimable result may use null numeric fields with class NOT_ESTIMABLE; explain its rule. At least 95% of reference-estimable contrasts must be estimated.

For each of the three kinetic parameters, report a `group_contrasts` row with `parameter`, `estimate` and a 95% `interval`: the mean gene-level log2 effect in stress-response genes minus that in other genes. Respect the parental replication and shared culture variation when assessing this group contrast. Both groups are fixed sets in the supplied panel.

No estimator, optimizer or software library is prescribed. Derive how the biological assumptions and each calibration relate to the observed signals. A good compartment-signal fit does not by itself establish valid mechanistic attribution or uncertainty.

## Answer

Write `results/final_answer.json` with schema `rna_transport/1`, case_id `ALS_RNA_TRANSPORT_006`, and `analyses`. The latter maps the three setting names to objects with `genes` and `group_contrasts`. Each gene row has `id` and `effects`, mapping each parameter name to the six fields above. Records are matched by ID, not position. The output schema is in `data/output_schema.json`.

Write `results/analysis.md`: methods with reasons, calibration use, treatment of censored signals, biological replication, group uncertainty, sensitivity changes, and limitations. Include one fenced JSON block with `analysis_counts`, a mapping from setting to class-count dictionary over all gene-by-parameter rows. Include all five labels even if a count is zero. The block is checked by recomputation. State that the data are synthetic and identify the packages used.

## Scientific assessment

Numerical comparisons use the frozen analysis of these same observations. Each analysis must meet all requirements below; any failed scientific criterion caps the score at 79. Passing requires 80. All comparisons are over reference-estimable gene-by-parameter rows, separately per analysis. Missing estimates count against coverage, rather than being treated as correct.

- At least 90% of estimated per-arm rates and log2 effects must differ from the reference by no more than the larger of 0.25 on the log2 scale and the applicable reference 95% half-width. The reference effect half-width is used for per-arm rates as a conservative allowance.
- At least 90% of estimated 95% intervals must cover the reference effect and have width between 0.4 and 2.5 times the reference width.
- Strong directional results are reference 95% intervals entirely beyond the material threshold plus an additional 0.2. At least 98% must receive the correct directional label. An opposite directional call is also forbidden when the reference 95% interval contradicts it; at most three forbidden calls are accepted.
- Strong equivalences are reference 90% intervals entirely within plus/minus 0.3 times the material threshold. At least 98% must be labelled EQUIVALENT. At most three EQUIVALENT calls are accepted where the reference 95% interval lies entirely outside either material boundary.
- Reported decisions must follow the stated rule; near-boundary disagreements supported by the intervals are accepted. Numeric effect and equivalence intervals must contain the estimate, with the latter nested within the 95% interval, to a numerical allowance of 0.0001.
- Each group estimate must lie within the larger of 0.12 and half the reference group interval width of its reference value. Each group interval must contain the reference estimate and have width 0.4 to 2.5 times the reference width.

The grading contract publishes weights; the expert rubric stores every expected result. Scientific scoring accepts numerically different methods meeting these broad requirements. Model failures must be scientific, not consequences of renamed optional metadata or a missing extra output slot. Correct scientific output with a missing/inconsistent calculated report loses only five report points. Extra metadata, numeric strings and a one-object list wrapper are recoverable and cost five presentation points once, without a scientific cap.

## Execution

Submit one self-contained `run_pipeline.py`; there are no helper-code slots. It accepts arbitrary `--data` and `--output-dir` paths, runs offline, derives results from those inputs, and writes the two results files. The three slots are run_pipeline.py, final_answer.json and analysis.md. Python 3.11+ supplies numpy, scipy and jsonschema, along with pandas, statsmodels and scikit-learn. No installation or network is available. Re-execution uses only task/ and submitted source, including a new simulated instance. Stored-answer substitution is rejected. Infrastructure failures are blocked checks and are not claimed as model failures.
