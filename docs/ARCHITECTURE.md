# Architecture

The application is a local PySide6 desktop client. `app/` owns startup and settings; `ui/` presents pages; import/project modules own source references and manifests; analysis and rule modules produce candidate evidence; reporting exports derived artifacts. `matlab_studio/` is optional and isolated behind backends. Rule packs and instrument profiles are versioned data, not executable plug-ins.

Source MAT files are input-only in normal workflows. Workspaces contain project metadata, derived cache, results, logs and exports. Provenance flows from input fingerprint and profile through processing version, method/rule configuration and expert decision. UI code must not silently turn candidate output into a confirmed physical claim.

## ML dataset readiness (Phase ML-A.1)

`ml_dataset_readiness` is a project-local, candidate-independent audit layer above expert-review corpora, campaigns, and disagreement-analysis contamination records. It freezes immutable readiness audits under `review_dataset/ml_readiness/` (gitignored runtime), reports coverage/missingness/reviewer independence/holdout feasibility, and records a Readiness Gate. Outcome F authorizes ML-B manifest planning only. No training, no RuleEngine wiring, no accuracy/F1 claims.

## ML dataset manifests (Phase ML-B.1)

`ml_dataset_manifests` builds immutable train/development/untouched-holdout/excluded identity manifests above a frozen readiness audit. Runtime sets live under `review_dataset/ml_manifests/` (gitignored). Atomic groups are formed by a deterministic leakage graph (related-frame, sequence, source-date, and related policies). Final freeze requires Gate F; holdout reference labels are workflow-sealed (not cryptographic). No training, no ML-C, no RuleEngine wiring, no accuracy/F1 claims.
