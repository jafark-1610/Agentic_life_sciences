# Rubric

Full submitted-code grading: `python expert_solution/verify_submission.py --solver PATH --data task/data --output-dir OUTPUT --replay-control`.

* course_decision: 40 points; all published fields in that group must pass.
* counterfactual_predictions: 25 points; all published fields in that group must pass.
* global_identifiability: 20 points; all published fields in that group must pass.
* continuous_peak_witness: 10 points; all published fields in that group must pass.
* measurement_fit: 5 points; all published fields in that group must pass.

Any failed scientific group caps at 79; execution/input-dependence failure caps at 79; caps precede presentation and delivery deductions. Pass threshold 80 inclusive. Group credit is all-or-nothing. Presentation deduction applies once and never activates a scientific cap. Delivery deductions total at most 10 including requirements.

Submitted pipeline must execute in staged offline isolation and pass both base and physically regenerated data. A failed or non-running pipeline or failed regenerated scientific result prevents acceptance and caps overall score at 79; missing/non-running pipeline is zero.

requirements.txt must exist and list numpy, scipy and jsonschema if imported by submitted code; missing/incorrect declaration deducts 2, within delivery cap 10.

Automatic zeros: absent/unreadable/duplicate-key/nonfinite JSON; missing or non-running pipeline in full submission verification.

Recovery: One-element answer-array wrapper and numeric strings are normalized before scientific evaluation. Extra fields and schema/case metadata slips incur presentation only. No arbitrary identifier renaming is accepted.

Delivery deductions: analysis diagnostic block 5; summary hashes/schema 5; requirements 2; combined cap 10.

## Public tolerances and data-derived dimensions

```json
{
  "tolerances": {
    "parameter_relative": 0.015,
    "parameter_absolute": 0.0005,
    "calibration_absolute": 0.0001,
    "fit_rmse_max": 2e-05,
    "efficacy_absolute": 0.002,
    "peak_absolute": 0.003,
    "witness_value_absolute": 0.003,
    "mass_balance_max": 2e-05,
    "cost_slack": 1e-06
  },
  "dimensions": {
    "chips": 6,
    "courses": 48,
    "model_counts": {
      "chip_01": 2,
      "chip_02": 2,
      "chip_03": 2,
      "chip_04": 2,
      "chip_05": 2,
      "chip_06": 2
    }
  },
  "field_contract": {
    "course_decision": "prompt.md: Counterfactual courses",
    "counterfactual_predictions": "prompt.md: Counterfactual courses",
    "global_identifiability": "prompt.md: Measurements and inference target",
    "continuous_peak_witness": "prompt.md: Counterfactual courses",
    "measurement_fit": "prompt.md: Measurements and inference target",
    "delivery": "prompt.md: Diagnostic evidence and Required deliverables"
  }
}
```

## Oracle execution comparison

The legacy numeric fallback is 1e-8; it does not replace any scientific acceptance rule. Oracle comparison uses the explicit paths and semantic witness checks below. Serialization precision applies only to oracle execution reproducibility, never to solver grading.

```json
{
  "command": "python expert_solution/compare_answers.py --actual expert_solution/results/final_answer.json --expected expert_solution/final_answer.json --data task/data",
  "path_syntax": "JSON Pointer with * matching one array index or object key",
  "path_tolerances": {
    "/chips/*/models/*/*": {
      "absolute": 0.0005,
      "relative": 0.015
    },
    "/chips/*/target_capacity_interval/*": {
      "absolute": 0.0005,
      "relative": 0.015
    },
    "/chips/*/calibration/*/*": {
      "absolute": 0.0001,
      "relative": 0.0
    },
    "/chips/*/fit_rmse": {
      "absolute": 2e-05,
      "relative": 0.0
    },
    "/courses/*/minimum_efficacy": {
      "absolute": 0.002,
      "relative": 0.0
    },
    "/courses/*/maximum_peak_free": {
      "absolute": 0.003,
      "relative": 0.0
    },
    "/courses/*/cases/*/efficacy": {
      "absolute": 0.002,
      "relative": 0.0
    },
    "/courses/*/cases/*/peak_free": {
      "absolute": 0.003,
      "relative": 0.0
    },
    "/selection/peak_witness/value": {
      "absolute": 0.003,
      "relative": 0.0
    }
  },
  "numeric_rule": "abs(actual-expected) <= absolute + relative*abs(expected)",
  "exact_fields": "Case/schema identity, scientific identifiers, Boolean flags, local rank, and resolved model indices.",
  "semantic_rules": {
    "ordering": "Match chips/courses/cases by identifiers and models by parameter-equivalence mapping.",
    "/selection/peak_witness/time": "Do not compare to a fixed coordinate. Recompute the physical value at the submitted time and check its agreement with the global peak.",
    "runtime_metadata": "Validate hashes and schema against the current execution; elapsed time and environment versions are not reference-equality fields."
  },
  "oracle_serialization": {
    "float_decimal_places": 8,
    "peak_time_decimal_places": 3,
    "peak_value": "Recomputed at the serialized time using the serialized parameter vector.",
    "scope": "Oracle reproducibility only; solver decimal precision is unrestricted."
  }
}
```
