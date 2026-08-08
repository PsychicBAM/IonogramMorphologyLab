"""Phase ML-B.1 — localization, audit reload, source/date, contract coverage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.display_labels import (
    RAW_CODES_FORBIDDEN_IN_RU_UI,
    denom_label,
    lifecycle_label,
)
from ionogram_morphology_lab.ml_dataset_readiness.inventory import (
    normalize_acquisition_date,
    project_cohort_inventory,
)
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from ionogram_morphology_lab.ui.ml_data_readiness_page import MLDataReadinessPage


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _snap(cid, it, state="mixed_spread_candidate"):
    return CandidateSnapshot(
        cohort_id=cid,
        item_id=it.item_id,
        source_sha256=it.source_sha256,
        frame_index=it.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="rules0.1.0",
        result_contract_version=2,
        diagnostics_cache_id="n/a",
        candidate_state=state,
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _owner_like_13_frame_corpus(tmp_path: Path, cid: str = "owner_13") -> MorphologyReviewCorpusStore:
    """13 frames, 1 MAT source, 1 acquisition date, times 04:59–06:59, 1 sequence."""
    store = MorphologyReviewCorpusStore(tmp_path)
    sha = _sha(0xABCD13)
    specs = []
    # Mix of ISO datetime and bare clock times (owner QA case)
    times = [
        "2014-03-12T04:59:00Z",
        "2014-03-12T05:09:00Z",
        "2014-03-12T05:19:00Z",
        "2014-03-12T05:29:00Z",
        "2014-03-12T05:39:00Z",
        "2014-03-12T05:49:00Z",
        "2014-03-12T05:59:00Z",
        "2014-03-12T06:09:00Z",
        "2014-03-12T06:19:00Z",
        "2014-03-12T06:29:00Z",
        "2014-03-12T06:39:00Z",
        "2014-03-12T06:49:00Z",
        "2014-03-12T06:59:00Z",
    ]
    morphs = [
        "mixed_spread",
        "mixed_spread",
        "frequency_spread",
        "range_spread",
        "mixed_spread",
        "no_supported_visible_spread",
        "mixed_spread",
        "frequency_spread",
        "mixed_spread",
        "range_spread",
        "mixed_spread",
        "frequency_spread",
        "mixed_spread",
    ]
    for i, ft in enumerate(times):
        specs.append(
            {
                "source_sha256": sha,
                "frame_index": i + 1,
                "source_display_name": "owner_pilot.mat",
                "source_inventory_id": "inv_owner_1",
                "frame_time": ft,
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": "seq_owner_1",
                    "related_frame_group": "rel_owner_1",
                    "source_date": "2014-03-12",
                },
            }
        )
    store.create_cohort(items=specs, cohort_id=cid)
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
    for i, it in enumerate(items):
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology=morphs[i],
                assessability="assessable" if i % 3 else "partially_assessable",
                interference=(
                    ["vertical_interference"] if i % 4 == 0 else ["none_supported"]
                ),
                ambiguity="moderate",
                confidence="high",
                rationale="owner-like",
            ),
        )
    return store


def _time_only_corpus(tmp_path: Path, cid: str = "time_only") -> MorphologyReviewCorpusStore:
    """Frames with bare clock times and explicit source_date — dates must not become times."""
    store = MorphologyReviewCorpusStore(tmp_path)
    sha = _sha(0x710001)

    specs = []
    bare_times = ["04:59", "05:09", "05:19"]
    for i, ft in enumerate(bare_times):
        specs.append(
            {
                "source_sha256": sha,
                "frame_index": i + 1,
                "source_display_name": "time_only.mat",
                "source_inventory_id": "inv_t1",
                "frame_time": ft,
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": "seq_t1",
                    "source_date": "2014-03-12",
                    # no related_frame_group → synthetic
                },
            }
        )
    store.create_cohort(items=specs, cohort_id=cid)
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
    for it in items:
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology="mixed_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="t",
            ),
        )
    return store


class _FakeProject:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root


class _FakeSession:
    def __init__(self, root: Path) -> None:
        self.project = _FakeProject(root)
        self.current_project = self.project
        self.events = SimpleNamespace(project_changed=None)
        self.project_changed = None


def test_build_identity_mla1a():
    ident = collect_build_identity(compute_sha=False)
    assert ident["release_phase"] == "ML-C.1b"
    assert ident["ml_dataset_readiness_protocol_version"] == "iml-ml-dataset-readiness-0.1.0"
    assert ident["disagreement_analysis_protocol_version"] == "iml-disagreement-analysis-0.1.0"


def test_normalize_acquisition_date_rejects_bare_time():
    assert normalize_acquisition_date("04:59") == ""
    assert normalize_acquisition_date("05:09:00") == ""
    assert normalize_acquisition_date("2014-03-12T04:59:00Z") == "2014-03-12"
    assert normalize_acquisition_date("04:59", "2014-03-12") == "2014-03-12"


def test_owner_like_counts_and_source_date_projection(tmp_path: Path):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "owner_13", task_contract="spread_f_morphology_classification"
    )
    assert len(rows) == 13
    cov = build_coverage_summary(rows, task_contract="spread_f_morphology_classification")
    dens = cov["denominators"]
    assert dens["raw_frame_count"] == 13
    assert dens["unique_sources"] == 1
    assert dens["unique_source_dates"] == 1
    assert dens["unique_sequences"] == 1
    # Source/date table: one group count 13; times separate
    sd = cov["source_date_rows"]
    assert len(sd) == 1
    assert sd[0]["label_count"] == 13
    assert sd[0]["source_date"] == "2014-03-12"
    assert "mixed_spread" not in sd[0]["source"]
    assert any("04:59" in t or "T04:59" in t for t in sd[0]["frame_times"])
    # Times must not appear as dates
    assert dens["unique_source_dates"] != 13
    # One sequence → correlation warning, not 13 independent events
    assert cov["correlation_warnings"]["sequence_correlation"] is True
    assert dens["unique_sequences"] < dens["raw_frame_count"]


def test_bare_frame_time_not_used_as_date(tmp_path: Path):
    corpus = _time_only_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "time_only", task_contract="spread_f_morphology_classification"
    )
    assert {r.source_date for r in rows} == {"2014-03-12"}
    assert all(r.related_frame_group_synthetic for r in rows)
    cov = build_coverage_summary(rows, task_contract="spread_f_morphology_classification")
    assert cov["denominators"]["unique_source_dates"] == 1
    assert cov["denominators"]["synthetic_related_frame_groups"] == 3
    assert cov["correlation_warnings"]["synthetic_related_frame_groups"] is True


@pytest.mark.parametrize(
    "contract,kind,must_have,must_not_be_morph_only",
    [
        ("spread_f_morphology_classification", "morphology", "mixed_spread", False),
        ("assessability_quality_classification", "assessability_quality", "assessable", True),
        ("interference_classification", "interference", "vertical_interference", True),
        ("ionogram_parameter_scaling", "parameter_scaling", None, True),
    ],
)
def test_task_contract_specific_target_projection(
    tmp_path: Path, contract, kind, must_have, must_not_be_morph_only
):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(corpus, "owner_13", task_contract=contract)
    cov = build_coverage_summary(rows, task_contract=contract)
    assert cov["target_kind"] == kind
    if contract == "ionogram_parameter_scaling":
        assert cov["target_unsupported"] is True
        assert cov["target_label_counts"] == {}
        assert "mixed_spread" not in (cov.get("target_label_counts") or {})
    else:
        assert must_have in cov["target_label_counts"]
        if must_not_be_morph_only:
            # Morphology must not be the sole/primary target map for B/C
            assert cov["target_kind"] != "morphology"


def test_frozen_audit_restores_own_task_contract(tmp_path: Path):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Assess",
        description="",
        task_contract="assessability_quality_classification",
        cohort_ids=["owner_13"],
        analyst_id="a1",
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    assert frozen.task_contract == "assessability_quality_classification"
    rows = store.load_inventory(frozen.audit_id)
    cov = build_coverage_summary(rows, task_contract=frozen.task_contract)
    assert cov["target_kind"] == "assessability_quality"
    assert "assessable" in cov["target_label_counts"]
    assert "mixed_spread" not in cov["target_label_counts"]


def test_export_does_not_create_audit(tmp_path: Path):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Export",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    n_before = len(store.list_audits())
    out = store.export_report(frozen.audit_id)
    assert out.exists()
    assert len(store.list_audits()) == n_before


def test_candidate_labels_excluded(tmp_path: Path):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "owner_13", task_contract="spread_f_morphology_classification"
    )
    for r in rows:
        assert "_candidate" not in (r.morphology or "")


def test_ru_denom_and_lifecycle_labels():
    assert denom_label("selected_records", "ru") == "Выбрано записей"
    assert denom_label("unique_current_items", "ru") == "Уникальных текущих элементов"
    assert denom_label("development_exposed_items", "ru") == (
        "Элементов, использованных в разработке"
    )
    assert denom_label("untouched_eligible_items", "ru") == (
        "Элементов, допустимых для независимого holdout"
    )
    assert lifecycle_label("gate_recorded", "ru") == "Решение зафиксировано"
    assert lifecycle_label("frozen", "ru") == "Заморожен"


@pytest.fixture
def no_msgbox(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)


def _make_page(qtbot, tmp_path: Path, lang: str = "ru") -> MLDataReadinessPage:
    session = _FakeSession(tmp_path)
    i18n = I18n(lang)
    page = MLDataReadinessPage(session, i18n)
    qtbot.addWidget(page)
    page.show()
    QApplication.processEvents()
    return page


def test_saved_audits_load_on_project_open_without_corpus_selection(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="SavedPilot",
        description="d",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
        analyst_id="a1",
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "ru")
    # No cohort selection required
    assert page.list_cohorts.selectedItems() == []
    assert page.list_saved.count() >= 1
    text = page.list_saved.item(0).text()
    assert "SavedPilot" in text
    assert "Заморожен" in text or "frozen" not in text.lower()
    assert page._audit_id


def test_show_event_reloads_audits(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="ShowEvt",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "en")
    page.list_saved.clear()
    assert page.list_saved.count() == 0
    QApplication.sendEvent(page, QEvent(QEvent.Type.Show))
    QApplication.processEvents()
    assert page.list_saved.count() >= 1


def test_ru_normal_ui_has_no_raw_canonical_codes(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="RU Audit",
        description="описание",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
        analyst_id="аналитик",
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    store.run_holdout_feasibility(frozen.audit_id)
    store.record_gate(
        frozen.audit_id,
        outcome="A_collect_more_expert_labels",
        analyst_id="аналитик",
        analyst_rationale="мало меток",
        blockers=["C_expand_class_source_date_sequence_coverage"],
    )
    page = _make_page(qtbot, tmp_path, "ru")
    # Ensure overview populated
    assert page.overview_text.toPlainText()
    ui = page.normal_ui_text()
    for code in RAW_CODES_FORBIDDEN_IN_RU_UI:
        assert code not in ui, f"raw code {code!r} leaked into RU UI"
    assert "note_en" not in ui
    assert "Выбрано записей" in ui or "Уникальных текущих элементов" in ui
    assert "Решение зафиксировано" in page.list_saved.item(0).text()
    # Technical details may contain raw keys but are excluded from normal_ui_text
    assert "selected_records" in page.tech_text.toPlainText()
    # Sources table: not morphology as source
    src0 = page.tbl_sources.item(0, 0).text() if page.tbl_sources.rowCount() else ""
    assert "mixed_spread" not in src0
    date0 = page.tbl_sources.item(0, 1).text() if page.tbl_sources.rowCount() else ""
    assert date0 == "2014-03-12"
    # Time column separate
    time0 = page.tbl_sources.item(0, 2).text() if page.tbl_sources.rowCount() else ""
    assert "04:59" in time0 or "T04:59" in time0


def test_en_mode_remains_correct(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="EN",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "en")
    ui = page.normal_ui_text()
    assert "Selected records" in ui or "Unique current items" in ui
    assert "Frozen" in page.list_saved.item(0).text()


def test_runtime_ru_en_refresh(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Lang",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "ru")
    assert "Заморожен" in page.list_saved.item(0).text()
    page.i18n.set_language("en")
    page.retranslate()
    QApplication.processEvents()
    assert "Frozen" in page.list_saved.item(0).text()
    page.i18n.set_language("ru")
    page.retranslate()
    assert "Заморожен" in page.list_saved.item(0).text()


def test_ui_export_does_not_create_audit(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="ExpUI",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "en")
    n_before = page.list_saved.count()
    page._audit_id = frozen.audit_id
    page._on_export()
    QApplication.processEvents()
    assert page.list_saved.count() == n_before


def test_ui_contract_b_shows_assessability_not_morphology(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="B",
        description="",
        task_contract="assessability_quality_classification",
        cohort_ids=["owner_13"],
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "en")
    classes = [
        page.tbl_class.item(r, 0).text()
        for r in range(page.tbl_class.rowCount())
        if page.tbl_class.item(r, 0)
    ]
    joined = " | ".join(classes).lower()
    assert "assessable" in joined or "Assessable" in " | ".join(classes)
    # Morphology codes should not dominate as class targets
    assert "mixed_spread" not in joined


def test_ui_contract_d_unsupported(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="D",
        description="",
        task_contract="ionogram_parameter_scaling",
        cohort_ids=["owner_13"],
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "ru")
    cell = page.tbl_class.item(0, 0).text() if page.tbl_class.rowCount() else ""
    assert "Не поддерживается" in cell or "метками" in cell
    assert "mixed_spread" not in cell


def test_safe_reload_no_lingering_worker(qtbot, tmp_path: Path, no_msgbox):
    _owner_like_13_frame_corpus(tmp_path)
    page = _make_page(qtbot, tmp_path, "en")
    page.on_project_changed()
    page.on_project_changed()
    assert page._worker is None
    page.close()
    QApplication.processEvents()
    assert page._worker is None


def test_reopen_restores_audit_lifecycle(qtbot, tmp_path: Path, no_msgbox):
    corpus = _owner_like_13_frame_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Lifecycle",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["owner_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    page = _make_page(qtbot, tmp_path, "ru")
    assert page._audit_id == frozen.audit_id
    # Simulate reopen
    page2 = _make_page(qtbot, tmp_path, "ru")
    assert page2.list_saved.count() >= 1
    assert page2._audit_id == frozen.audit_id
    assert "Заморожен" in page2.list_saved.item(0).text()
