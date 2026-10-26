# Protein design analysis

Capture controls calibrate the background and ceiling independently for each assay. The four-state partition model is fitted jointly to all screen counts using quadratic genotype energies. Predictions retain competitive ligand binding and the measured genotype dependence of denaturation. The selected variant maximizes the published manufacturing and occupancy utility over the supplied candidate panel.

The following diagnostics are calculated from the serialized answer and staged counts.

```json
{
  "proteins": [
    {
      "id": "binder_0b8c50c7",
      "capture_deviance_per_observation": 1.003098,
      "capture_rmse": 3.89e-05,
      "mean_apo_folded": 0.3834689,
      "mean_worst_a": 0.103725
    },
    {
      "id": "binder_0cf797f3",
      "capture_deviance_per_observation": 0.971965,
      "capture_rmse": 2.06e-05,
      "mean_apo_folded": 0.0114604,
      "mean_worst_a": 0.0032291
    },
    {
      "id": "binder_82ef5504",
      "capture_deviance_per_observation": 0.9774272,
      "capture_rmse": 2.73e-05,
      "mean_apo_folded": 0.0813336,
      "mean_worst_a": 0.0167034
    },
    {
      "id": "binder_41646adf",
      "capture_deviance_per_observation": 0.9684643,
      "capture_rmse": 2.6e-05,
      "mean_apo_folded": 0.0557062,
      "mean_worst_a": 0.0112474
    },
    {
      "id": "binder_e059740b",
      "capture_deviance_per_observation": 0.9902679,
      "capture_rmse": 2.58e-05,
      "mean_apo_folded": 0.0219819,
      "mean_worst_a": 0.0172955
    },
    {
      "id": "binder_8352f9d7",
      "capture_deviance_per_observation": 0.9599514,
      "capture_rmse": 3.54e-05,
      "mean_apo_folded": 0.2110884,
      "mean_worst_a": 0.3561573
    }
  ]
}
```

The assays are synthetic equilibrium measurements. The genotype model restricts energies to second order; conclusions do not establish clinical efficacy, dynamics, or behavior outside the specified mutation panel and thermodynamic conditions. A low capture residual does not independently validate latent energies or extrapolated designs.
