"""Phase 3C: documentation consistency and contract audit integrity."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_control_reference_has_phase3b_rows():
    text = (ROOT / "docs" / "USER_GUIDE_EN.md").read_text(encoding="utf-8")
    for label in (
        "Open Project",
        "Choose Project Folder",
        "Editor Tools",
        "More Actions",
        "Restore Defaults",
        "Save Expert Edits",
        "Morphology (structured list)",
    ):
        assert label in text
    meta = json.loads((ROOT / "docs" / "_control_reference_phase3c.json").read_text(encoding="utf-8"))
    assert meta["count"] >= 55


def test_user_guide_ru_no_known_english_prose():
    ru = (ROOT / "docs" / "USER_GUIDE_RU.md").read_text(encoding="utf-8")
    for phrase in (
        "Open next guided page",
        "Writable workspace",
        "Creates project",
        "Permission error",
        "Running job",
        "Editor open",
        "Writes manifest",
        "Persist or reload settings",
    ):
        assert phrase not in ru


def test_readme_projects_mentions_open_controls():
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Open Project" in en
    assert "Choose Project Folder" in en
    assert "Project name; Create project" not in en
    ru = (ROOT / "README_RU.md").read_text(encoding="utf-8")
    assert "Открыть проект" in ru
    assert "Выбрать папку проекта" in ru


def test_contract_audit_matches_count_contracts():
    from ionogram_morphology_lab.matlab_studio.method_contracts import count_contracts

    data = json.loads((ROOT / "docs" / "MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.json").read_text(encoding="utf-8"))
    totals = count_contracts()
    summary = data["summary"]
    assert summary["declared"] == totals["declared"] == 82
    assert summary["diagnostic_figures"] == totals["diagnostic_figures"] == 32
    assert summary["values_only"] == totals["values_only"] == 5
    assert len(data["methods"]) == 82
    # Runtime verification must not silently equal all figure methods
    assert len(summary.get("figure_outputs_confirmed") or []) < totals["diagnostic_figures"]


def test_validate_phase3c_docs_script_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_phase3c_docs.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_packaged_ui_manual_qa_exists():
    text = (ROOT / "docs" / "PACKAGED_UI_MANUAL_QA.md").read_text(encoding="utf-8")
    assert "1366" in text and "1920" in text
    assert "125%" in text and "150%" in text
