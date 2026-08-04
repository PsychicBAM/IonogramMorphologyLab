"""Synthetic ionogram-like matrices for tests only — not scientific validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

SYNTHETIC_CLASSES = [
    "smooth_trace",
    "horizontally_diffuse",
    "vertically_diffuse",
    "mixed_diffuse",
    "clean_double_branch",
    "vertical_interference",
    "low_signal",
    "all_zero",
    "nonfinite_corruption",
]


def generate_synthetic_case(kind: str, height: int = 256, width: int = 400, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    frame = np.zeros((height, width), dtype=np.float64)
    # background noise
    if kind != "all_zero":
        frame += rng.normal(0, 2.0, size=frame.shape)

    def add_trace(f0: int, h0: float, slope: float, amp: float, h_spread: float, f_spread: float) -> None:
        for j in range(width):
            i_center = h0 + slope * (j - f0)
            for di in range(-int(3 * h_spread) - 1, int(3 * h_spread) + 2):
                i = int(round(i_center + di))
                if 0 <= i < height:
                    for dj in range(-int(3 * f_spread) - 1, int(3 * f_spread) + 2):
                        jj = j + dj
                        if 0 <= jj < width:
                            frame[i, jj] += amp * np.exp(
                                -0.5 * ((di / max(h_spread, 0.5)) ** 2 + (dj / max(f_spread, 0.5)) ** 2)
                            )

    if kind == "smooth_trace":
        add_trace(50, 80, 0.15, 80, 1.2, 1.0)
    elif kind == "horizontally_diffuse":
        # Near-flat ridge so frequency broadening is not a slope chord artifact.
        add_trace(50, 90, 0.02, 70, 1.5, 8.0)
    elif kind == "vertically_diffuse":
        # Compact tall echo: range thickness without a long frequency ridge.
        for i in range(70, 165):
            for j in range(188, 208):
                frame[i, j] += 85.0 * np.exp(
                    -0.5
                    * (
                        ((i - 117) / 28.0) ** 2
                        + ((j - 198) / 4.0) ** 2
                    )
                )
    elif kind == "mixed_diffuse":
        # Compact filled blob: substantial thickness on both axes without a long ridge.
        for i in range(85, 135):
            for j in range(140, 220):
                frame[i, j] += 90.0 * np.exp(
                    -0.5
                    * (
                        ((i - 110) / 18.0) ** 2
                        + ((j - 180) / 28.0) ** 2
                    )
                )
    elif kind == "clean_double_branch":
        add_trace(50, 85, 0.14, 70, 1.2, 1.0)
        add_trace(50, 110, 0.14, 65, 1.2, 1.0)
    elif kind == "vertical_interference":
        add_trace(40, 90, 0.1, 40, 1.5, 1.0)
        for col in (80, 81, 200, 201, 320):
            frame[:, col] += 120
    elif kind == "low_signal":
        add_trace(50, 90, 0.1, 5, 1.0, 1.0)
    elif kind == "all_zero":
        frame[:, :] = 0.0
    elif kind == "nonfinite_corruption":
        add_trace(50, 90, 0.1, 50, 1.0, 1.0)
        frame[10:20, 10:20] = np.nan
        frame[100, 100] = np.inf
    else:
        raise ValueError(f"unknown_synthetic_kind:{kind}")

    # Label marker in metadata via finite check — values themselves remain numeric
    return frame


def write_synthetic_mat_library(out_dir: Path | str | None = None) -> list[Path]:
    """Write synthetic Amp_all-shaped MAT files (single-frame tiled) for importer tests."""
    from scipy.io import savemat

    out_dir = Path(out_dir) if out_dir else app_root() / "synthetic_data"
    ensure_dir(out_dir)
    paths: list[Path] = []
    for i, kind in enumerate(SYNTHETIC_CLASSES):
        frame = generate_synthetic_case(kind, seed=i)
        # Build a tiny Amp_all-like stack: 3 frames only for speed (not full day)
        # For KFU-shaped tests, also write one full-shape lightweight zeros+frame file optionally.
        amp_small = np.zeros((3 * 256, 400), dtype=np.float64)
        for f in range(3):
            amp_small[f * 256 : (f + 1) * 256, :] = frame
        ff = np.linspace(1.5, 9.081, 400)
        path = out_dir / f"demo_{kind}.mat"
        savemat(
            str(path),
            {
                "Amp_all": amp_small,
                "ff": ff,
                "SYNTHETIC_LABEL": kind,
                "NOTE": "SYNTHETIC — not scientific validation",
            },
            do_compression=True,
        )
        paths.append(path)
    # One KFU-shaped sparse file for shape tests (mostly zeros — memory ok ~1GB? 368640*400*8 ~ 1.1GB — too big)
    # Instead write a manifest describing expected shape without huge file.
    (out_dir / "README.md").write_text(
        "# Synthetic test data\n\n"
        "All matrices are **synthetic** and must not be used as scientific validation.\n"
        "Classes: " + ", ".join(SYNTHETIC_CLASSES) + "\n"
        "Small Amp_all stacks are 3×256×400 for fast tests.\n",
        encoding="utf-8",
    )
    return paths
