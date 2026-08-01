"""Data-quality audit for MAT files and frames."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix, extract_frame_kfu
from ionogram_morphology_lab.security import ForbiddenPathError, default_blocklist


@dataclass
class AuditResult:
    path: str
    status: str
    inventory_status: str
    adapter: str | None = None
    sha256: str | None = None
    variables: list[dict[str, Any]] = field(default_factory=list)
    expected_variable: str | None = None
    shape: tuple[int, ...] | None = None
    finite_fraction: float | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_mat_path(
    path: Path | str,
    profile: dict[str, Any] | None = None,
) -> AuditResult:
    """Audit a MAT path without modifying it. Isolates CRC/unreadable errors."""
    try:
        default_blocklist().assert_allowed(path)
    except ForbiddenPathError as exc:
        return AuditResult(
            path=str(path),
            status="blocked_path",
            inventory_status="blocked",
            error=str(exc),
        )

    inv = inventory_mat(path)
    if not inv.readable:
        status = inv.status if inv.status in ("CRC_error", "unreadable") else "unreadable"
        return AuditResult(
            path=str(path),
            status=status,
            inventory_status=inv.status,
            adapter=inv.adapter,
            sha256=inv.sha256,
            error=inv.error,
        )

    amp_name = (profile or {}).get("amplitude_variable_name", "Amp_all")
    expected_shape = (profile or {}).get("expected_amplitude_shape")
    vars_dicts = [asdict(v) if hasattr(v, "__dataclass_fields__") else v for v in inv.variables]
    # VariableInfo -> dict
    from dataclasses import asdict as _asdict
    from ionogram_morphology_lab.importers.mat_inventory import VariableInfo

    vars_dicts = [_asdict(v) if isinstance(v, VariableInfo) else v for v in inv.variables]

    names = {v.name for v in inv.variables}
    warnings: list[str] = []
    if amp_name not in names:
        return AuditResult(
            path=str(path),
            status="insufficient_metadata",
            inventory_status=inv.status,
            adapter=inv.adapter,
            sha256=inv.sha256,
            variables=vars_dicts,
            expected_variable=amp_name,
            error=f"missing_variable:{amp_name}",
            warnings=["expected amplitude variable not found"],
        )

    try:
        loaded = load_amplitude_matrix(path, variable=amp_name, adapter=inv.adapter if inv.adapter != "known_kfu_cyclone" else None)
        shape = tuple(loaded.data.shape)
        finite_frac = float(np.isfinite(loaded.data).mean())
    except Exception as exc:  # noqa: BLE001
        return AuditResult(
            path=str(path),
            status="unreadable",
            inventory_status=inv.status,
            adapter=inv.adapter,
            sha256=inv.sha256,
            variables=vars_dicts,
            expected_variable=amp_name,
            error=str(exc),
        )

    status = "valid"
    if expected_shape and list(shape) != list(expected_shape):
        status = "unexpected_shape"
        warnings.append(f"shape {shape} != expected {expected_shape}")
    if finite_frac < 1.0:
        status = "valid_with_warning" if status == "valid" else status
        if finite_frac < 0.5:
            status = "nonfinite_data"
        warnings.append(f"finite_fraction={finite_frac:.4f}")
    if np.nanmax(np.abs(np.nan_to_num(loaded.data))) == 0:
        status = "all_zero"
        warnings.append("entire matrix is zero")

    return AuditResult(
        path=str(path),
        status=status,
        inventory_status=inv.status,
        adapter=loaded.adapter,
        sha256=inv.sha256,
        variables=vars_dicts,
        expected_variable=amp_name,
        shape=shape,
        finite_fraction=finite_frac,
        warnings=warnings,
    )


def audit_frame(frame: np.ndarray) -> dict[str, Any]:
    """Per-frame quality flags (does not reject unusual morphology)."""
    arr = np.asarray(frame)
    finite = np.isfinite(arr)
    finite_frac = float(finite.mean()) if arr.size else 0.0
    vals = arr[finite] if finite.any() else np.array([0.0])
    zero = bool(np.all(vals == 0))
    # heuristic saturation: top 0.1% equal to max and max >> median
    saturated = False
    if vals.size > 100:
        mx = float(np.max(vals))
        med = float(np.median(vals))
        sat_frac = float(np.mean(vals >= mx * 0.99)) if mx > 0 else 0.0
        saturated = sat_frac > 0.05 and mx > max(med * 50, 1.0)
    low_signal = bool(np.percentile(vals, 99) <= np.percentile(vals, 50) * 1.05 + 1e-9)

    if not finite.any():
        status = "nonfinite_data"
    elif zero:
        status = "all_zero"
    elif finite_frac < 0.9:
        status = "nonfinite_data"
    elif low_signal:
        status = "valid_with_warning"
    else:
        status = "valid"

    return {
        "status": status,
        "finite_fraction": finite_frac,
        "all_zero": zero,
        "saturated": saturated,
        "low_signal": low_signal,
        "unusual_morphology_not_corruption": True,
    }
