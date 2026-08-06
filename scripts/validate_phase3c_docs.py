#!/usr/bin/env python3
"""Phase 3C documentation consistency validators."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.matlab_studio.method_contracts import count_contracts

ERRORS: list[str] = []

REQUIRED_EN_CONTROLS = [
    "Open Project",
    "Choose Project Folder",
    "Open Recent Project",
    "Remove from Recent List",
    "Create Project",
    "Validate",
    "Save As",
    "Revert",
    "Compare with Saved",
    "Restore Defaults",
    "Editor Tools",
    "More Actions",
    "Values",
    "Figures",
    "Created Files",
    "Open Results Folder",
    "Show Generated Figures",
    "Export Result",
    "Add to Method Comparison",
    "Register MATLAB Plugin",
    "Run Again",
    "Technical Log",
    "Accept",
    "Reject",
    "Indeterminate",
    "Save Expert Edits",
    "Morphology (structured list)",
    "Interference (structured list)",
    "Rationale",
    "Save expert decision",
]

RU_FORBIDDEN_PROSE = [
    "Open next guided page",
    "Writable workspace",
    "Creates project",
    "Permission error",
    "Running job",
    "Editor open",
    "Writes manifest",
    "Missing values",
    "Persist settings",
    "Persist or reload settings",
]

PROJECTS_README_MARKERS_EN = [
    "Open Project",
    "Choose Project Folder",
    "Open Recent Project",
    "Current project",
    "unsaved",
]
PROJECTS_README_MARKERS_RU = [
    "Открыть проект",
    "Выбрать папку проекта",
    "недавн",
    "Текущ",
    "несохран",
]


def err(msg: str) -> None:
    ERRORS.append(msg)


def check_control_reference() -> None:
    en = (ROOT / "docs" / "USER_GUIDE_EN.md").read_text(encoding="utf-8")
    ru = (ROOT / "docs" / "USER_GUIDE_RU.md").read_text(encoding="utf-8")
    if "Complete control reference" not in en and "control reference" not in en.lower():
        err("USER_GUIDE_EN missing Complete control reference heading")
    en_rows = [ln for ln in en.splitlines() if ln.startswith("| ") and "RU label" not in ln and "------" not in ln]
    # Count table rows under control reference only
    section = en.split("Complete control reference")[-1].split("Scientific status")[0]
    rows = [ln for ln in section.splitlines() if ln.startswith("| ") and not ln.startswith("| Page") and not ln.startswith("|------")]
    if len(rows) < 55:
        err(f"USER_GUIDE_EN control rows too few: {len(rows)} (need Phase 3B coverage)")
    for label in REQUIRED_EN_CONTROLS:
        if label not in en:
            err(f"USER_GUIDE_EN missing control: {label}")
    for phrase in RU_FORBIDDEN_PROSE:
        # Allow phrase only inside EN label column patterns by checking RU guide body cells.
        if phrase in ru:
            err(f"USER_GUIDE_RU still contains English prose: {phrase!r}")
    meta = ROOT / "docs" / "_control_reference_phase3c.json"
    if meta.is_file():
        count = json.loads(meta.read_text(encoding="utf-8")).get("count", 0)
        if count != len(rows):
            err(f"control reference row count mismatch: table={len(rows)} meta={count}")


def check_readme_projects() -> None:
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README_RU.md").read_text(encoding="utf-8")
    # Prefer Projects details block; fall back to Projects and MAT section.
    def block(text: str, title: str) -> str:
        m = re.search(rf"<summary><strong>{title}</strong></summary>(.*?)</details>", text, re.S)
        return m.group(1) if m else ""

    def section(text: str, heading: str) -> str:
        m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        return m.group(1) if m else ""

    en_b = block(en, "Projects") or section(en, "Projects and MAT data")
    ru_b = block(ru, "Проекты") or section(ru, "Проекты и данные MAT")
    if "Project name; Create project" in en_b or en_b.strip() == "":
        err("README.md Projects section still lists only Create project / missing Open controls")
    for marker in PROJECTS_README_MARKERS_EN:
        if marker.lower() not in en_b.lower():
            err(f"README.md Projects missing marker: {marker}")
    for marker in PROJECTS_README_MARKERS_RU:
        if marker.lower() not in ru_b.lower():
            err(f"README_RU.md Projects missing marker: {marker}")


def check_screenshots() -> None:
    shot_dir = ROOT / "docs" / "assets" / "screenshots" / "v1.1.1"
    required = [
        "project_creation_en.png",
        "project_creation_ru.png",
        "matlab_studio_en.png",
        "matlab_studio_ru.png",
        "pipeline_builder_en.png",
        "pipeline_builder_ru.png",
        "parameters_en.png",
        "parameters_ru.png",
    ]
    for name in required:
        p = shot_dir / name
        if not p.is_file() or p.stat().st_size < 1000:
            err(f"Missing/too-small screenshot: {p.relative_to(ROOT)}")
    # README featured gallery may use ml-a1a2; historical assets remain under v1.1.1.
    allowed_dirs = ("v1.1.1", "ml-a1a2")
    for readme in (ROOT / "README.md", ROOT / "README_RU.md"):
        text = readme.read_text(encoding="utf-8")
        for m in re.finditer(r"!\[[^\]]*\]\((docs/assets/screenshots/[^)]+)\)", text):
            rel = m.group(1)
            if not any(f"/{d}/" in f"/{rel}" or f"screenshots/{d}/" in rel for d in allowed_dirs):
                err(f"{readme.name}: screenshot not under allowed gallery ({'/'.join(allowed_dirs)}): {rel}")
            path = ROOT / rel
            if not path.is_file():
                err(f"{readme.name}: broken screenshot link: {rel}")


def check_contract_audit() -> None:
    md = ROOT / "docs" / "MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.md"
    js = ROOT / "docs" / "MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.json"
    if not md.is_file() or not js.is_file():
        err("Missing MATLAB_METHOD_OUTPUT_CONTRACT_AUDIT.md/.json — run generate_matlab_output_contract_audit.py")
        return
    data = json.loads(js.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    totals = count_contracts()
    for key in ("declared", "diagnostic_figures", "values_only"):
        if summary.get(key) != totals.get(key):
            err(f"Contract audit summary.{key}={summary.get(key)} != count_contracts {totals.get(key)}")
    if summary.get("count_contracts") != totals:
        # tolerate key order
        cc = summary.get("count_contracts") or {}
        if any(cc.get(k) != totals.get(k) for k in totals):
            err("Audit JSON count_contracts block disagrees with live count_contracts()")
    methods = data.get("methods") or []
    if len(methods) != totals["declared"]:
        err(f"Audit lists {len(methods)} methods, expected {totals['declared']}")
    # Runtime verification must not equal all diagnostic figures unless evidence says so
    fig_confirmed = summary.get("figure_outputs_confirmed") or []
    if len(fig_confirmed) >= totals["diagnostic_figures"] and totals["diagnostic_figures"] > 10:
        # Only fail if evidence claims all passed without listing real_matlab for all
        real = summary.get("real_matlab_passed") or []
        if len(real) < totals["diagnostic_figures"]:
            err("Audit claims all figures confirmed without real_matlab_passed for each figure method")
    text = md.read_text(encoding="utf-8")
    if "real_matlab_passed` from metadata alone" not in text and "metadata alone" not in text:
        err("Audit MD must warn against treating metadata as runtime verification")


def check_matlab_guide_ru() -> None:
    text = (ROOT / "docs" / "MATLAB_STUDIO_GUIDE_RU.md").read_text(encoding="utf-8")
    if "Артеfact" in text:
        err("MATLAB_STUDIO_GUIDE_RU still has typo Артеfact")
    # Mixed Latin UX terms that should be localized in prose (identifiers in backticks OK)
    prose = re.sub(r"`[^`]+`", "", text)
    for bad in ("viewer", "batch analysis", "Guided", "Research", "Expert", "provenance", "abstention"):
        # allow English only in code identifiers already stripped; flag leftover prose words
        if re.search(rf"\b{bad}\b", prose):
            err(f"MATLAB_STUDIO_GUIDE_RU still has untranslated term in prose: {bad}")


def check_packaged_qa_doc() -> None:
    path = ROOT / "docs" / "PACKAGED_UI_MANUAL_QA.md"
    if not path.is_file():
        err("Missing docs/PACKAGED_UI_MANUAL_QA.md")
        return
    text = path.read_text(encoding="utf-8")
    for marker in ("1366×768", "125%", "150%", "1920×1080", "SHA-256"):
        if marker not in text and marker.replace("×", "x") not in text:
            # allow ascii x
            if marker.replace("×", "x") not in text.replace("×", "x"):
                err(f"PACKAGED_UI_MANUAL_QA.md missing marker: {marker}")


def main() -> int:
    check_control_reference()
    check_readme_projects()
    check_screenshots()
    check_contract_audit()
    check_matlab_guide_ru()
    check_packaged_qa_doc()
    if ERRORS:
        print("validate_phase3c_docs FAILED:")
        for e in ERRORS:
            print(" -", e)
        return 1
    print("validate_phase3c_docs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
