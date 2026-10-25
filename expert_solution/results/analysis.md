# Computed disposition and course diagnostics

```json
{
  "case_id": "ALS_TMDD_PULSE_002",
  "chip_diagnostics": [
    {
      "id": "chip_01",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.94568309,
        1.43006837
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_02",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.89365086,
        1.04384878
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_03",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.99637807,
        1.25231559
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_04",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.91847277,
        1.17807053
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_05",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.73437783,
        1.41901897
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_06",
      "fit_rmse": 0.0,
      "local_rank": 10,
      "target_capacity_interval": [
        0.74130136,
        1.05559049
      ],
      "target_capacity_point_identified": false
    }
  ],
  "selection": {
    "status": "selected",
    "course": "course_020",
    "peak_witness": {
      "chip": "chip_06",
      "model_index": 0,
      "scenario": "slow_clearance",
      "time": 14.561,
      "value": 0.88583096
    }
  },
  "decision_limits": {
    "efficacy_floor": 0.4,
    "peak_ceiling": 0.93
  },
  "limitations": [
    "synthetic_reduced_system",
    "rounded_deterministic_signals",
    "counterfactuals_depend_on_model"
  ]
}
```

The parameter solutions describe chemical-site identities without imposing a rate ordering. Counterfactuals cover every returned solution and specified scenario. Continuous free-tissue peaks are optimized between input events. The model is synthetic and is not a clinical dosing recommendation.
