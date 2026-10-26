# Thermodynamic protein design

Infer folding and competitive binding energy landscapes from calibrated capture experiments, predict the supplied mutation panel, and select variants by manufacturing and occupancy utility.

`task/` contains the model, counts, controls, variant panel, data validator, and answer contract. `expert_solution/` contains the joint inference implementation, executable grader, reproducibility metadata, independent numerical checks, and scientific robustness experiments.

Run the expert pipeline from `expert_solution/`:

    python run_pipeline.py --data ../task/data --output-dir results

Validate the package and score the output:

    python validate_package.py
    python score_rubric.py --answer results/final_answer.json --analysis results/analysis.md --data ../task/data --output-dir results/grading
