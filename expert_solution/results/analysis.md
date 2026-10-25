# Computed disposition and course diagnostics

```json
{
  "case_id": "ALS_TMDD_PULSE_002",
  "chip_diagnostics": [
    {
      "id": "chip_01",
      "fit_rmse": 1.061386466807673e-12,
      "local_rank": 10,
      "target_capacity_interval": [
        0.9456830872693298,
        1.4300683691699096
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_02",
      "fit_rmse": 9.44035956834048e-13,
      "local_rank": 10,
      "target_capacity_interval": [
        0.8936508616397215,
        1.0438487801044531
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_03",
      "fit_rmse": 9.093204353759814e-13,
      "local_rank": 10,
      "target_capacity_interval": [
        0.9963780668226313,
        1.2523155859671788
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_04",
      "fit_rmse": 8.802671867985405e-13,
      "local_rank": 10,
      "target_capacity_interval": [
        0.9184727661260207,
        1.178070532611281
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_05",
      "fit_rmse": 1.1775205471568263e-12,
      "local_rank": 10,
      "target_capacity_interval": [
        0.7343778261520598,
        1.4190189672915738
      ],
      "target_capacity_point_identified": false
    },
    {
      "id": "chip_06",
      "fit_rmse": 8.460505040136185e-13,
      "local_rank": 10,
      "target_capacity_interval": [
        0.7413013558377961,
        1.0555904903563182
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
      "time": 14.560684948378686,
      "value": 0.8858309708365496
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
