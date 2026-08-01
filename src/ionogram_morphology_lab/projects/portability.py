"""Portable project packages without source MAT data by default."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any


PACKAGE_MANIFEST = "package_manifest.json"
_INCLUDED_DIRS = ("config", "configs", "scripts", "models", "results", "runs")


def _safe_members(archive: zipfile.ZipFile, destination: Path) -> list[zipfile.ZipInfo]:
    root = destination.resolve()
    members: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        target = (destination / info.filename).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"unsafe_package_member:{info.filename}")
        members.append(info)
    return members


def export_project_package(
    project_root: Path | str,
    destination: Path | str,
    *,
    include_source_mat: bool = False,
) -> Path:
    """Package project metadata and derived artifacts, excluding source MAT by default."""
    root = Path(project_root)
    if not (root / "project.json").is_file():
        raise FileNotFoundError(root / "project.json")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [root / "project.json"]
    for name in _INCLUDED_DIRS:
        folder = root / name
        if folder.exists():
            files.extend(p for p in folder.rglob("*") if p.is_file())
    if include_source_mat:
        files.extend(p for p in root.rglob("*.mat") if p.is_file())
    files = sorted(set(files))
    manifest: dict[str, Any] = {
        "format": "iml-project-package-v1",
        "includes_source_mat": include_source_mat,
        "files": [str(p.relative_to(root).as_posix()) for p in files],
    }
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
        archive.writestr(PACKAGE_MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False))
    return destination


def import_project_package(
    package_path: Path | str,
    destination: Path | str,
    *,
    relink_source_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Extract a package and optionally relink source paths in its project metadata."""
    package = Path(package_path)
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        members = _safe_members(archive, root)
        archive.extractall(root, members)
    project_path = root / "project.json"
    if not project_path.exists():
        raise ValueError("package_missing_project_json")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    relinked = False
    if relink_source_paths is not None:
        project["source_paths"] = list(relink_source_paths)
        project_path.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
        relinked = True
    return {
        "project_root": str(root),
        "project": project,
        "relinked_source_paths": relinked,
        "source_paths": project.get("source_paths", []),
    }
