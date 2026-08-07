"""ML-B.1d — collapsible layout, holdout wording consistency, frozen immutability UI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    GATE_F,
    MANIFEST_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_dataset_manifests.display_labels import (
    contract_compact_label,
    gate_compact_label,
    lifecycle_label,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from ionogram_morphology_lab.ui.ml_dataset_manifests_page import MLDatasetManifestsPage
from tests.test_mlb1a_manifest_ux_dates import _build_scenario_b_gate_f
from tests.test_mlb1_dataset_manifests import _freeze_readiness_with_gate


class _I18n:
    def __init__(self, lang: str = "en") -> None:
        self.language = lang
        self._en = json.loads(
            Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8")
        )
        self._ru = json.loads(
            Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8")
        )

    def t(self, key, **kwargs):
        src = self._ru if str(self.language).lower().startswith("ru") else self._en
        text = src.get(key, key)
        try:
            return text.format(**kwargs) if kwargs else text
        except Exception:
            return text

    def set_language(self, lang: str) -> None:
        self.language = lang


class _Sess:
    def __init__(self, root: Path) -> None:
        self.project_path = root
        self.active_project_path = root


def _page(qtbot, root: Path, lang: str = "en") -> MLDatasetManifestsPage:
    page = MLDatasetManifestsPage(_Sess(root), _I18n(lang))
    qtbot.addWidget(page)
    page.show()
    page.on_project_changed()
    QApplication.processEvents()
    return page


def _prepare_frozen_scenario_b(tmp_path: Path) -> tuple[MLDatasetManifestStore, str]:
    rstore, audit_id, _meta = _build_scenario_b_gate_f(tmp_path)
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore,
        audit_id=audit_id,
        title="MLB1C Scenario B",
        seed=42,
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    report = mstore.validate(ms.manifest_set_id)
    assert report.get("integrity_ok", report.get("ok"))
    frozen = mstore.freeze(ms.manifest_set_id)
    assert frozen.lifecycle_state == "frozen"
    return mstore, frozen.manifest_set_id


def test_build_identity_mlb1c():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-B.1d"
    assert info["ml_dataset_manifest_protocol_version"] == MANIFEST_PROTOCOL_VERSION
    assert info["shadow_only"] is True


def test_compact_label_helpers():
    assert gate_compact_label(GATE_F, "en") == "Gate F"
    assert gate_compact_label(GATE_F, "ru") == "Gate F"
    assert "Spread-F" in contract_compact_label(
        "spread_f_morphology_classification", "en"
    )
    assert "Spread-F" in contract_compact_label(
        "spread_f_morphology_classification", "ru"
    )
    assert lifecycle_label("frozen", "ru") == "Заморожен"


def test_panels_default_collapsed_and_toggle(qtbot, tmp_path: Path):
    page = _page(qtbot, tmp_path)
    assert page._context_box.isChecked() is False
    assert page._tech_box.isChecked() is False
    assert page._context_body.isVisible() is False
    assert page._tech_body.isVisible() is False
    assert page._compact_summary.isVisible() is True

    page._context_box.setChecked(True)
    QApplication.processEvents()
    assert page._context_expanded is True
    assert page._context_body.isVisible() is True

    page._tech_box.setChecked(True)
    QApplication.processEvents()
    assert page._tech_expanded is True
    assert page._tech_body.isVisible() is True

    page._context_box.setChecked(False)
    page._tech_box.setChecked(False)
    QApplication.processEvents()
    assert page._context_body.isVisible() is False
    assert page._tech_body.isVisible() is False


def test_compact_status_visible_when_context_collapsed(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    assert page._context_box.isChecked() is False
    text = page._compact_summary.text()
    assert "Frozen" in text
    assert "Gate F" in text
    assert "Spread-F" in text
    assert "9 items" in text or "9" in text
    assert page._compact_summary.isVisible() is True
    # Full disclaimer lives in collapsible body, not the compact line
    assert "accuracy" not in text.lower() or "claim" not in text.lower()


def test_critical_gate_blocker_visible_when_context_collapsed(qtbot, tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="gate_block_ui", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="blocked", seed=1
    )
    page = _page(qtbot, tmp_path)
    page._load_saved(ms.manifest_set_id)
    QApplication.processEvents()
    assert page._context_box.isChecked() is False
    assert page._alert.isVisible() is True
    alert = page._alert.text()
    assert alert
    # Gate-not-F blocker must remain outside the collapsed context panel
    assert "freeze" in alert.lower() or "Gate" in alert or "holdout" in alert.lower()
    assert page._btn_freeze.isEnabled() is False
    assert "Gate F" not in page._compact_summary.text() or "Not ready" in alert


def test_central_tab_gains_space_when_panels_collapse(qtbot, tmp_path: Path):
    page = _page(qtbot, tmp_path)
    page.resize(1600, 900)
    QApplication.processEvents()
    page._context_box.setChecked(True)
    page._tech_box.setChecked(True)
    QApplication.processEvents()
    expanded_h = page._tabs.height()
    page._context_box.setChecked(False)
    page._tech_box.setChecked(False)
    QApplication.processEvents()
    collapsed_h = page._tabs.height()
    assert collapsed_h >= expanded_h


def test_retranslate_preserves_tab_manifest_and_expand(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    page._tabs.setCurrentIndex(2)
    page._context_box.setChecked(True)
    page._tech_box.setChecked(False)
    QApplication.processEvents()
    tab = page._tabs.currentIndex()
    page.i18n.set_language("ru")
    page.retranslate()
    QApplication.processEvents()
    assert page._current_id == mid
    assert page._tabs.currentIndex() == tab
    assert page._context_expanded is True
    assert page._tech_expanded is False
    assert "Контекст манифеста" in page._context_box.title()
    assert "Технические детали" in page._tech_box.title()
    assert "Заморожен" in page._compact_summary.text()
    page.i18n.set_language("en")
    page.retranslate()
    QApplication.processEvents()
    assert "Manifest context" in page._context_box.title()
    assert "Technical Details" in page._tech_box.title()
    assert "Frozen" in page._compact_summary.text()


def test_frozen_holdout_reserved_wording(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    holdout = page._txt_holdout.toPlainText()
    validation = page._txt_validation.toPlainText()
    assert "Holdout reserved" in holdout
    assert "Draft holdout assignment (not reserved)" not in holdout
    assert "Draft holdout assignment (not reserved)" not in validation
    assert "Holdout reserved" in validation


def test_draft_holdout_not_reserved_wording(qtbot, tmp_path: Path):
    rstore, audit_id, _ = _build_scenario_b_gate_f(tmp_path, cohort_id="draft_h")
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="draft", seed=42
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    page = _page(qtbot, tmp_path)
    page._load_saved(ms.manifest_set_id)
    QApplication.processEvents()
    holdout = page._txt_holdout.toPlainText()
    assert "Draft holdout assignment (not reserved)" in holdout
    assert "Holdout reserved:" not in holdout


def test_frozen_missing_lock_fails_closed(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    lock = mstore.path_for(mid) / "holdout_lock.json"
    assert lock.is_file()
    lock.unlink()
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    holdout = page._txt_holdout.toPlainText()
    assert "Integrity warning" in holdout or "integrity" in holdout.lower()
    assert "Draft holdout assignment (not reserved)" not in holdout
    assert "Holdout reserved:" not in holdout
    assert page._alert.isVisible() is True


def test_frozen_controls_disabled_export_ok(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    assert page._title.isEnabled() is False
    assert page._desc.isEnabled() is False
    assert page._seed.isEnabled() is False
    assert page._policy.isEnabled() is False
    assert page._btn_leakage.isEnabled() is False
    assert page._btn_propose.isEnabled() is False
    assert page._btn_validate.isEnabled() is False
    assert page._btn_freeze.isEnabled() is False
    assert page._btn_export.isEnabled() is True
    assert page._btn_refresh.isEnabled() is True


def test_expand_collapse_does_not_mutate_manifest(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    before = (mstore.path_for(mid) / "manifest_set.json").read_text(encoding="utf-8")
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    for _ in range(3):
        page._context_box.setChecked(True)
        page._tech_box.setChecked(True)
        QApplication.processEvents()
        page._context_box.setChecked(False)
        page._tech_box.setChecked(False)
        QApplication.processEvents()
    after = (mstore.path_for(mid) / "manifest_set.json").read_text(encoding="utf-8")
    assert after == before
    assert json.loads(after)["lifecycle_state"] == "frozen"


def test_i18n_keys_for_collapsible_panels():
    en = json.loads(Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads(Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    assert en["manifests.context_panel"]
    assert "Контекст манифеста" in ru["manifests.context_panel"]
    assert "ещё не зарезервировано" in ru["manifests.holdout_draft"]
    assert "элементов=" in ru["manifests.holdout_reserved"]
