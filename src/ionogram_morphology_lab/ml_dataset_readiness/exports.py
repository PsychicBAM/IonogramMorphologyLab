"""Export helpers for ML-A.1 readiness audits."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore


def export_readiness_bundle(
    store: MLDatasetReadinessStore,
    audit_id: str,
    export_dir: Path | None = None,
) -> Path:
    return store.export_report(audit_id, export_dir=export_dir)
