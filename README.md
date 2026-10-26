# Persistent-cycle intervention pipeline

Infer persistent molecular subtype kinetics from reset population observations and bulk turnover calibration. Compute sharp intervention, retention, rate, and entropy ranges, then select an observation-dependent policy by its worst-case net gain.

`task/` contains the physical model, population moment arrays, protocols, data checks, and output contract. `expert_solution/` contains the inference implementation, numerical grader, expected comparison items, tests, robustness experiments, and execution records.

From `expert_solution/`:

    python run_pipeline.py --data ../task/data --output-dir results
    python score_rubric.py --answer results/final_answer.json --analysis results/analysis.md --data ../task/data --output-dir results/grading
    python validate_package.py
