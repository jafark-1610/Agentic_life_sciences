# Paired-clone policy analysis

```json
{
  "case_id": "ALS_PAIRED_IMMUNITY_003",
  "selected_policy": "policy_08",
  "selected_policy_metrics": {
    "id": "policy_08",
    "worst_net_gain": 0.17316,
    "worst_harm": 0.04794,
    "worst_cost": 1.182,
    "minimum_eligibility": 0.9654,
    "resource_adjusted_score": -0.08097
  },
  "decision_limits": {
    "maximum_harm": 0.22,
    "maximum_cost": 1.3,
    "minimum_eligibility": 0.8,
    "resource_penalty": 0.215
  },
  "interval_interpretation": "sharp_bounds_over_compatible_causal_models",
  "context_diagnostics": [
    {
      "id": "cohort_01",
      "point_identified_policy_count": 1,
      "largest_net_gain_width": 0.05352000000000001
    },
    {
      "id": "cohort_02",
      "point_identified_policy_count": 1,
      "largest_net_gain_width": 0.054790000000000005
    },
    {
      "id": "cohort_03",
      "point_identified_policy_count": 1,
      "largest_net_gain_width": 0.05341999999999997
    }
  ]
}
```

The compatible family preserves the same latent clone and instrument variables across potential worlds. Survival-conditioned target comparisons retain their joint conditioning event. The intervals are population-limit causal bounds under the stipulated model and measurement bands. They are not sampling confidence intervals or clinical findings.
