# Scientific wrong-method controls

Run the independent estimator and then the control workflow:

    python tests/independent_oracle.py --data ../task/data --output-dir /tmp/cycle-independent
    python robustness_checks/run_checks.py --independent-output /tmp/cycle-independent

The controls evaluate a single bulk-compatible microscopic fit, independent extrema used as outer intervals, endpoint occupancy in place of first passage, and a convex relaxation that allows extra microscopic heterogeneity. Every control is scored by the package grader. The single-model record also checks its full reset moment fit and bulk turnover compatibility.

The independent estimator must pass. Presentation and report controls verify that correct science keeps credit. The convexification audit records its numerical gap without assuming it exceeds the scientific tolerance. These are numerical experiments, separate from external model evaluation.
