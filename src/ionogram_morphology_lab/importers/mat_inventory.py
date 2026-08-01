"""MAT file variable inventory (v5/v7 via SciPy; v7.3 via h5py)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.security import default_blocklist
from ionogram_morphology_lab.utils.hashing import sha256_file


@dataclass
class VariableInfo:
    name: str
    shape: tuple[int, ...] | None
    dtype: str | None
    notes: str = ""


@dataclass
class MatInventory:
    path: str
    adapter: str
    readable: bool
    status: str
    sha256: str | None = None
    matlab_format: str | None = None
    variables: list[VariableInfo] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _is_hdf5_mat(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
        return sig == b"\x89HDF\r\n\x1a\n"
    except OSError:
        return False


def _inventory_scipy(path: Path) -> MatInventory:
    from scipy.io import loadmat, whosmat

    try:
        infos = whosmat(str(path))
        variables = [
            VariableInfo(name=n, shape=tuple(s) if s is not None else None, dtype=str(t))
            for n, s, t in infos
        ]
        sha = sha256_file(path)
        return MatInventory(
            path=str(path),
            adapter="scipy_mat_v5",
            readable=True,
            status="valid",
            sha256=sha,
            matlab_format="v5_or_v7",
            variables=variables,
        )
    except Exception as exc:  # noqa: BLE001 — inventory must isolate errors
        msg = str(exc)
        status = "unreadable"
        if "CRC" in msg.upper() or "errno 23" in msg.lower():
            status = "CRC_error"
        return MatInventory(
            path=str(path),
            adapter="scipy_mat_v5",
            readable=False,
            status=status,
            error=msg,
        )


def _inventory_h5py(path: Path) -> MatInventory:
    import h5py

    variables: list[VariableInfo] = []
    try:
        with h5py.File(path, "r") as f:
            def visit(name: str, obj: Any) -> None:
                if isinstance(obj, h5py.Dataset):
                    variables.append(
                        VariableInfo(
                            name=name,
                            shape=tuple(obj.shape),
                            dtype=str(obj.dtype),
                            notes="hdf5_dataset",
                        )
                    )

            f.visititems(visit)
        return MatInventory(
            path=str(path),
            adapter="hdf5_mat_v73",
            readable=True,
            status="valid",
            sha256=sha256_file(path),
            matlab_format="v7.3",
            variables=variables,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        status = "CRC_error" if "CRC" in msg.upper() else "unreadable"
        return MatInventory(
            path=str(path),
            adapter="hdf5_mat_v73",
            readable=False,
            status=status,
            error=msg,
        )


def inventory_mat(path: Path | str) -> MatInventory:
    """Read-only inventory of a MAT file. Never modifies the source."""
    p = default_blocklist().assert_allowed(path)
    if not p.is_file():
        return MatInventory(
            path=str(p),
            adapter="none",
            readable=False,
            status="unreadable",
            error="not_a_file",
        )
    if _is_hdf5_mat(p):
        return _inventory_h5py(p)
    return _inventory_scipy(p)


def list_mat_files(folder: Path | str, recursive: bool = True) -> list[Path]:
    """List .mat files under folder (blocklist-checked)."""
    root = default_blocklist().assert_allowed(folder)
    pattern = "**/*.mat" if recursive else "*.mat"
    return sorted(root.glob(pattern))
