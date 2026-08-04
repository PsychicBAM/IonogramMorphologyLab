#!/usr/bin/env python3
"""Capture clean PNG screenshots from the live Qt UI using synthetic data only."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.main_window import MainWindow

VERSION = "v1.1.1"
OUT = ROOT / "docs" / "assets" / "screenshots" / VERSION
LEGACY = ROOT / "docs" / "assets" / "screenshots"
SCHEMATICS = ROOT / "docs" / "assets" / "schematics"
WORK = ROOT / "workspaces" / "_evidence_qa_v111"


def _configure_fonts(app: QApplication) -> str:
    preferred = [
        "Segoe UI",
        "Arial",
        "Noto Sans",
        "DejaVu Sans",
        "Microsoft YaHei UI",
        "Tahoma",
        "Consolas",
    ]
    available = set(QFontDatabase.families())
    for name in preferred:
        if name in available:
            font = QFont(name, 10)
            app.setFont(font)
            return name
    # Offscreen/minimal font databases may report no families; force a Windows UI face
    # so Cyrillic labels do not render as tofu boxes in captured PNGs.
    forced = "Segoe UI"
    font = QFont(forced, 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    return f"{forced} (forced; available={len(available)})"


REQUIRED = [
    ("home", "home"),
    ("projects", "project_creation"),
    ("import", "mat_import"),
    ("audit", "data_audit"),
    ("profile", "instrument_profile"),
    ("viewer", "ionogram_viewer"),
    ("sequences", "contact_sheet"),
    ("batch", "batch_analysis"),
    ("results", "results"),
    ("parameters", "parameters"),
    ("expert", "expert_review"),
    ("reports", "reports"),
    ("atlas", "reference_atlas"),
    ("science", "scientific_basis"),
    ("rules", "rule_builder"),
    ("rule_test", "rule_testing"),
    ("matlab", "matlab_studio"),
    ("compare", "method_comparison"),
    ("pipeline", "pipeline_builder"),
    ("models", "model_lab"),
    ("settings", "settings"),
    ("help", "help"),
]


def _move_schematics() -> None:
    SCHEMATICS.mkdir(parents=True, exist_ok=True)
    for svg in list(LEGACY.glob("*.svg")):
        shutil.move(str(svg), str(SCHEMATICS / svg.name))


def _grab(win: MainWindow, key: str, stem: str, lang: str) -> Path:
    win._navigate_key(key)
    QApplication.processEvents()
    path = OUT / f"{stem}_{lang}.png"
    win.grab().save(str(path), "PNG")
    legacy = LEGACY / f"{stem}_{lang}.png"
    shutil.copy2(path, legacy)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LEGACY.mkdir(parents=True, exist_ok=True)
    _move_schematics()
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    mats = write_synthetic_mat_library(WORK / "synthetic")
    mat = mats[0]

    if os.name == "nt" and os.environ.get("IML_FORCE_OFFSCREEN", "") != "1":
        os.environ.pop("QT_QPA_PLATFORM", None)
    app = QApplication.instance() or QApplication([])
    font_name = _configure_fonts(app)
    print("font:", font_name, "platform:", app.platformName())
    written: list[str] = []

    for lang in ("ru", "en"):
        win = MainWindow(language=lang)
        win.settings.set("general", "workspace_dir", str(WORK / "projects"))
        win.settings.set("general", "first_launch_done", True)
        win.settings.set("general", "show_onboarding", False)
        win.settings.set("ux", "interface_mode", "expert")
        win.settings.set("performance", "cache_location", str(WORK / "cache"))
        win.settings.set("matlab", "matlab_executable", "")
        win.settings.set("matlab", "active_backend", "auto")
        win.settings.save()

        win.session.project = create_project(
            "EvidenceQA_Synthetic",
            language=lang,
            workspace_parent=str(WORK / "projects"),
            profile_id="kfu_cyclone_2013_2014",
        )
        win.session.set_active_mat(mat)
        win.session.load_profile("kfu_cyclone_2013_2014")
        try:
            store = win.session.ensure_store()
            store.ensure_ready()
            win.session.current_frame = 1
        except Exception as exc:  # noqa: BLE001
            print("cache note:", exc)

        win.resize(1366, 768)
        win.show()
        win.retranslate()
        win._apply_ux_mode()
        win._update_status_bar()
        if hasattr(win, "home_dashboard"):
            win.home_dashboard.refresh()
        QApplication.processEvents()

        for nav_key, stem in REQUIRED:
            p = _grab(win, nav_key, stem, lang)
            written.append(str(p.relative_to(ROOT)).replace("\\", "/"))
            print("wrote", p.relative_to(ROOT))
        win.close()

    (OUT / "CAPTURE_LOG.md").write_text(
        "# Screenshot capture log\n\n"
        f"- Version dir: `{VERSION}`\n"
        f"- UI: live Qt MainWindow\n"
        f"- Platform: `{app.platformName()}`\n"
        "- Data: synthetic teaching MAT only (EvidenceQA workspace)\n"
        "- Private paths / research MAT / MATLAB install path: excluded\n"
        f"- Count: {len(written)}\n\n"
        + "\n".join(f"- `{n}`" for n in written)
        + "\n",
        encoding="utf-8",
    )
    print("done", len(written))
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
