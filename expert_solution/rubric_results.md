# Canonical submission evaluation

Scientific answer and diagnostic artifact score: 100/100.

Isolated original and regenerated executions: 100/100 each. Private-file denial, read-only task and offline-network probes passed. A stored-answer pipeline failed regenerated data even after refreshing its hashes. Detailed execution evidence is in results/verification_result.json.

Two Python/NumPy/SciPy runtimes produced byte-identical answers with zero differing leaves across all 8985 fields. The reported platform parameter drift is covered by regression tests. See results/cross_runtime_comparison.json and results/correction_scope.json. External platform revalidation remains pending.
