# Methods

Origin-resolved standards calibrate the full fractionation map because its cross-contamination and gains change among samples. Joint compartment mass balance retains residual synthesis and cell dilution. Censored log-normal likelihood is used to avoid interpreting undetected signal as zero. Log-rate contrasts use matched parental populations; group intervals preserve shared culture variation. Sensitivity settings refit the eligible evidence and recompute biological inference.

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

# Limitations

The observations are synthetic. First-order rates, equilibrated baseline pools, and well-mixed compartments are model assumptions. The calibration precision is high but finite. Six parents provide limited resolution for small nuclear destruction effects. Library fractions and technical standards do not increase biological sample size. NumPy and SciPy provide numerical linear algebra, normal tail probabilities and Student quantiles.
