# Metabolic rescue design analysis

The feasible state includes 32 fluxes and four shared calibration offsets per culture. Linear programs retain mass balance, capacities, standards and all assay intervals jointly. Each flux range is optimized directly. Utility differences use the same feasible state for both designs. Global regret maximizes over culture, challenger and feasible state. Safety is a separate worst-case utility constraint.

## Decision
{
  "selection": [
    "export_1",
    "redox_2",
    "uptake_1"
  ],
  "metrics": {
    "modules": [
      "export_1",
      "redox_2",
      "uptake_1"
    ],
    "floor": 10.597267369187339,
    "regret": 31.388735674682387,
    "by_culture": [
      {
        "culture": "culture_01",
        "floor": 32.049108845138974,
        "regret": 29.20629411607236
      },
      {
        "culture": "culture_02",
        "floor": 24.328232272429158,
        "regret": 31.388735674682387
      },
      {
        "culture": "culture_03",
        "floor": 24.367938396947178,
        "regret": 8.653414189383351
      },
      {
        "culture": "culture_04",
        "floor": 10.597267369187339,
        "regret": 24.124813942167734
      },
      {
        "culture": "culture_05",
        "floor": 28.554881464017257,
        "regret": 16.038917835145476
      },
      {
        "culture": "culture_06",
        "floor": 15.899149274366785,
        "regret": 30.25949820604933
      },
      {
        "culture": "culture_07",
        "floor": 40.22876377975173,
        "regret": 4.727777619367494
      },
      {
        "culture": "culture_08",
        "floor": 19.300319865464154,
        "regret": 18.738320709269203
      }
    ]
  }
}

## Identifiability
The forward and reverse exchange cycles admit large gross-flux ranges. Their interval widths, not a point estimate or assay residual, determine the reported identifiability flags.

## Computed diagnostics
All endpoints are LP optima. The selected witness is a feasible adversarial state attaining the global regret. Separate unit tests verify primal feasibility and support-function duality; the robustness workflow tests ordering, units, calibration translation and scientifically wrong decision procedures.

## Limitations
This is a synthetic reduced carbon-equivalent network with stipulated affine response surfaces. The assay is a calibrated linear tracer fingerprint, not a nonlinear raw mass-isotopomer model. Bounded errors are deterministic admissibility bounds, not confidence intervals. Findings do not establish clinical efficacy.

## Numerical identifiability diagnostics
[
  {
    "culture": "culture_01",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_02",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_03",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_04",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_05",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_06",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_07",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  },
  {
    "culture": "culture_08",
    "identifiable_count": 2,
    "widest_interval": 16.0,
    "widest_reaction": "hexose_activation"
  }
]
