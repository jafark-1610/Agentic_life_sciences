# Delivery-owner verification

This package includes local disposable-runtime evidence. It is not an attestation of the external evaluation service or an L2 closure. A delivery owner must rerun the final published source with equivalent isolation and retain its own identity-matched receipt.

From expert_solution, with Python, approved dependencies, Linux user namespaces and bubblewrap available:

    python export_solver.py --output /tmp/rna-delivered/run_pipeline.py
    python verify_submission.py --solver /tmp/rna-delivered --output-dir /tmp/rna-receipt --replay-control

Record SHA-256 of the submitted source, verifier, grader, rubric, config, Python executable and input manifest. verification_result.json records these identities, effective host IDs, the submitted-code canary's namespace IDs and mountinfo, actual invocations, and per-control source hashes. Source probes use Python and a child utility against an existing protected canary and private evaluator files. Public inputs are read-only; private evaluator files are unmounted; network is isolated.

The positive computation must pass original and regenerated data. The missing-report control must retain scientific credit and receive 95; the harmless private-directory comment control must receive 100. The parent-5-only measurement replacement keeps metadata bytes unchanged: base must respond, and leave_parent_out scientific results must remain invariant. A metadata-keyed cache that passes the original fixture must fail altered measurements with identical metadata. All source controls must execute successfully, so failures are not attributed to crashes.

If bubblewrap or the matching disposable-runtime capabilities are unavailable, the verifier returns BLOCKED. Do not reinterpret unavailable isolation as a solver failure or claim that the included local receipt matches another delivery host. Reproduce the namespace profile in an owner-managed environment before closing the runtime evidence hold.
