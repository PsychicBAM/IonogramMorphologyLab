"""Ionogram construction and rendering — raw unchanged; no hidden smoothing."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.rendering.display_transform import (
    default_kfu_display_identity,
    matplotlib_imshow_origin,
)
from ionogram_morphology_lab.utils.paths import ensure_dir


@dataclass
class RenderSpec:
    colormap: str = "jet"
    clim: tuple[float, float] | None = None
    scaling_method: str = "none"  # none | log_offset | percentile_display
    log_offset: float = 80.0
    data_quantiles: tuple[float, float] = (1.0, 99.0)
    axis_source: str = "profile"
    profile_source: str = ""
    render_version: str = "iml1-0.1.0"
    view_kind: str = "raw"  # raw | derived_diagnostic
    range_label_en: str = "Nominal virtual height"
    range_label_ru: str = "Номинальная виртуальная высота"
    frequency_label_en: str = "Frequency, MHz*"
    frequency_label_ru: str = "Частота, МГц*"
    warnings: list[str] = field(
        default_factory=lambda: [
            "nominal virtual-height axis",
            "not true physical height",
            "no hidden denoising/smoothing/interpolation",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.clim is not None:
            d["clim"] = list(self.clim)
        d["data_quantiles"] = list(self.data_quantiles)
        return d


def _display_array(frame: np.ndarray, spec: RenderSpec) -> np.ndarray:
    """Prepare display array without mutating original frame."""
    arr = np.asarray(frame, dtype=np.float64)
    if spec.scaling_method == "none":
        return arr
    if spec.scaling_method == "log_offset":
        return np.log(np.clip(arr, 0, None) + spec.log_offset)
    if spec.scaling_method == "percentile_display":
        return arr
    return arr


def render_raw_ionogram(
    frame: np.ndarray,
    frequency_axis: list[float] | np.ndarray,
    range_axis: list[float] | np.ndarray,
    out_path: Path | str | None = None,
    spec: RenderSpec | None = None,
    title: str = "",
) -> dict[str, Any]:
    """
    Render a single ionogram. Original matrix is never modified.
    Default scientific mode uses no smoothing / no interpolation.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    spec = spec or RenderSpec()
    original = np.asarray(frame)
    display = _display_array(original, spec)

    if spec.clim is not None:
        vmin, vmax = spec.clim
    else:
        finite = display[np.isfinite(display)]
        if finite.size:
            qlo, qhi = spec.data_quantiles
            vmin = float(np.percentile(finite, qlo))
            vmax = float(np.percentile(finite, qhi))
            if vmin == vmax:
                vmax = vmin + 1.0
        else:
            vmin, vmax = 0.0, 1.0

    freq = np.asarray(frequency_axis, dtype=float)
    rng = np.asarray(range_axis, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    # extent: left, right, bottom, top — axis xy
    extent = [
        float(freq[0]) if freq.size else 0.0,
        float(freq[-1]) if freq.size else float(original.shape[1]),
        float(rng[0]) if rng.size else 0.0,
        float(rng[-1]) if rng.size else float(original.shape[0]),
    ]
    # Canonical display: scientific matrix + origin matching DisplayOrientationIdentity
    orient = default_kfu_display_identity()
    # No interpolation — nearest neighbor only
    im = ax.imshow(
        display,
        origin=matplotlib_imshow_origin(orient),
        aspect="auto",
        cmap=spec.colormap,
        vmin=vmin,
        vmax=vmax,
        extent=extent,
        interpolation="nearest",
    )
    ax.set_xlabel(spec.frequency_label_en)
    ax.set_ylabel(spec.range_label_en)
    if title:
        ax.set_title(title)
    # Label derived views clearly
    footer = f"view={spec.view_kind}; scaling={spec.scaling_method}; {spec.warnings[0]}"
    fig.text(0.01, 0.01, footer, fontsize=7, ha="left")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    meta = {
        "render_spec": spec.to_dict(),
        "clim_used": [vmin, vmax],
        "raw_shape": list(original.shape),
        "raw_unchanged": True,
        "interpolation": "nearest",
        "smoothing": False,
        "display_orientation": orient.to_dict(),
        "scientific_matrix_mutated": False,
    }
    if out_path is not None:
        out_path = Path(out_path)
        ensure_dir(out_path.parent)
        fig.savefig(out_path, bbox_inches="tight")
        meta["path"] = str(out_path)
    plt.close(fig)
    # Integrity: original must be unchanged (caller owns it; we used asarray without write)
    return meta


def render_contact_sheet(
    frames: list[np.ndarray],
    frequency_axis: list[float] | np.ndarray,
    range_axis: list[float] | np.ndarray,
    out_path: Path | str,
    labels: list[str] | None = None,
    rows: int = 5,
    cols: int = 5,
    spec: RenderSpec | None = None,
) -> dict[str, Any]:
    """Render up to rows×cols temporal contact sheet."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    spec = spec or RenderSpec()
    n = min(len(frames), rows * cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.2, rows * 1.8), dpi=100)
    axes_flat = np.atleast_1d(axes).ravel()
    freq = np.asarray(frequency_axis, dtype=float)
    rng = np.asarray(range_axis, dtype=float)
    extent = [
        float(freq[0]) if freq.size else 0.0,
        float(freq[-1]) if freq.size else 1.0,
        float(rng[0]) if rng.size else 0.0,
        float(rng[-1]) if rng.size else 1.0,
    ]
    for i, ax in enumerate(axes_flat):
        if i < n:
            display = _display_array(frames[i], spec)
            finite = display[np.isfinite(display)]
            vmin = float(np.percentile(finite, 1)) if finite.size else 0.0
            vmax = float(np.percentile(finite, 99)) if finite.size else 1.0
            ax.imshow(
                display,
                origin=matplotlib_imshow_origin(default_kfu_display_identity()),
                aspect="auto",
                cmap=spec.colormap,
                vmin=vmin,
                vmax=vmax,
                extent=extent,
                interpolation="nearest",
            )
            if labels and i < len(labels):
                ax.set_title(labels[i], fontsize=7)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Temporal contact sheet (raw; nearest; no smoothing)", fontsize=9)
    out_path = Path(out_path)
    ensure_dir(out_path.parent)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {"path": str(out_path), "n_frames": n, "view_kind": spec.view_kind}
