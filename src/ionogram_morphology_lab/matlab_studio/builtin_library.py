"""Read-only index of matlab_builtin methods for MATLAB Studio."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


@dataclass
class BuiltinMethod:
    method_id: str
    category: str
    path: Path
    read_only: bool = True


def builtin_root() -> Path:
    return app_root() / "matlab_builtin"


def list_builtin_methods(category: str | None = None) -> list[BuiltinMethod]:
    root = builtin_root()
    if not root.exists():
        return []
    out: list[BuiltinMethod] = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        if folder.name in {"manifests", "tests"} and category not in (None, folder.name):
            pass
        cat = folder.name
        if category and cat != category:
            continue
        for m in sorted(folder.glob("*.m")):
            out.append(BuiltinMethod(method_id=m.stem, category=cat, path=m))
    return out


def read_builtin_source(method_id: str) -> tuple[BuiltinMethod, str]:
    for rec in list_builtin_methods():
        if rec.method_id == method_id:
            return rec, rec.path.read_text(encoding="utf-8")
    raise FileNotFoundError(method_id)


def create_editable_copy(
    method_id: str,
    *,
    project_root: Path | str | None = None,
) -> Path:
    """Copy built-in method into user/project library; never modify original."""
    rec, text = read_builtin_source(method_id)
    if project_root:
        dest_dir = ensure_dir(Path(project_root) / "matlab_user_methods" / rec.category)
    else:
        dest_dir = ensure_dir(app_root() / "user_library" / "matlab_methods" / rec.category)
    dest = dest_dir / f"{rec.method_id}_user.m"
    # avoid clobber without versioning suffix
    if dest.exists():
        i = 2
        while True:
            cand = dest_dir / f"{rec.method_id}_user_v{i}.m"
            if not cand.exists():
                dest = cand
                break
            i += 1
    header = (
        "% EDITABLE COPY of built-in method — original remains read-only\n"
        f"% Source: {rec.path.as_posix()}\n"
        "% Do not claim source-verified status without review.\n"
    )
    dest.write_text(header + text, encoding="utf-8")
    return dest


def restore_original_view(method_id: str) -> str:
    """Return original source text (does not overwrite user copies)."""
    _, text = read_builtin_source(method_id)
    return text


def export_method_package(method_id: str, dest_zip: Path | str) -> Path:
    import zipfile

    rec, _ = read_builtin_source(method_id)
    dest = Path(dest_zip)
    ensure_dir(dest.parent)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(rec.path, f"{rec.category}/{rec.path.name}")
        man = builtin_root() / "manifests" / f"{rec.category}.iml-matlab.yaml"
        if man.exists():
            z.write(man, f"manifests/{man.name}")
        readme = builtin_root() / "README_EN.md"
        if readme.exists():
            z.write(readme, "README_EN.md")
    return dest


def count_builtin_by_category() -> dict[str, int]:
    counts: dict[str, int] = {}
    for rec in list_builtin_methods():
        counts[rec.category] = counts.get(rec.category, 0) + 1
    return counts
