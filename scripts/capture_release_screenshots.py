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
from ionogram_morphology_lab.ui.main_window import NAV_KEYS, MainWindow

OUT = ROOT / "docs" / "assets" / "screenshots"
SCHEMATICS = ROOT / "docs" / "assets" / "schematics"
WORK = ROOT / "workspaces" / "_evidence_qa_v111"


def _configure_fonts(app: QApplication) -> str:
    """Prefer a Unicode-capable UI font so Cyrillic/Latin render (esp. offscreen)."""
    preferred = [
        "Segoe UI",
        "Arial",
        "Noto Sans",
        "DejaVu Sans",
        "Microsoft YaHei UI",
        "Tahoma",
    ]
    available = set(QFontDatabase.families())
    for name in preferred:
        if name in available:
            font = QFont(name, 10)
            app.setFont(font)
            return name
    app.setFont(QFont("Sans Serif", 10))
    return "Sans Serif"

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
    ("expert", "expert_review"),
    ("rules", "rule_builder"),
    ("rule_test", "rule_testing"),
    ("matlab", "matlab_studio"),
    ("compare", "method_comparison"),
    ("pipeline", "pipeline_builder"),
    ("parameters", "parameters"),
    ("settings", "settings"),
    ("help", "help"),
]


def _move_schematics() -> None:
    SCHEMATICS.mkdir(parents=True, exist_ok=True)
    for svg in list(OUT.glob("*.svg")):
        shutil.move(str(svg), str(SCHEMATICS / svg.name))


def _grab(win: MainWindow, key: str, stem: str, lang: str) -> Path:
    keys = [k for k, _ in NAV_KEYS]
    win.nav.setCurrentRow(keys.index(key))
    QApplication.processEvents()
    path = OUT / f"{stem}_{lang}.png"
    win.grab().save(str(path), "PNG")
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    _move_schematics()
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    mats = write_synthetic_mat_library(WORK / "synthetic")
    mat = mats[0]

    # Prefer real Windows platform when available so fonts rasterize correctly.
    if os.name == "nt" and os.environ.get("IML_FORCE_OFFSCREEN", "") != "1":
        os.environ.pop("QT_QPA_PLATFORM", None)
    app = QApplication.instance() or QApplication([])
    font_name = _configure_fonts(app)
    print("font:", font_name, "platform:", app.platformName())
    written: list[str] = []

    for lang in ("ru", "en"):
        win = MainWindow(language=lang)
        # Isolate settings/workspace for evidence (no machine MATLAB path in UI)
        win.settings.set("general", "workspace_dir", str(WORK / "projects"))
        win.settings.set("general", "first_launch_done", True)
        win.settings.set("general", "show_onboarding", False)
        win.settings.set("ux", "interface_mode", "guided")
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

        win.resize(1280, 800)
        win.show()
        win.retranslate()
        win._update_status_bar()
        if hasattr(win, "home_dashboard"):
            win.home_dashboard.refresh()
        QApplication.processEvents()

        for nav_key, stem in REQUIRED:
            # EN: capture required set; RU: capture required set
            p = _grab(win, nav_key, stem, lang)
            written.append(p.name)
            print("wrote", p.relative_to(ROOT))
        win.close()

    (OUT / "CAPTURE_LOG.md").write_text(
        "# Screenshot capture log\n\n"
        f"- UI: live Qt MainWindow\n"
        f"- Platform: `{os.environ.get('QT_QPA_PLATFORM')}`\n"
        "- Data: synthetic teaching MAT only (EvidenceQA workspace)\n"
        "- Private paths / research MAT / MATLAB install path: excluded from settings shown\n"
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
