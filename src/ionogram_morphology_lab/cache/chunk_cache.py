"""Read-only-derived chunked cache for large MAT matrices (Zarr preferred)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir


@dataclass
class CacheProvenance:
    source_path: str
    source_sha256: str
    variable_name: str
    shape: list[int]
    dtype: str
    conversion: str
    created_at: str
    note: str = (
        "Derived cache only — not new scientific measurements. "
        "Original MAT remains authoritative and unmodified."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChunkedCache:
    """Create/load a Zarr cache beside the project workspace (never overwrites MAT)."""

    def __init__(self, cache_root: Path | str):
        self.cache_root = ensure_dir(cache_root)

    def cache_dir_for(self, source_sha: str, variable: str) -> Path:
        return self.cache_root / f"{source_sha[:16]}_{variable}"

    def build_from_array(
        self,
        array: np.ndarray,
        source_path: Path | str,
        variable_name: str,
        chunks: tuple[int, ...] | None = None,
    ) -> Path:
        import zarr

        source_path = Path(source_path)
        sha = sha256_file(source_path) if source_path.is_file() else "nosha"
        out = self.cache_dir_for(sha, variable_name)
        if out.exists():
            return out
        ensure_dir(out)
        arr = np.asarray(array)
        if chunks is None:
            # Prefer frame-friendly chunks for KFU layout
            if arr.shape == (368640, 400):
                chunks = (256, 400)
            else:
                chunks = tuple(min(256, s) for s in arr.shape)
        z = zarr.open_array(
            str(out / "data.zarr"),
            mode="w",
            shape=arr.shape,
            chunks=chunks,
            dtype=arr.dtype,
        )
        z[:] = arr
        prov = CacheProvenance(
            source_path=str(source_path),
            source_sha256=sha,
            variable_name=variable_name,
            shape=list(arr.shape),
            dtype=str(arr.dtype),
            conversion="zarr_chunked_copy",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        (out / "provenance.json").write_text(
            json.dumps(prov.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out

    def load_array(self, cache_dir: Path | str) -> np.ndarray:
        import zarr

        z = zarr.open_array(str(Path(cache_dir) / "data.zarr"), mode="r")
        return np.asarray(z[:])

    def load_provenance(self, cache_dir: Path | str) -> dict[str, Any]:
        p = Path(cache_dir) / "provenance.json"
        return json.loads(p.read_text(encoding="utf-8"))

    def delete_cache(self, cache_dir: Path | str) -> None:
        import shutil

        p = Path(cache_dir)
        if p.exists():
            shutil.rmtree(p)
