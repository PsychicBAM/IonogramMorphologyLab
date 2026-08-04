#!/usr/bin/env python3
"""Capture MainWindow grabs at resolution/scale combinations for PACKAGED_UI_MANUAL_QA evidence."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Prefer native Windows fonts (not offscreen tofu).
os.environ.pop("QT_QPA_PLATFORM", None)
os.environ.pop("IML_FORCE_OFFSCREEN", None)

from PySide6.QtWidgets import QApplication  # noqa: E402

from ionogram_morphology_lab.projects.model import create_project  # noqa: E402
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library  # noqa: E402
from ionogram_morphology_lab.ui.main_window import MainWindow  # noqa: E402

OUT = ROOT / "docs" / "assets" / "screenshots" / "v1.1.1" / "manual_qa"
CASES = [
    (1366, 768, 1.0, "1366x768_100"),
    (1366, 768, 1.25, "1366x768_125"),
    (1366, 768, 1.5, "1366x768_150"),
    (1920, 1080, 1.0, "1920x1080_100"),
]
PAGES = ("projects", "matlab", "pipeline", "parameters", "help")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    work = ROOT / "workspaces" / "_manual_qa_v111"
    work.mkdir(parents=True, exist_ok=True)
    mats = write_synthetic_mat_library(work / "synthetic")
    app = QApplication.instance() or QApplication([])
    results = []
    for w, h, scale, tag in CASES:
        os.environ["QT_SCALE_FACTOR"] = str(scale)
        for lang in ("en", "ru"):
            win = MainWindow(language=lang)
            win.settings.set("general", "workspace_dir", str(work / "projects"))
            win.settings.set("general", "first_launch_done", True)
            win.settings.set("general", "show_onboarding", False)
            win.settings.set("ux", "interface_mode", "expert")
            win.settings.save()
            win.session.project = create_project(
                f"QA_{tag}",
                language=lang,
                workspace_parent=str(work / "projects"),
                profile_id="kfu_cyclone_2013_2014",
            )
            win.session.set_active_mat(mats[0])
            win.session.load_profile("kfu_cyclone_2013_2014")
            win.resize(w, h)
            win.show()
            win.retranslate()
            QApplication.processEvents()
            for key in PAGES:
                win._navigate_key(key)
                QApplication.processEvents()
                path = OUT / f"{tag}_{key}_{lang}.png"
                win.grab().save(str(path), "PNG")
                results.append(str(path.relative_to(ROOT)).replace("\\", "/"))
            win.close()
    os.environ.pop("QT_SCALE_FACTOR", None)
    (OUT / "CAPTURE_INDEX.md").write_text(
        "# Manual QA captures\n\n" + "\n".join(f"- `{r}`" for r in results) + "\n",
        encoding="utf-8",
    )
    print("wrote", len(results), "captures under", OUT)
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
