# Task pipeline

Read `prompt.md`, validate the scientific data, construct the compatible same-clone causal family, calculate the requested conditional sharp bounds, and select the policy under the public resource and safety rules.

The exact solver submission slots are `run_pipeline.py`, `final_answer.json` and `analysis.md`. `required_deliverables.json` and `deliverables.json` are flat three-name lists for that same contract. Write the two result files in the directory passed to `--output-dir`. `requirements.txt` describes supplied dependencies and is not another submission slot.

`data/output_schema.json` defines the answer. `data/data_dictionary.md` defines fields and conventions. `data/data_manifest.json` fixes scientific input integrity. `data/validate_dataset.py` verifies table completeness and data relationships. Provenance and rights are in `data/source_provenance.json` and `data/SOURCE_RIGHTS.md`.
