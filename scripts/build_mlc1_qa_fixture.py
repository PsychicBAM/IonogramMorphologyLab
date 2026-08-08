"""Build a gitignored, synthetic-only ML-C.1 QA project."""
from __future__ import annotations

import sys
from pathlib import Path

from ionogram_morphology_lab.projects.model import create_project

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tests.mlc1_fixtures import build_mlc1_fixture


def main() -> int:
    root = ROOT
    project = create_project(
        "MLC1_Offline_Baselines_QA", workspace_parent=root / "workspaces",
    )
    project_root, manifest_set_id, *_ = build_mlc1_fixture(Path(project.root))
    (project_root / "README.md").write_text(
        "# SYNTHETIC QA DATA / NOT RESEARCH IONOGRAMS\n\n"
        "This project contains generated MAT stacks solely for ML-C.1 offline baseline QA.\n",
        encoding="utf-8",
    )
    print(project_root)
    print(manifest_set_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
