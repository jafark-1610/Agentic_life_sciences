# Population and protocol inputs

Each preparation's NPZ file is a standard numpy archive without pickled objects. `moment1` has shape [108], `moment2` [108,108], `moment3` [108,108,108], and `response` [18,18]. Outcome u=18*g+o joins the independently assigned initial module g to the observed endpoint class o. Axis order is the replicate-outcome order stated in the prompt. Probabilities are population laws stored as float64.

`study_metadata.json` lists dimensions, preparation IDs, archive filenames, local kinetic bounds, policies, numerical tolerances, and report tolerances. Physical state i=3*g+p. Rates have inverse-frame units. Policy actions are indexed by observation category.

`protocols.json` maps preparation IDs to initial probabilities, pre-screen loss, selection, the separate intervention observation sensor, target states, time durations, action multipliers, action loss rates, resource costs, penalties, and the shared unselected-population bulk turnover interval. Multipliers affect off-diagonal rates; reconstruct action diagonals. Loss is a distinct absorbing outcome. The turnover interval uses the stationary signed current specified in the prompt.

`output_schema.json` and `grading_contract.json` define the answer and scoring fields. `data_manifest.json` pins every other data file. `validate_dataset.py` checks normalization, symmetry, marginal consistency, ranks, generators' public bounds, protocols, and every file hash. No missing values or external annotations are used.
