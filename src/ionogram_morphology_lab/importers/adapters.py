"""MAT load adapters: scipy v5/v7, h5py v7.3, optional MATLAB, known KFU profile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.importers.mat_inventory import inventory_mat, _is_hdf5_mat
from ionogram_morphology_lab.security import default_blocklist


@dataclass
class LoadedMatrix:
    data: np.ndarray
    variable_name: str
    adapter: str
    source_path: str
    notes: str = ""


def select_adapter(path: Path | str) -> str:
    p = Path(path)
    if _is_hdf5_mat(p):
        return "hdf5_mat_v73"
    inv = inventory_mat(p)
    if not inv.readable:
        return "unreadable"
    names = {v.name for v in inv.variables}
    if "Amp_all" in names and any(
        v.name == "Amp_all" and v.shape == (368640, 400) for v in inv.variables
    ):
        return "known_kfu_cyclone"
    return "scipy_mat_v5"


def _load_scipy_variable(path: Path, variable: str) -> np.ndarray:
    from scipy.io import loadmat

    mat = loadmat(str(path), variable_names=[variable], simplify_cells=True)
    if variable not in mat:
        raise KeyError(f"missing_variable:{variable}")
    arr = np.asarray(mat[variable])
    return arr


def _load_h5py_variable(path: Path, variable: str) -> np.ndarray:
    import h5py

    with h5py.File(path, "r") as f:
        if variable not in f:
            # try nested
            key = variable
            if key not in f:
                raise KeyError(f"missing_variable:{variable}")
        ds = f[variable]
        return np.asarray(ds[()])


def load_amplitude_matrix(
    path: Path | str,
    variable: str = "Amp_all",
    adapter: str | None = None,
) -> LoadedMatrix:
    """Load amplitude matrix read-only. Does not alter the MAT file."""
    p = default_blocklist().assert_allowed(path)
    ad = adapter or select_adapter(p)
    if ad == "unreadable":
        raise OSError("unreadable_disk_or_format")
    if ad in ("scipy_mat_v5", "known_kfu_cyclone", "generic_user_profile"):
        data = _load_scipy_variable(p, variable)
        return LoadedMatrix(
            data=data,
            variable_name=variable,
            adapter=ad,
            source_path=str(p),
            notes="read_only_scipy",
        )
    if ad == "hdf5_mat_v73":
        data = _load_h5py_variable(p, variable)
        return LoadedMatrix(
            data=data,
            variable_name=variable,
            adapter=ad,
            source_path=str(p),
            notes="read_only_h5py",
        )
    if ad == "optional_matlab_engine":
        return _load_matlab_engine(p, variable)
    raise ValueError(f"unsupported_adapter:{ad}")


def _load_matlab_engine(path: Path, variable: str) -> LoadedMatrix:
    try:
        import matlab.engine  # type: ignore
    except ImportError as exc:
        raise RuntimeError("matlab_engine_not_available") from exc
    eng = matlab.engine.start_matlab()
    try:
        eng.cd(str(path.parent), nargout=0)
        eng.eval(f"tmp_iml = load('{path.name}', '{variable}');", nargout=0)
        data = np.asarray(eng.eval(f"tmp_iml.{variable}"))
    finally:
        eng.quit()
    return LoadedMatrix(
        data=data,
        variable_name=variable,
        adapter="optional_matlab_engine",
        source_path=str(path),
        notes="optional_matlab",
    )


def extract_frame_kfu(
    amp_all: np.ndarray,
    matlab_index: int,
    height_bins: int = 256,
    frequency_bins: int = 400,
) -> np.ndarray:
    """
    Extract one frame from KFU Cyclone Amp_all layout.
    matlab_index is 1-based; rows = (i-1)*height_bins : i*height_bins.
    Returns copy — never mutates amp_all.
    Supports full-day (1440) or smaller stacked test matrices.
    """
    if amp_all.ndim == 3 and amp_all.shape[1:] == (height_bins, frequency_bins):
        n_frames = amp_all.shape[0]
        if not (1 <= matlab_index <= n_frames):
            raise IndexError(f"frame_index_out_of_range:{matlab_index}")
        return np.array(amp_all[matlab_index - 1], copy=True)
    if amp_all.ndim != 2 or amp_all.shape[1] != frequency_bins:
        raise ValueError(f"unexpected_shape:{amp_all.shape}")
    if amp_all.shape[0] % height_bins != 0:
        raise ValueError(f"unexpected_shape:{amp_all.shape}")
    n_frames = amp_all.shape[0] // height_bins
    if not (1 <= matlab_index <= n_frames):
        raise IndexError(f"frame_index_out_of_range:{matlab_index}")
    r0 = (matlab_index - 1) * height_bins
    r1 = matlab_index * height_bins
    return np.array(amp_all[r0:r1, :], copy=True)
