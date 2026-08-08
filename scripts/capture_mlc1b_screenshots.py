#!/usr/bin/env python3
"""Capture sanitized ML-C.1b Offline ML Baselines screenshots (synthetic QA only)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# Prefer native Windows platform so Segoe UI / Cyrillic glyphs render in PNGs.
# Offscreen builds often produce tofu boxes for README galleries.
if sys.platform.startswith("win"):
    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QMenu

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_offline_baselines.constants import BASELINE_MAJORITY
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.source_resolve import build_index_from_directory
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.ui.ml_offline_baselines_page import MLOfflineBaselinesPage

OUT = ROOT / "docs" / "assets" / "screenshots" / "ml-c1b"
QA = ROOT / "workspaces" / "MLC1_Offline_Baselines_QA_8a22c20228f2"
# Corrected new experiments (never historical `m` artifacts)
MAJORITY_ID = "mlc_21af3cb4c78e"
CENTROID_ID = "mlc_d448ea6f8bb4"
SIZE = (1600, 900)


class _Sess:
    def __init__(self, root: Path) -> None:
        self.project_path = root
        self.active_project_path = root


def _configure_fonts(app: QApplication) -> str:
    available = set(QFontDatabase.families())
    for name in ("Segoe UI", "Arial", "Noto Sans", "Tahoma", "Microsoft YaHei UI"):
        if name in available:
            font = QFont(name, 10)
            app.setFont(font)
            return name
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    return f"Segoe UI (forced; available={len(available)})"


def _grab(page: MLOfflineBaselinesPage, stem: str, lang: str) -> Path:
    QApplication.processEvents()
    path = OUT / f"{stem}_{lang}.png"
    page.grab().save(str(path), "PNG")
    return path


def _grab_menu(page: MLOfflineBaselinesPage, menu: QMenu, stem: str, lang: str) -> Path:
    QApplication.processEvents()
    menu.popup(page.mapToGlobal(QPoint(40, 80)))
    QApplication.processEvents()
    path = OUT / f"{stem}_{lang}.png"
    # Capture page with open menu overlay when possible; also grab menu widget
    page.grab().save(str(path), "PNG")
    menu.hide()
    QApplication.processEvents()
    return path


def _select(page: MLOfflineBaselinesPage, experiment_id: str) -> None:
    page._refresh_experiments(prefer=experiment_id)
    page._load(experiment_id)
    QApplication.processEvents()


def _set_lang(page: MLOfflineBaselinesPage, i18n: I18n, lang: str) -> None:
    i18n.set_language(lang)
    page.i18n = i18n
    page.retranslate()
    QApplication.processEvents()


def main() -> int:
    if not QA.is_dir():
        print("ERROR: synthetic QA workspace missing:", QA, file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    font_name = _configure_fonts(app)
    print("font", font_name, "platform", os.environ.get("QT_QPA_PLATFORM"))

    manifests = MLDatasetManifestStore(QA)
    frozen = [m for m in manifests.list_manifest_sets() if m.lifecycle_state == "frozen"]
    if not frozen:
        print("ERROR: no frozen manifest", file=sys.stderr)
        return 1
    mid = frozen[0].manifest_set_id
    store = OfflineBaselineStore(QA)
    index = build_index_from_directory(QA)

    # Ensure a fresh draft + validated draft exist for lifecycle shots
    draft = store.create_draft(
        ExperimentConfig(
            "ML-C.1b gallery draft",
            "gallery_qa",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=17,
            description="SYNTHETIC QA DATA / NOT RESEARCH IONOGRAMS",
        )
    )
    validated = store.create_draft(
        ExperimentConfig(
            "ML-C.1b gallery validated",
            "gallery_qa",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=17,
            description="SYNTHETIC QA DATA / NOT RESEARCH IONOGRAMS",
        )
    )
    assert store.validate(validated.experiment_id, manifests, index).state == "validated"

    i18n = I18n()
    page = MLOfflineBaselinesPage(_Sess(QA), i18n)
    page.resize(*SIZE)
    page.show()
    page.on_project_changed()
    QApplication.processEvents()

    written: list[str] = []
    for lang in ("en", "ru"):
        _set_lang(page, i18n, lang)

        # 1 Overview / Setup on completed Majority (corrected)
        _select(page, MAJORITY_ID)
        page._tabs.setCurrentIndex(0)
        written.append(_grab(page, "baselines_overview", lang).name)

        # 2 New draft with Validate + disabled Run
        _select(page, draft.experiment_id)
        page._tabs.setCurrentIndex(0)
        written.append(_grab(page, "draft_validate_disabled_run", lang).name)

        # 3 Validated with enabled Run
        _select(page, validated.experiment_id)
        page._tabs.setCurrentIndex(0)
        written.append(_grab(page, "validated_enabled_run", lang).name)

        # 4 Dataset / holdout SEALED (completed majority)
        _select(page, MAJORITY_ID)
        page._tabs.setCurrentIndex(1)
        written.append(_grab(page, "dataset_holdout_sealed", lang).name)

        # 5 Features
        page._tabs.setCurrentIndex(2)
        written.append(_grab(page, "features", lang).name)

        # 6 Baselines
        page._tabs.setCurrentIndex(3)
        written.append(_grab(page, "baselines", lang).name)

        # 7 Development Evaluation (Majority — valid labels)
        page._tabs.setCurrentIndex(5)
        written.append(_grab(page, "development_evaluation", lang).name)

        # 8 Error Analysis (Majority)
        page._tabs.setCurrentIndex(6)
        written.append(_grab(page, "error_analysis", lang).name)

        # 9 Completed Experiment Summary (Nearest Centroid also OK; prefer Majority summary)
        page._tabs.setCurrentIndex(7)
        written.append(_grab(page, "completed_summary", lang).name)

        # Also capture centroid development evaluation as optional alternate (overwrite not needed)
        _select(page, CENTROID_ID)
        page._tabs.setCurrentIndex(5)
        written.append(_grab(page, "development_evaluation_centroid", lang).name)

        # 10 View menu
        _select(page, MAJORITY_ID)
        page._tabs.setCurrentIndex(0)
        written.append(_grab_menu(page, page._view.menu(), "view_menu", lang).name)

        # 11 More menu
        written.append(_grab_menu(page, page._more.menu(), "more_menu", lang).name)

    log = [
        "# ML-C.1b README screenshot capture log",
        "",
        "- Version dir: `ml-c1b`",
        "- Build Identity: `ML-C.1b`",
        "- UI: live Qt `MLOfflineBaselinesPage` from ML-C.1b source matching accepted packaged EXE",
        "- Accepted EXE SHA-256: `1BA1E89E7B51C32992D7C3D00B807D4854EE2135DF5F25729CBA6322BDC3C484`",
        "- Size: 1600×900",
        "- Data: synthetic QA project `MLC1_Offline_Baselines_QA_8a22c20228f2` (NOT RESEARCH IONOGRAMS)",
        "- Experiments: corrected Majority `mlc_21af3cb4c78e`, Nearest Centroid `mlc_d448ea6f8bb4`",
        "- Historical malformed `m` experiments: **not** shown",
        "- Private paths / research MAT / credentials: excluded",
        f"- Count: **{len(list(OUT.glob('*.png')))}** PNG",
        "",
        "## Files",
        "",
    ]
    for path in sorted(OUT.glob("*.png")):
        log.append(f"- `{path.name}`")
    log.append("")
    log.append("Historical `ml-b1d/` and `ml-a1a2/` galleries were **not** overwritten.")
    log.append("")
    (OUT / "CAPTURE_LOG.md").write_text("\n".join(log), encoding="utf-8")
    print("wrote", len(list(OUT.glob("*.png"))), "png under", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
