"""ML-B.1d — freeze-status consistency and human-readable Coverage presentation."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ionogram_morphology_lab.ml_dataset_manifests.constants import MANIFEST_PROTOCOL_VERSION
from ionogram_morphology_lab.ml_dataset_manifests.display_labels import (
    COVERAGE_RAW_KEYS_FORBIDDEN_IN_UI,
    contamination_label,
    coverage_field_label,
    short_source_id,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from ionogram_morphology_lab.ui.ml_dataset_manifests_page import MLDatasetManifestsPage
from tests.test_mlb1a_manifest_ux_dates import _build_scenario_b_gate_f
from tests.test_mlb1_dataset_manifests import _freeze_readiness_with_gate
from tests.test_mlb1c_layout_holdout_ui import _I18n, _Sess, _prepare_frozen_scenario_b


def _page(qtbot, root: Path, lang: str = "en") -> MLDatasetManifestsPage:
    page = MLDatasetManifestsPage(_Sess(root), _I18n(lang))
    qtbot.addWidget(page)
    page.show()
    page.on_project_changed()
    QApplication.processEvents()
    return page


def test_build_identity_mlb1d():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-B.1d"
    assert info["ml_dataset_manifest_protocol_version"] == MANIFEST_PROTOCOL_VERSION


def test_coverage_label_helpers():
    assert coverage_field_label("unique_items", "en") == "Items"
    assert coverage_field_label("unique_items", "ru") == "Элементов"
    assert coverage_field_label("atomic_groups", "ru") == "Атомарных групп"
    assert coverage_field_label("acquisition_dates", "ru") == "Дат съёмки"
    assert "разработк" in contamination_label("development_exposed", "ru").lower()
    assert "кандидат" in contamination_label("untouched_candidate", "ru").lower()
    sha = "00000000000000000000000000000000000000000000000000000000c2111111"
    assert short_source_id(sha) == "c211…1111"
    assert len(short_source_id(sha)) < len(sha)


def test_frozen_input_audit_never_says_run_validate(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    text = page._txt_input.toPlainText()
    assert "run Validate" not in text
    assert "выполните Проверку" not in text
    assert "already frozen" in text.lower() or "No further freeze" in text
    assert "(none yet — run Validate)" not in text


def test_draft_shows_validation_pending_status(qtbot, tmp_path: Path):
    rstore, audit_id, _ = _build_scenario_b_gate_f(tmp_path, cohort_id="draft_status")
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="draft", seed=42
    )
    page = _page(qtbot, tmp_path)
    page._load_saved(ms.manifest_set_id)
    QApplication.processEvents()
    text = page._txt_input.toPlainText()
    assert "Validation has not been completed." in text
    assert "already frozen" not in text.lower()


def test_validated_shows_eligible_to_freeze(qtbot, tmp_path: Path):
    rstore, audit_id, _ = _build_scenario_b_gate_f(tmp_path, cohort_id="val_status")
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="val", seed=42
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    report = mstore.validate(ms.manifest_set_id)
    assert report.get("ok")
    assert mstore.load_manifest_set(ms.manifest_set_id).lifecycle_state == "validated"
    page = _page(qtbot, tmp_path)
    page._load_saved(ms.manifest_set_id)
    QApplication.processEvents()
    text = page._txt_input.toPlainText()
    assert "eligible for freeze" in text.lower()
    assert "run Validate" not in text
    assert "already frozen" not in text.lower()


def test_blocked_manifest_shows_localized_blockers(qtbot, tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="blocked_status", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="blocked", seed=1
    )
    page = _page(qtbot, tmp_path)
    page._load_saved(ms.manifest_set_id)
    QApplication.processEvents()
    text = page._txt_input.toPlainText()
    assert "Freeze blockers" in text or "blocker" in text.lower()
    assert "already frozen" not in text.lower()
    # Should show a real blocker, not the draft-only pending message alone
    assert "Validation has not been completed." not in text or "Gate" in text


def test_coverage_human_readable_no_raw_keys(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    cov = page._txt_coverage.toPlainText()
    assert "Development" in cov or "Train" in cov
    assert "Items:" in cov
    assert "Atomic groups:" in cov
    assert "Sequences:" in cov
    assert "Acquisition dates:" in cov
    assert "Sources:" in cov
    assert "Target classes:" in cov or "Target class" in cov
    for key in COVERAGE_RAW_KEYS_FORBIDDEN_IN_UI:
        # raw key must not appear as a label like "unique_items:"
        assert f"{key}:" not in cov
        assert f"{key} =" not in cov
    # full SHA-256 (64 hex) must not be primary visible text
    import re

    assert not re.search(r"\b[0-9a-fA-F]{64}\b", cov)
    # shortened form present
    assert "…" in cov or "..." in cov


def test_full_sha_remains_in_technical_details(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    tech = page._tech.toPlainText()
    cov_path = mstore.path_for(mid) / "group_coverage.json"
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    sources = (cov.get("item_level") or {}).get("development", {}).get("sources") or []
    assert sources
    assert any(sha in tech for sha in sources)
    assert "group_coverage.json" in tech or "unique_items" in tech


def test_coverage_counts_match_scientific_payload(qtbot, tmp_path: Path):
    mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    cov = json.loads((mstore.path_for(mid) / "group_coverage.json").read_text(encoding="utf-8"))
    text = page._txt_coverage.toPlainText()
    for role, label in (
        ("train", "Train"),
        ("development", "Development"),
        ("untouched_holdout", "Untouched holdout"),
    ):
        payload = cov["item_level"][role]
        assert label in text
        assert f"Items: {payload['unique_items']}" in text
        assert f"Atomic groups: {payload['atomic_groups']}" in text
        assert f"Sequences: {len(payload['sequences'])}" in text
        assert f"Acquisition dates: {len(payload['acquisition_dates'])}" in text
        assert f"Sources: {len(payload['sources'])}" in text


def test_coverage_ru_labels_and_live_retranslate(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    page.i18n.set_language("ru")
    page.retranslate()
    QApplication.processEvents()
    cov = page._txt_coverage.toPlainText()
    assert "Элементов:" in cov
    assert "Атомарных групп:" in cov
    assert "Дат съёмки:" in cov
    assert "Источников:" in cov
    assert "unique_items:" not in cov
    input_txt = page._txt_input.toPlainText()
    assert "уже заморожен" in input_txt.lower() or "Повторная заморозка" in input_txt
    assert "выполните Проверку" not in input_txt
    page.i18n.set_language("en")
    page.retranslate()
    QApplication.processEvents()
    assert "Items:" in page._txt_coverage.toPlainText()
    assert "already frozen" in page._txt_input.toPlainText().lower()


def test_frozen_holdout_structured_reserved(qtbot, tmp_path: Path):
    _mstore, mid = _prepare_frozen_scenario_b(tmp_path)
    page = _page(qtbot, tmp_path)
    page._load_saved(mid)
    QApplication.processEvents()
    holdout = page._txt_holdout.toPlainText()
    assert "Holdout reserved" in holdout
    assert "Items: 3" in holdout
    assert "Atomic groups: 2" in holdout
    assert "Reference labels: sealed" in holdout
    assert "Unlock in ML-B: unavailable" in holdout
    assert "Draft holdout assignment (not reserved)" not in holdout
    assert "Draft holdout assignment (not reserved)" not in page._txt_validation.toPlainText()


def test_i18n_freeze_status_keys_present():
    en = json.loads(Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads(Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    for key in (
        "manifests.freeze_status_draft",
        "manifests.freeze_status_validated",
        "manifests.freeze_status_frozen",
        "manifests.holdout_reserved_title",
        "manifests.holdout_ref_labels_sealed",
        "manifests.holdout_unlock_unavailable",
    ):
        assert en[key]
        assert ru[key]
    assert "Проверка ещё не выполнена" in ru["manifests.freeze_status_draft"]
    assert "уже заморожен" in ru["manifests.freeze_status_frozen"]
