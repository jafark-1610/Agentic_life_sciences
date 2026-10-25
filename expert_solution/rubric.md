# Rubric

Case: ALS_FLUX_RESCUE_001

| Scientific group | Points | Required behavior |
|---|---:|---|
| robust_selection | 55 | Safe minimax-regret design within published selection slack, or correct no-rescue status |
| utility_envelopes | 20 | Every culture and global floor and regret within numeric tolerance |
| flux_ranges | 15 | Every feasible flux endpoint and width-based identifiability flag correct |
| adversarial_witness | 10 | Feasible shared state and legal challenger attain selected global regret |

All comparisons use supplied public inputs and computed reference. No method requirement. All scientific groups are gates. Any failed scientific group caps at 79. Presentation-only schema errors deduct 5 once, never activate cap. Arrays are matched by IDs or sorted module tuples. Malformed/missing numerical entries fail their group. Each group is all-or-nothing. Code provenance and offline execution are separately reviewed, not inferred from text or automatically scored. No other caps or deductions.

Pass threshold: 80 inclusive. Automatic zero: answer missing, unreadable, duplicate-key or nonfinite JSON.

## Published tolerances
```json
{
  "numeric_abs": 0.002,
  "witness_feasibility_abs": 2e-05,
  "witness_objective_abs": 0.002,
  "selection_regret_slack": 0.002,
  "identifiable_width": 0.01
}
```

## Dataset dimensions
```json
{
  "cultures": 8,
  "reactions_per_culture": 32,
  "feasible_designs": 17
}
```

## Graded field contract
```json
{
  "robust_selection": "prompt.md: Decision and Deliverables selection",
  "utility_envelopes": "prompt.md: Deliverables designs",
  "flux_ranges": "prompt.md: Deliverables cultures",
  "adversarial_witness": "prompt.md: Adversarial witness"
}
```
