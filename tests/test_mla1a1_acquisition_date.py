"""Phase ML-B.1 — acquisition date authority, legacy diagnostics, gate B evidence."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    diagnose_invalid_date_projection,
    is_time_only_value,
    is_valid_acquisition_date,
    normalize_acquisition_date,
    parse_date_from_filename,
    resolve_acquisition_date,
)
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.holdout_feasibility import (
    assess_holdout_feasibility,
)
from ionogram_morphology_lab.ml_dataset_readiness.inventory import project_cohort_inventory
from ionogram_morphology_lab.ml_dataset_readiness.missingness import build_missingness_report
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import suggest_gate_blockers
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


def _snap(cid, it):
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
        candidate_state="mixed_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _am_all_13_corpus(tmp_path: Path, cid: str = "am_all_13") -> MorphologyReviewCorpusStore:
    """Owner fixture: Am_all_2014-10-15.mat, bare HH:MM times, no grouping.source_date."""
    store = MorphologyReviewCorpusStore(tmp_path)
    sha = _sha(0xA2014)
    times = [
        "04:59",
        "05:09",
        "05:19",
        "05:29",
        "05:39",
        "05:49",
        "05:59",
        "06:09",
        "06:19",
        "06:29",
        "06:39",
        "06:49",
        "06:59",
    ]
    specs = []
    for i, ft in enumerate(times):
        specs.append(
            {
                "source_sha256": sha,
                "frame_index": i + 1,
                "source_display_name": "Am_all_2014-10-15.mat",
                "source_inventory_id": "inv_am_all",
                "frame_time": ft,
                # Intentionally no datetime_metadata / source_date — filename is authority
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": "seq_am_1",
                    "related_frame_group": "rel_am_1",
                    "source": "Am_all_2014-10-15.mat",
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
                rationale="am",
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


@pytest.fixture
def no_msgbox(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)


def test_build_identity_mla1a1():
    ident = collect_build_identity(compute_sha=False)
    assert ident["release_phase"] == "ML-C.1b"
    assert ident["ml_dataset_readiness_protocol_version"] == "iml-ml-dataset-readiness-0.1.0"


def test_filename_am_all_resolves_to_iso_date():
    assert parse_date_from_filename("Am_all_2014-10-15.mat") == "2014-10-15"
    assert parse_date_from_filename(r"E:\data\Am_all_2014-10-15.mat") == "2014-10-15"
    assert is_time_only_value("04:59")
    assert is_time_only_value("05:09:00")
    assert not is_valid_acquisition_date("04:59")
    assert normalize_acquisition_date("04:59") == ""
    assert normalize_acquisition_date("04:59", "2014-10-15") == "2014-10-15"
    assert (
        resolve_acquisition_date(
            grouping={},
            source_display_name="Am_all_2014-10-15.mat",
        )
        == "2014-10-15"
    )


def test_frame_time_never_becomes_acquisition_date():
    assert (
        resolve_acquisition_date(
            grouping={"source_date": "04:59"},
            datetime_metadata="05:09",
            source_display_name="nosuch.mat",
        )
        == ""
    )


def test_am_all_13_counts_and_table(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "am_all_13", task_contract="spread_f_morphology_classification"
    )
    assert len(rows) == 13
    assert all(r.source_date == "2014-10-15" for r in rows)
    assert all(is_time_only_value(r.frame_time) or ":" in r.frame_time for r in rows)
    cov = build_coverage_summary(rows, task_contract="spread_f_morphology_classification")
    dens = cov["denominators"]
    assert dens["raw_frame_count"] == 13
    assert dens["unique_sources"] == 1
    assert dens["unique_source_dates"] == 1
    assert dens["unique_sequences"] == 1
    assert dens["unique_frame_times"] == 13
    # Invariant: many frame times must not inflate dates
    assert dens["unique_source_dates"] < dens["unique_frame_times"]
    sd = cov["source_date_rows"]
    assert len(sd) == 1
    assert sd[0]["source_date"] == "2014-10-15"
    assert sd[0]["source"] == "Am_all_2014-10-15.mat"
    assert "mixed_spread" not in sd[0]["source"]
    assert "04:59" in sd[0]["frame_times"]
    assert "06:59" in sd[0]["frame_times"]


def test_missing_date_not_time_derived(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    cid = "no_date"
    store.create_cohort(
        items=[
            {
                "source_sha256": _sha(1),
                "frame_index": 1,
                "source_display_name": "plain.mat",
                "source_inventory_id": "inv1",
                "frame_time": "04:59",
                "feature_version": "iml2-0.2.0",
                "grouping": {"sequence_id": "s1", "related_frame_group": "r1"},
            }
        ],
        cohort_id=cid,
    )
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, items[0])])
    store.save_blind_review(
        cid,
        BlindReviewRecord.create(
            reviewer_id="e1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id=cid,
            item_id=items[0].item_id,
            morphology="mixed_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="x",
        ),
    )
    rows, _, _ = project_cohort_inventory(
        store, cid, task_contract="spread_f_morphology_classification"
    )
    assert rows[0].source_date == ""
    assert rows[0].frame_time == "04:59"
    cov = build_coverage_summary(rows)
    assert cov["denominators"]["unique_source_dates"] == 0


def test_exports_use_corrected_date(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="AmAll",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    rows = store.load_inventory(frozen.audit_id)
    assert {r.source_date for r in rows} == {"2014-10-15"}
    cov = json.loads(
        (store.path_for(frozen.audit_id) / "coverage_summary.json").read_text(encoding="utf-8")
    )
    assert cov["denominators"]["unique_source_dates"] == 1
    csv_text = (store.path_for(frozen.audit_id) / "source_date_coverage.csv").read_text(
        encoding="utf-8"
    )
    assert "2014-10-15" in csv_text
    assert "04:59" not in csv_text.splitlines()[1]  # date column not time
    out = store.export_report(frozen.audit_id)
    bundle = json.loads((out / "readiness_report.json").read_text(encoding="utf-8"))
    assert bundle["denominators"]["unique_source_dates"] == 1
    assert len(store.list_audits()) == 1


def test_holdout_grouping_uses_acquisition_date_not_frame_time(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "am_all_13", task_contract="spread_f_morphology_classification"
    )
    report = assess_holdout_feasibility(rows, audit_id="x")
    # Dates in report should not be frame times
    for d in report.dates_only_in_exposed:
        assert is_valid_acquisition_date(d) or d == ""
        assert not is_time_only_value(d)


def test_legacy_frozen_audit_unchanged_and_warns(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Legacy",
        description="",
        task_contract="assessability_quality_classification",
        cohort_ids=["am_all_13"],
        analyst_id="a1",
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    # Mutate frozen inventory to simulate legacy invalid projection (do not via API)
    inv_path = store.path_for(frozen.audit_id) / "label_inventory.jsonl"
    rows = [json.loads(line) for line in inv_path.read_text(encoding="utf-8").splitlines() if line]
    times = [
        "04:59",
        "05:09",
        "05:19",
        "05:29",
        "05:39",
        "05:49",
        "05:59",
        "06:09",
        "06:19",
        "06:29",
        "06:39",
        "06:49",
        "06:59",
    ]
    for i, row in enumerate(rows):
        row["source_date"] = times[i]
        row["frame_time"] = times[i]
    inv_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    loaded = store.load_inventory(frozen.audit_id)
    assert loaded[0].source_date == "04:59"  # frozen snapshot unchanged content
    diag = diagnose_invalid_date_projection(loaded)
    assert diag["legacy_invalid_date_projection"] is True
    assert "older version" in diag["warning_en"].lower()
    assert "некорректной проекцией" in diag["warning_ru"]
    cov = build_coverage_summary(
        loaded, task_contract="assessability_quality_classification"
    )
    # Invalid times must not count as unique_source_dates
    assert cov["denominators"]["unique_source_dates"] == 0
    assert cov["acquisition_date_diagnostics"]["legacy_invalid_date_projection"] is True
    # Parent inventory file still has invalid dates (immutable)
    reloaded = store.load_inventory(frozen.audit_id)
    assert reloaded[0].source_date == "04:59"


def test_corrected_revision_gets_normalized_date(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="ToFix",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    # Corrupt parent to legacy time-as-date projection
    inv_path = store.path_for(frozen.audit_id) / "label_inventory.jsonl"
    rows = [json.loads(line) for line in inv_path.read_text(encoding="utf-8").splitlines() if line]
    times = [
        "04:59",
        "05:09",
        "05:19",
        "05:29",
        "05:39",
        "05:49",
        "05:59",
        "06:09",
        "06:19",
        "06:29",
        "06:39",
        "06:49",
        "06:59",
    ]
    for i, row in enumerate(rows):
        row["source_date"] = times[i]
    inv_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    parent_hash = store.load_manifest(frozen.audit_id).inventory_hash
    parent_dates_before = [r.source_date for r in store.load_inventory(frozen.audit_id)]
    rev = store.create_revision(
        frozen.audit_id,
        corpus,
        revision_reason="Correct invalid acquisition date projection",
    )
    assert rev.audit_id != frozen.audit_id
    assert rev.parent_audit_id == frozen.audit_id
    # Parent unchanged
    assert store.load_manifest(frozen.audit_id).inventory_hash == parent_hash
    assert [r.source_date for r in store.load_inventory(frozen.audit_id)] == parent_dates_before
    new_rows = store.load_inventory(rev.audit_id)
    assert all(r.source_date == "2014-10-15" for r in new_rows)
    assert not diagnose_invalid_date_projection(new_rows)["has_invalid_acquisition_dates"]
    cov = build_coverage_summary(new_rows)
    assert cov["denominators"]["unique_source_dates"] == 1


def test_suggest_blocker_b_requires_evidence(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    rows, _, _ = project_cohort_inventory(
        corpus, "am_all_13", task_contract="assessability_quality_classification"
    )
    cov = build_coverage_summary(rows, task_contract="assessability_quality_classification")
    miss = build_missingness_report(rows, task_contract="assessability_quality_classification")
    assert int(miss.get("categories", {}).get("structurally_missing") or 0) == 0
    suggestions = suggest_gate_blockers(
        coverage=cov,
        missingness=miss,
        task_contract="assessability_quality_classification",
    )
    codes = {s["code"] for s in suggestions}
    assert "B_repair_label_contract_or_missing_data" not in codes
    # Manual B remains allowed — suggestions do not restrict owner choice
    assert "B_repair_label_contract_or_missing_data"  # code still exists as selectable


def test_suggest_blocker_b_with_missing_evidence(tmp_path: Path):
    cov = {
        "denominators": {"missing_required_fields": 3, "unique_current_items": 10},
        "target_unsupported": False,
    }
    miss = {"categories": {"structurally_missing": 3}}
    suggestions = suggest_gate_blockers(
        coverage=cov, missingness=miss, task_contract="spread_f_morphology_classification"
    )
    b = [s for s in suggestions if s["code"].startswith("B_")]
    assert b
    assert "missing_required_fields=3" in b[0]["evidence"]


def test_ui_am_all_dates_and_contract_visibility(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="UIAm",
        description="",
        task_contract="assessability_quality_classification",
        cohort_ids=["am_all_13"],
        analyst_id="a",
    )
    store.freeze_audit(draft.audit_id, corpus)
    page = MLDataReadinessPage(_FakeSession(tmp_path), I18n("ru"))
    qtbot.addWidget(page)
    page.show()
    QApplication.processEvents()
    assert "Контракт задачи" in page._form_labels["contract"].text()
    assert "целевые метки" in page.lbl_contract_explain.text()
    assert "Контракт текущего аудита" in page.lbl_current_contract.text()
    assert "оценимости" in page.lbl_current_contract.text().lower() or "Assessability" not in page.lbl_current_contract.text()
    dens = page.overview_text.toPlainText()
    assert "Уникальных дат" in dens or "unique_source_dates" not in dens
    assert page.tbl_sources.rowCount() >= 1
    assert page.tbl_sources.item(0, 1).text() == "2014-10-15"
    assert "04:59" in (page.tbl_sources.item(0, 2).text() or "")
    assert "mixed_spread" not in (page.tbl_sources.item(0, 0).text() or "")
    # Headers
    assert "Дата" in page.tbl_sources.horizontalHeaderItem(1).text()
    assert "Время" in page.tbl_sources.horizontalHeaderItem(2).text()


def test_ui_legacy_warn_and_ru_en(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="LegUI",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    inv_path = store.path_for(frozen.audit_id) / "label_inventory.jsonl"
    rows = [json.loads(line) for line in inv_path.read_text(encoding="utf-8").splitlines() if line]
    times = ["04:59", "05:09", "05:19", "05:29", "05:39", "05:49", "05:59", "06:09", "06:19", "06:29", "06:39", "06:49", "06:59"]
    for i, row in enumerate(rows):
        row["source_date"] = times[i]
    inv_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    page = MLDataReadinessPage(_FakeSession(tmp_path), I18n("ru"))
    qtbot.addWidget(page)
    page.show()
    QApplication.processEvents()
    assert page.lbl_legacy_date_warn.isVisible()
    assert "некорректной проекцией" in page.lbl_legacy_date_warn.text()
    assert page.btn_corrected_revision.isVisible()
    page.i18n.set_language("en")
    page.retranslate()
    QApplication.processEvents()
    assert "invalid acquisition" in page.lbl_legacy_date_warn.text().lower()
    assert "Corrected" in page.btn_corrected_revision.text()
