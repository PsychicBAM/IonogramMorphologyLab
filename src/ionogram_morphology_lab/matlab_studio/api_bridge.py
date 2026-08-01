"""Python-side MATLAB data API — efficient binary exchange for matrices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import savemat

from ionogram_morphology_lab.utils.paths import ensure_dir

# Documented API function names mirrored by MATLAB helpers under matlab_helpers/
API_FUNCTIONS = [
    "iml_get_current_frame",
    "iml_get_selected_frames",
    "iml_get_sequence",
    "iml_get_frequency_axis",
    "iml_get_range_axis",
    "iml_get_profile",
    "iml_get_metadata",
    "iml_report_progress",
    "iml_save_matrix",
    "iml_save_plot",
    "iml_save_table",
    "iml_register_feature",
    "iml_register_candidate_result",
    "iml_add_warning",
    "iml_add_provenance",
]


def prepare_run_workspace(
    work_dir: Path | str,
    *,
    current_frame: np.ndarray | None = None,
    selected_frames: list[np.ndarray] | None = None,
    frequency_axis: list[float] | np.ndarray | None = None,
    range_axis: list[float] | np.ndarray | None = None,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    frame_ids: list[int] | None = None,
    times: list[str] | None = None,
) -> Path:
    """Write bridge inputs for MATLAB helpers (MAT + JSON, not megabyte JSON matrices)."""
    work = ensure_dir(work_dir)
    mats: dict[str, Any] = {}
    if current_frame is not None:
        mats["iml_current_frame"] = np.asarray(current_frame)
    if selected_frames:
        # stack as 3D if shapes match
        arrs = [np.asarray(f) for f in selected_frames]
        mats["iml_selected_frames"] = np.stack(arrs, axis=0)
    if frequency_axis is not None:
        mats["iml_frequency_axis"] = np.asarray(frequency_axis, dtype=float)
    if range_axis is not None:
        mats["iml_range_axis"] = np.asarray(range_axis, dtype=float)
    if mats:
        savemat(str(work / "iml_bridge_inputs.mat"), mats, do_compression=True)
    meta = {
        "profile": profile or {},
        "metadata": metadata or {},
        "frame_ids": frame_ids or [],
        "times": times or [],
        "api_functions": API_FUNCTIONS,
    }
    (work / "iml_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    # registry files for features/results written by MATLAB helpers
    (work / "iml_registered_features.json").write_text("[]", encoding="utf-8")
    (work / "iml_registered_candidates.json").write_text("[]", encoding="utf-8")
    (work / "iml_warnings.json").write_text("[]", encoding="utf-8")
    (work / "iml_provenance.json").write_text("[]", encoding="utf-8")
    return work


def read_registered_side_effects(work_dir: Path | str) -> dict[str, Any]:
    work = Path(work_dir)

    def _load(name: str) -> Any:
        p = work / name
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    return {
        "features": _load("iml_registered_features.json"),
        "candidates": _load("iml_registered_candidates.json"),
        "warnings": _load("iml_warnings.json"),
        "provenance": _load("iml_provenance.json"),
    }
