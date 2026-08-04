"""Local analysis project model and run workspace layout."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.database.project_db import ProjectDatabase
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


MORPHOLOGY_FOLDERS = [
    "frequency",
    "range",
    "mixed",
    "none",
    "indeterminate",
    "artifact",
    "not_assessable",
    "abstain",
    "disagreement",
]


@dataclass
class AnalysisProject:
    project_id: str
    name: str
    language: str
    root: str
    created_at: str
    profile_id: str = "kfu_cyclone_2013_2014"
    source_paths: list[str] = field(default_factory=list)
    active_source_path: str | None = None
    application_version: str = __version__
    rule_pack_version: str = "IML1-0.1.0"
    reference_atlas_version: str = "IML1-0.1.0"
    model_version: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisProject":
        """Load project.json with backward-compatible defaults."""
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @property
    def path(self) -> Path:
        return Path(self.root)


@dataclass
class RunLayout:
    run_id: str
    root: Path

    def ensure(self) -> "RunLayout":
        for sub in (
            "config",
            "audit",
            "raw_renders",
            "diagnostic_renders",
            "masks",
            "features",
            "predictions",
            "reports",
            "exports",
            "logs",
        ):
            ensure_dir(self.root / sub)
        for m in MORPHOLOGY_FOLDERS:
            ensure_dir(self.root / "by_morphology" / m)
        return self


def default_workspaces() -> Path:
    return ensure_dir(app_root() / "workspaces")


def create_project(
    name: str,
    language: str = "en",
    workspace_parent: Path | str | None = None,
    profile_id: str = "kfu_cyclone_2013_2014",
) -> AnalysisProject:
    parent = Path(workspace_parent) if workspace_parent else default_workspaces()
    ensure_dir(parent)
    project_id = uuid.uuid4().hex[:12]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_") or "project"
    root = ensure_dir(parent / f"{safe}_{project_id}")
    project = AnalysisProject(
        project_id=project_id,
        name=name,
        language=language if language in ("en", "ru") else "en",
        root=str(root),
        created_at=datetime.now(timezone.utc).isoformat(),
        profile_id=profile_id,
    )
    (root / "project.json").write_text(
        json.dumps(project.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    db = ProjectDatabase(root / "project.sqlite")
    db.initialize()
    db.insert_project(project.to_dict())
    ensure_dir(root / "runs")
    ensure_dir(root / "audit")
    return project


def new_run(project: AnalysisProject) -> RunLayout:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    layout = RunLayout(run_id=run_id, root=Path(project.root) / "runs" / run_id).ensure()
    return layout
