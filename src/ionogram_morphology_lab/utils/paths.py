"""Path utilities for application root and safe path resolution."""

from __future__ import annotations

from pathlib import Path


def app_root() -> Path:
    """Return IonogramMorphologyLab application root (contains pyproject.toml)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "ionogram_morphology_lab").exists():
            return parent
    return here.parents[3]


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_under(base: Path | str, *parts: str) -> Path:
    """Resolve a path under base; reject escapes via '..'."""
    base_p = Path(base).resolve()
    candidate = (base_p.joinpath(*parts)).resolve()
    try:
        candidate.relative_to(base_p)
    except ValueError as exc:
        raise ValueError(f"Path escapes base directory: {candidate}") from exc
    return candidate
