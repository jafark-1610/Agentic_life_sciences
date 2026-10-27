# Methods

Joint compartment mass balance is fitted because nuclear disappearance includes both export and destruction. A censored log-normal likelihood and multiple initializations stabilize the kinetic estimates.

# Calibration

Origin-resolved RNA standards identify each sample fractionation and gain matrix. Both physical compartments contribute to each collected fraction, without forcing row normalization.

# Censoring

Signals below the detection limit contribute normal lower-tail probabilities in log space. They are not zero intensities or observations missing at random.

# Replication

Parental populations supply the biological replication. Paired sibling cultures define the treatment contrasts; technical standards, genes and time points do not increase the parent count.

# Group uncertainty

Stress and other transcript means are first contrasted within each parent. Variation among those parental contrasts determines the group interval, preserving shared culture variation.

# Sensitivity

The early window refits the retained sampling times. Parent exclusion uses only indices zero through four, with recomputed paired contrasts and multiplicity adjustment; inference_trace records the actual rate inputs.

# Limitations

The observations are synthetic. First-order destruction, equilibrated baseline pools and well-mixed compartments are assumptions. Six biological parents provide limited precision for small nuclear destruction effects.

# Software

numpy 2.3.5, scipy 1.17.0 were used for numerical linear algebra and distribution calculations.

```json
{
  "analysis_counts": {
    "base": {
      "INCREASED": 120,
      "DECREASED": 178,
      "EQUIVALENT": 1204,
      "UNRESOLVED": 298,
      "NOT_ESTIMABLE": 0
    },
    "early_window": {
      "INCREASED": 69,
      "DECREASED": 130,
      "EQUIVALENT": 1071,
      "UNRESOLVED": 530,
      "NOT_ESTIMABLE": 0
    },
    "leave_parent_out": {
      "INCREASED": 97,
      "DECREASED": 165,
      "EQUIVALENT": 1155,
      "UNRESOLVED": 383,
      "NOT_ESTIMABLE": 0
    }
  }
}
```
