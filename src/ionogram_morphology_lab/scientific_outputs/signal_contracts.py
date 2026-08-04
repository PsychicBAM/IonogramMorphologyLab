"""Load and apply MAT signal contracts (Phase 4A)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from ionogram_morphology_lab.importers.adapters import extract_frame_kfu
from ionogram_morphology_lab.utils.paths import app_root


@dataclass(frozen=True)
class FrameRowRange:
    frame_index: int  # 1-based
    row_start: int  # inclusive, 0-based
    row_end_exclusive: int
    height_bins: int = 256
    frequency_bins: int = 400

    @property
    def matlab_row_start_1based(self) -> int:
        return self.row_start + 1

    @property
    def matlab_row_end_1based(self) -> int:
        return self.row_end_exclusive


def contracts_path() -> Path:
    return app_root() / "knowledge_base" / "SIGNAL_CONTRACTS.yaml"


STATUS_VOCABULARY = frozenset(
    {
        "verified",
        "provisionally_verified",
        "source_supported",
        "project_heuristic",
        "unavailable",
        "unresolved",
        "disabled",
    }
)


def load_signal_contracts() -> dict[str, Any]:
    path = contracts_path()
    if not path.is_file():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # Phase 4A.1 compatibility: expose accepted_shapes even if an older file
    # still has accepted_shape_variants (numeric entries only).
    for c in data.get("contracts") or []:
        if "accepted_shapes" not in c and "accepted_shape_variants" in c:
            shapes = []
            for entry in c.get("accepted_shape_variants") or []:
                if isinstance(entry, list) and all(isinstance(x, (int, float)) for x in entry):
                    shapes.append([int(x) for x in entry])
            c["accepted_shapes"] = shapes
            c.setdefault("shape_constraints", {})
            c.setdefault("optional_presence", False)
            c.setdefault("verification_evidence", [])
            c.setdefault(
                "accepted_dtypes",
                [c["dtype"]] if isinstance(c.get("dtype"), str) and c.get("dtype") != "unresolved" else [],
            )
    return data


def validate_contract_schema(data: dict[str, Any] | None = None) -> list[str]:
    """Validate Phase 4A.1 structured shape/dtype/status schema."""
    data = data or load_signal_contracts()
    errors: list[str] = []
    for c in data.get("contracts") or []:
        cid = c.get("contract_id", "<missing>")
        for field in (
            "accepted_shapes",
            "shape_constraints",
            "accepted_dtypes",
            "optional_presence",
            "verification_evidence",
            "verification_status",
        ):
            if field not in c:
                errors.append(f"{cid}: missing {field}")
        # accepted_shapes must be a list of numeric shape lists only
        shapes = c.get("accepted_shapes")
        if shapes is None:
            pass
        elif not isinstance(shapes, list):
            errors.append(f"{cid}: accepted_shapes must be a list")
        else:
            for i, sh in enumerate(shapes):
                if not isinstance(sh, list) or not sh or not all(isinstance(x, int) for x in sh):
                    errors.append(f"{cid}: accepted_shapes[{i}] must be a list of ints (no notes)")
        if "accepted_shape_variants" in c:
            # Allowed only as legacy; must not mix notes if still present
            for i, entry in enumerate(c.get("accepted_shape_variants") or []):
                if isinstance(entry, dict):
                    errors.append(
                        f"{cid}: accepted_shape_variants[{i}] mixes notes — use shape_constraints/optional_presence"
                    )
        status = c.get("verification_status")
        if status not in STATUS_VOCABULARY:
            errors.append(f"{cid}: invalid verification_status {status!r}")
        cal = c.get("calibration_status")
        if cal is not None and cal not in STATUS_VOCABULARY:
            errors.append(f"{cid}: invalid calibration_status {cal!r}")
        sc = c.get("shape_constraints") or {}
        if not isinstance(sc, dict):
            errors.append(f"{cid}: shape_constraints must be a mapping")
        else:
            for key in ("frames_per_file", "rows_per_frame", "dim1", "axis_length", "ndim"):
                if key in sc and sc[key] is not None and not isinstance(sc[key], int):
                    errors.append(f"{cid}: shape_constraints.{key} must be int")
        dtypes = c.get("accepted_dtypes")
        if dtypes is not None and not isinstance(dtypes, list):
            errors.append(f"{cid}: accepted_dtypes must be a list")
        if "optional_presence" in c and not isinstance(c.get("optional_presence"), bool):
            errors.append(f"{cid}: optional_presence must be bool")
        # Nested axis status vocabulary
        for axis_name in ("frame_axis", "range_axis", "frequency_axis", "time_axis"):
            axis = c.get(axis_name)
            if isinstance(axis, dict):
                st = axis.get("verification_status")
                if st is not None and st not in STATUS_VOCABULARY:
                    errors.append(f"{cid}.{axis_name}: invalid verification_status {st!r}")
                if axis_name == "frame_axis":
                    for k in ("frames_per_file", "height_bins", "rows_per_frame"):
                        if k in axis and axis[k] is not None and not isinstance(axis[k], int):
                            errors.append(f"{cid}.{axis_name}.{k} must be int")
                if axis_name in ("range_axis", "frequency_axis") and "bins" in axis:
                    if axis["bins"] is not None and not isinstance(axis["bins"], int):
                        errors.append(f"{cid}.{axis_name}.bins must be int")
    return errors


def list_contracts(profile_id: str | None = None) -> list[dict[str, Any]]:
    data = load_signal_contracts()
    items = list(data.get("contracts") or [])
    if profile_id:
        items = [c for c in items if c.get("profile_id") == profile_id]
    return items


def get_contract(contract_id: str) -> dict[str, Any]:
    for c in list_contracts():
        if c.get("contract_id") == contract_id:
            return c
    raise KeyError(contract_id)


def get_contract_by_variable(variable_name: str, profile_id: str = "kfu_cyclone_2013_2014") -> dict[str, Any] | None:
    for c in list_contracts(profile_id):
        if c.get("variable_name") == variable_name:
            return c
    return None


def frame_row_range(frame_index: int, height_bins: int = 256, frequency_bins: int = 400) -> FrameRowRange:
    """Canonical KFU stacked-row mapping (1-based frame index)."""
    if frame_index < 1:
        raise IndexError(f"frame_index_out_of_range:{frame_index}")
    r0 = (frame_index - 1) * height_bins
    r1 = frame_index * height_bins
    return FrameRowRange(
        frame_index=frame_index,
        row_start=r0,
        row_end_exclusive=r1,
        height_bins=height_bins,
        frequency_bins=frequency_bins,
    )


def extract_frame_consistent(
    amp_all: np.ndarray,
    frame_index: int,
    *,
    height_bins: int = 256,
    frequency_bins: int = 400,
) -> tuple[np.ndarray, FrameRowRange]:
    """Same mapping as viewer/batch/MATLAB bridge — returns frame copy + row provenance."""
    rng = frame_row_range(frame_index, height_bins, frequency_bins)
    frame = extract_frame_kfu(amp_all, frame_index, height_bins, frequency_bins)
    if frame.shape != (height_bins, frequency_bins):
        raise ValueError(f"unexpected_frame_shape:{frame.shape}")
    return frame, rng


def phase_interpretation_message(lang: str = "en") -> str:
    c = get_contract_by_variable("Phs_all") or {}
    if lang == "ru":
        return c.get(
            "ui_message_ru",
            "Фазовые данные доступны, но их научная интерпретация для этого профиля не подтверждена.",
        )
    return c.get(
        "ui_message_en",
        "Phase data are available, but their scientific interpretation is not verified for this profile.",
    )


def phase_automatic_rules_enabled() -> bool:
    c = get_contract_by_variable("Phs_all") or {}
    return bool(c.get("automatic_rules_enabled", False))


def match_inventory_to_contracts(variables: list[Any], profile_id: str = "kfu_cyclone_2013_2014") -> list[dict[str, Any]]:
    """Return match records for inventory variables against contracts."""
    by_name = {getattr(v, "name", None) or v.get("name"): v for v in variables}
    out = []
    for c in list_contracts(profile_id):
        name = c.get("variable_name")
        present = name in by_name
        shape = None
        dtype = None
        if present:
            v = by_name[name]
            shape = tuple(getattr(v, "shape", None) or (v.get("shape") if isinstance(v, dict) else None) or ())
            dtype = getattr(v, "dtype", None) or (v.get("dtype") if isinstance(v, dict) else None)
        expected = c.get("expected_shape")
        shape_ok = False
        if present and expected not in (None, "unresolved") and isinstance(expected, list):
            shape_ok = list(shape) == list(expected) if shape else False
            # Accept N*256 x 400 for Amp_all teaching stacks
            if not shape_ok and name == "Amp_all" and shape and len(shape) == 2 and shape[1] == 400:
                shape_ok = shape[0] % 256 == 0
        out.append(
            {
                "contract_id": c.get("contract_id"),
                "variable_name": name,
                "present": present,
                "shape": shape,
                "dtype": dtype,
                "shape_ok": shape_ok if present else None,
                "verification_status": c.get("verification_status"),
                "phase_warning": name == "Phs_all" and present,
            }
        )
    return out


def frame_stats(frame: np.ndarray) -> dict[str, Any]:
    """Compute stats without misreporting float analysis dtype as the source MAT dtype."""
    source = np.asarray(frame)
    source_dtype = str(source.dtype)
    source_shape = list(source.shape)
    # Float conversion only for numerical statistics
    analysis = np.asarray(source, dtype=np.float64)
    analysis_dtype = str(analysis.dtype)
    analysis_shape = list(analysis.shape)
    finite = np.isfinite(analysis)
    n = analysis.size
    n_finite = int(finite.sum())
    n_nan = int(np.isnan(analysis).sum())
    n_inf = int(np.isinf(analysis).sum())
    vals = analysis[finite]
    # Heuristic saturation unless source dtype / instrument saturation is verified
    sat_frac = 0.0
    if vals.size:
        vmax = float(np.max(vals))
        if vmax > 0:
            sat_frac = float(np.mean(vals >= 0.999 * vmax))
    return {
        "source_dtype": source_dtype,
        "analysis_dtype": analysis_dtype,
        "source_shape": source_shape,
        "analysis_shape": analysis_shape,
        # Backward-compatible aliases (source, not analysis)
        "shape": source_shape,
        "dtype": source_dtype,
        "min": float(np.min(vals)) if vals.size else None,
        "max": float(np.max(vals)) if vals.size else None,
        "median": float(np.median(vals)) if vals.size else None,
        "finite_fraction": (n_finite / n) if n else 0.0,
        "nan_count": n_nan,
        "inf_count": n_inf,
        "saturated_fraction_heuristic": sat_frac,
        "saturation_is_heuristic": True,
    }
