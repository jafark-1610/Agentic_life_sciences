# Input tables

`variants.csv`: variant_id (unique key), mutations (20 binary characters in position order), role (`screen` has measurements; `candidate` has none). Both roles are design candidates. CSV row order defines all answer-array rows. Bit string is authoritative; identifiers encode the same binary vector with the first character as bit 0.

`capture_counts.csv`: protein_id, variant_id, condition_id (foreign keys), trials (positive integer), captured (integer from zero through trials). Complete Cartesian product of binders, screen variants, and screen conditions. Count-row order is arbitrary.

`calibration_counts.csv`: condition_id, control_id (joint key), bound_fraction (known occupancy, zero to one), trials, captured. The linear capture calibration is shared by all binders in that condition. Fractions are independent physical controls, not protein variants.

`study_metadata.json`: binder identifiers and known denaturation slopes; screen/challenge conditions, energy ordering, utility, acceptance thresholds and report tolerances. Ligand activities are dimensionless; energies use kBT. The condition field `urea` is a molar offset from `urea_baseline_molar` = 1.0 M. Actual concentration is baseline plus offset, so all supplied absolute concentrations are positive. The energy origin and requested apo fraction use zero offset, at the baseline concentration. Missing values are not used.

`output_schema.json` defines answer structure. `grading_contract.json` maps every compared science field to the task and publishes weights. `source_provenance.json` and `SOURCE_RIGHTS.md` describe the simulation. `data_manifest.json` pins every other data file; `validate_dataset.py` checks hashes, table completeness and types.
