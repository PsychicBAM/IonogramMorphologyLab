"""Reproducibility manifests for analysis runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.projects.model import AnalysisProject
from ionogram_morphology_lab.utils.paths import ensure_dir


def write_reproducibility_manifest(
    path: Path | str,
    project: AnalysisProject,
    run_id: str,
    config: dict[str, Any],
    n_results: int,
) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    payload = {
        "application": "Ionogram Morphology Lab",
        "application_version": __version__,
        "project_id": project.project_id,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "language": project.language,
        "profile_id": project.profile_id,
        "rule_pack_version": project.rule_pack_version,
        "reference_atlas_version": project.reference_atlas_version,
        "model_version": project.model_version,
        "config": config,
        "n_results": n_results,
        "random_seed": config.get("seed", 0),
        "notes": [
            "Original MAT files were not modified",
            "No Article 3 blinded materials were accessed",
            "No final ML model was trained",
            "Morphology results are candidate classifications requiring expert review",
        ],
        "network_telemetry": "disabled",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
