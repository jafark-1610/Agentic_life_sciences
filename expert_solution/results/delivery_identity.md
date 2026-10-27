# Exact delivered source identity

The modular expert entry point builds on analysis_engine.py and artifacts.py. Runtime verification executes the standalone export. Its exact tested bytes are shipped at `results/verified_submission/run_pipeline.py`; its SHA-256 matches verification_result.json. The controlled missing-report and harmless-comment variants are shipped under results/delivered_controls/, also with matching hashes.

Run from the package root:

    python expert_solution/verify_submission.py --solver expert_solution/results/verified_submission --output-dir /tmp/rna-owner-receipt --replay-control

The receipt binds verifier, grader, configuration, rubric, snapshot, source, Python binary, effective user and mount permissions. This is local evidence. The delivery owner must reproduce and attest its own runtime before closing the L2 hold.
