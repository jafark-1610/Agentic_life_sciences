# RNA inference pipeline

analysis_engine.py jointly fits compartment trajectories and pools parental contrasts. run_pipeline.py consumes config/parameters.yaml and writes results/final_answer.json, results/analysis.md and the expert execution metadata results/run_summary.json. The latter is outside solver slots. score_rubric.py grades all three settings using the public statistical allowances. Validation, tests and scientific controls are in tests/ and robustness_checks/. The source generator and simulation truth are evaluator-only.

    python run_pipeline.py --data ../task/data --output-dir results
    python -m unittest discover -s tests

`calibrate.py` regenerates five reserved experiments and measures population-effect interval coverage. `method_notes.md` explains the mechanistic and statistical assumptions and distinguishes these checks from external model qualification.
