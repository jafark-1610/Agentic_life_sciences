# Capture-to-design workflow

Read `prompt.md`, validate `data/`, infer the three sequence-energy landscapes for each binder, predict folding and competitive occupancy, and select a variant using the published utility.

`data/variants.csv` fixes row order. Capture and calibration tables join to conditions and binders in `study_metadata.json`. The dictionary supplies units and keys. The schema and grading contract define the answer and numerical acceptance rules. The data manifest provides integrity checks.

The submitted entry point is one self-contained `run_pipeline.py`. The pipeline accepts `--data` and `--output-dir` and writes `final_answer.json` and `analysis.md` in the chosen output directory. The two deliverable manifests list the same three submission slots.
