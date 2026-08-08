"""Source SHA resolution and single-frame loading for ML-C.1."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class SourcePathIndex:
    paths: dict[str, Path] = field(default_factory=dict)
    _cache: dict[Path, np.ndarray] = field(default_factory=dict, init=False, repr=False)

    def resolve(self, sha256: str) -> Path:
        try:
            return self.paths[sha256.lower()]
        except KeyError as exc:
            raise FileNotFoundError(f"Source SHA not indexed: {sha256}") from exc

    def resolve_frame(self, path: Path | str, frame_index: int) -> np.ndarray:
        source = Path(path)
        if source not in self._cache:
            self._cache[source] = load_amplitude_matrix(source).data
        frame, _ = extract_frame_consistent(self._cache[source], int(frame_index))
        return np.asarray(frame)


def build_index_from_directory(root: Path | str) -> SourcePathIndex:
    root_path = Path(root)
    paths = { _file_sha256(path).lower(): path for path in sorted(root_path.rglob("*.mat")) }
    return SourcePathIndex(paths)


def resolve_frame(path: Path | str, frame_index: int) -> np.ndarray:
    """Resolve one frame without a cache; use SourcePathIndex for a run cache."""
    frame, _ = extract_frame_consistent(load_amplitude_matrix(path).data, int(frame_index))
    return np.asarray(frame)
