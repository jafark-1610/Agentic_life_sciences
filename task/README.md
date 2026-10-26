# Reset measurements to intervention bounds

Read `prompt.md`, run `data/validate_dataset.py`, analyze the eight population moment archives with the supplied response matrices, and enforce the matching bulk turnover intervals. Use the screening and intervention protocols to calculate every requested range and select a policy.

`data/study_metadata.json` supplies dimensions and tolerances. `data/protocols.json` supplies state-indexed experiments and actions. The dictionary explains tensor axes and units. The schema and grading contract define outputs and scientific acceptance.

Submit one self-contained `run_pipeline.py`, plus `final_answer.json` and `analysis.md` produced in the chosen output directory. Both deliverable manifests list these three slots.
