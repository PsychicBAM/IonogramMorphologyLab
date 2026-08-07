"""Thin export wrapper for ML-B.1 manifest bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore


def export_manifest_bundle(
    store: MLDatasetManifestStore,
    manifest_set_id: str,
    export_dir: Path | str | None = None,
    *,
    progress_cb: Callable[[int, str], None] | None = None,
    cancel_cb: Callable[[], bool] | None = None,
) -> Path:
    return store.export_bundle(
        manifest_set_id,
        export_dir,
        progress_cb=progress_cb,
        cancel_cb=cancel_cb,
    )
