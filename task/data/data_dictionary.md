# Data dictionary

* network.json: `metabolites` names the nine rows; `reactions` names 32 columns; `stoichiometry` is row-major. Fluxes are irreversible, carbon fluxes in mmol carbon-equivalent gDW^-1 h^-1; cofactor coefficients define reduced-model turnover per carbon-equivalent. Zero in stoichiometry means no contribution. There are no missing values.
* assay_panel.json: `channels` identifies 28 rows of H; `H` has one column per reaction. Coefficients convert model flux units to calibrated fingerprint units. `offset_groups` contains zero-based indices 0–3 in channel order. H contains signed coefficients and is not a probability matrix.
* cultures.json: eight independent environments. `bounds` is 32 [lower,upper] pairs in reaction order; `offset_bounds` is four pairs in group order. `observations` links by channel name and stores value and halfwidth. `standards` links by offset_group and stores known level, observed level and halfwidth; IDs are unique within culture. `response` contains `baseline_intercept`, `baseline_coefficients`, and `modules` keyed by ID; each module has an intercept and 32 coefficients. There is no intercept/offset equivalence between response and assay models.
* design_rules.json: costs and budget are arbitrary resource units. Incompatible pairs are unordered. `choose_per_group` is 1. `safety_floor` is dimensionless utility. Every legal combination is an available design, including combinations with poor safety.
* study_metadata.json: identity, units, tie tolerance and absolute numerical acceptance tolerances. An interval width cutoff defines `identifiable`; no normal-distribution interpretation is intended.
* data_manifest.json: byte lengths and SHA-256 hashes for the immutable analysis inputs. Output schema and validator are package code, covered separately by the package freeze manifest.
* source_provenance.json and SOURCE_RIGHTS.md: generation and redistribution basis.
* output_schema.json: JSON Schema 2020-12. Identifier uniqueness and menu completeness are additionally checked by the grader because JSON Schema alone cannot express them.
* validate_dataset.py: integrity, shape, finite values, cross-file relationships and per-culture joint feasibility.

No patient, donor, institution, or public study identifiers occur in these data.
