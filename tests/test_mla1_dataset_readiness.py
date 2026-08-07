"""Phase ML-A.1 — dataset and label readiness audit contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    ADJACENT_FRAME_WARNING_EN,
    ADJACENT_FRAME_WARNING_RU,
    GATE_OUTCOMES,
    LIMITED_COVERAGE_WARNING_EN,
    NO_CLAIM_STATEMENT_EN,
    PARAMETER_SCALING_UNSUPPORTED_EN,
    PROHIBITED_METRICS,
    READINESS_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_dataset_readiness.contracts import contract_descriptor
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.holdout_feasibility import (
    assess_holdout_feasibility,
)
from ionogram_morphology_lab.ml_dataset_readiness.inventory import dedupe_cohort_references
from ionogram_morphology_lab.ml_dataset_readiness.missingness import build_missingness_report
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import validate_gate_record
from ionogram_morphology_lab.ml_dataset_readiness.store import (
    MLDatasetReadinessStore,
    ReadinessStoreError,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
    MorphologyDisagreementAnalysisStore,
)
from ionogram_morphology_lab.morphology_review_corpus.batch_compare import (
    batch_reveal_and_compare,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    AdjudicationRecord,
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity


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


def _build_readiness_corpus(tmp_path: Path, cid: str = "mla1_pilot") -> MorphologyReviewCorpusStore:
    """Synthetic: multiple classes, dates, groups; second review; arbitration; correction."""
    store = MorphologyReviewCorpusStore(tmp_path)
    specs = []
    # Source A date1 — related group A (4 adjacent frames) — mixed
    for i in range(4):
        specs.append(
            {
                "source_sha256": _sha(0xA100),
                "frame_index": i + 1,
                "source_display_name": "srcA.mat",
                "source_inventory_id": f"inv_a_{i}",
                "frame_time": f"2014-10-15T0{i}:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": "seq_A",
                    "related_frame_group": "rel_A",
                    "source_date": "2014-10-15",
                },
            }
        )
    # Source B date2 — frequency + range + no spread
    morph_plan = [
        ("frequency_spread", "assessable", ["none_supported"]),
        ("range_spread", "assessable", ["none_supported"]),
        ("no_supported_visible_spread", "partially_assessable", ["vertical_interference"]),
        ("indeterminate", "partially_assessable", ["uncertain"]),
    ]
    for i, _ in enumerate(morph_plan):
        specs.append(
            {
                "source_sha256": _sha(0xB200 + i),
                "frame_index": 1,
                "source_display_name": f"srcB{i}.mat",
                "source_inventory_id": f"inv_b_{i}",
                "frame_time": f"2015-01-0{i+1}T12:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": f"seq_B{i}",
                    "related_frame_group": f"rel_B{i}",
                    "source_date": f"2015-01-0{i+1}",
                },
            }
        )
    # Untouched candidate group C — separate date/source (frequency)
    specs.append(
        {
            "source_sha256": _sha(0xC300),
            "frame_index": 1,
            "source_display_name": "srcC.mat",
            "source_inventory_id": "inv_c_0",
            "frame_time": "2016-06-01T08:00:00Z",
            "feature_version": "iml2-0.2.0",
            "grouping": {
                "sequence_id": "seq_C",
                "related_frame_group": "rel_C",
                "source_date": "2016-06-01",
            },
        }
    )
    # Invalid identity fixture — empty sha skipped by create? use placeholder then mark unavailable
    specs.append(
        {
            "source_sha256": _sha(0xD400),
            "frame_index": 1,
            "source_display_name": "srcD.mat",
            "source_inventory_id": "inv_d_0",
            "frame_time": "2016-07-01T08:00:00Z",
            "feature_version": "iml2-0.2.0",
            "item_status": "item_unavailable",
            "grouping": {
                "sequence_id": "seq_D",
                "related_frame_group": "rel_D",
                "source_date": "2016-07-01",
            },
        }
    )

    store.create_cohort(items=specs, cohort_id=cid)
    items = store.load_items(cid)
    snaps = [_snap(cid, it) for it in items if it.item_status != "item_unavailable"]
    # still freeze with available snaps
    store.freeze_cohort(cid, candidate_snapshots=snaps)

    # Label first 4 mixed
    for i in range(4):
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=items[i].item_id,
                morphology="mixed_spread",
                assessability="assessable",
                interference=["vertical_interference"],
                ambiguity="moderate",
                confidence="high",
                rationale="mixed",
            ),
        )
    # Remaining labelled
    for j, (morph, assess, interf) in enumerate(morph_plan):
        idx = 4 + j
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=items[idx].item_id,
                morphology=morph,
                assessability=assess,
                interference=interf,
                ambiguity="moderate",
                confidence="high",
                rationale="label",
            ),
        )
    # Untouched C
    store.save_blind_review(
        cid,
        BlindReviewRecord.create(
            reviewer_id="expert_one",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id=cid,
            item_id=items[8].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="untouched candidate",
        ),
    )
    # Correct first review on item 0
    r0 = store.locked_review_for_item(cid, items[0].item_id, review_round=1)
    assert r0 is not None
    store.save_blind_review(
        cid,
        BlindReviewRecord.create(
            reviewer_id="expert_one",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id=cid,
            item_id=items[0].item_id,
            morphology="mixed_spread",
            assessability="assessable",
            interference=["vertical_interference"],
            ambiguity="high",
            confidence="high",
            rationale="corrected",
            prior_review_id=r0.review_id,
            revision_reason="clarify ambiguity",
        ),
    )
    # Independent second review on item 4 (frequency)
    r1 = store.locked_review_for_item(cid, items[4].item_id, review_round=1)
    assert r1 is not None
    store.save_blind_review(
        cid,
        BlindReviewRecord.create(
            reviewer_id="expert_two",
            reviewer_role="reviewer",
            review_round=2,
            cohort_id=cid,
            item_id=items[4].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="second",
        ),
    )
    r2 = store.locked_review_for_item(cid, items[4].item_id, review_round=2)
    assert r2 is not None
    store.save_adjudication(
        cid,
        AdjudicationRecord(
            adjudication_id="adj_1",
            adjudicator_id="arbiter",
            cohort_id=cid,
            item_id=items[4].item_id,
            input_review_ids=[r1.review_id, r2.review_id],
            adjudicated_morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            rationale="agree frequency",
        ).with_hash(),
    )
    return store


def test_build_identity_mla1():
    ident = collect_build_identity(compute_sha=False)
    assert ident["release_phase"] == "ML-B.1d"
    assert ident.get("scientifically_validated") is False
    assert ident.get("ml_dataset_readiness_protocol_version") == READINESS_PROTOCOL_VERSION
    assert ident.get("disagreement_analysis_protocol_version")


def test_morphology_task_contract_and_freeze(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="MLA1",
        description="pilot",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
        analyst_id="a1",
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    assert frozen.lifecycle_state == "frozen"
    assert frozen.audit_protocol_version == READINESS_PROTOCOL_VERSION
    rows = store.load_inventory(frozen.audit_id)
    assert len(rows) >= 9
    # Corrected review counts once
    assert sum(1 for r in rows if r.item_id == corpus.load_items("mla1_pilot")[0].item_id) == 1
    assert any(r.first_review_corrected for r in rows)
    # Candidate labels excluded
    for r in rows:
        assert "_candidate" not in (r.morphology or "")
        assert not any("_candidate" in f for f in (r.interference or []))
    cov = build_coverage_summary(rows)
    assert "mixed_spread" in cov["morphology_label_counts"]
    assert "range_spread" in cov["morphology_label_counts"]
    # absent class: indeterminate is present; secondary/multiple may be absent from taxonomy
    assert cov["denominators"]["unique_related_frame_groups"] < cov["denominators"]["unique_current_items"]
    assert ADJACENT_FRAME_WARNING_EN in (cov["correlation_warnings"]["en"] or [])
    assert ADJACENT_FRAME_WARNING_RU in (cov["correlation_warnings"]["ru"] or [])


def test_parameter_scaling_unsupported(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="param",
        description="",
        task_contract="ionogram_parameter_scaling",
        cohort_ids=["mla1_pilot"],
    )
    assert PARAMETER_SCALING_UNSUPPORTED_EN in draft.contract_status_note
    desc = contract_descriptor("ionogram_parameter_scaling")
    assert desc["supports_parameter_scaling"] is False
    frozen = store.freeze_audit(draft.audit_id, corpus)
    miss = build_missingness_report(
        store.load_inventory(frozen.audit_id),
        task_contract="ionogram_parameter_scaling",
    )
    assert miss["categories"]["not_applicable"] >= 1


def test_assessability_and_interference_contracts(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    for contract in (
        "assessability_quality_classification",
        "interference_classification",
    ):
        draft = store.create_draft(
            title=contract,
            description="",
            task_contract=contract,
            cohort_ids=["mla1_pilot"],
        )
        frozen = store.freeze_audit(draft.audit_id, corpus)
        assert frozen.task_contract == contract
        rows = store.load_inventory(frozen.audit_id)
        assert rows


def test_dedupe_cohort_references():
    unique, acct = dedupe_cohort_references(["a", "b", "a", "a"])
    assert unique == ["a", "b"]
    assert acct["duplicate_references_removed"] == 2


def test_corrected_not_second_reviewer_and_independence(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="ind",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    cov = build_coverage_summary(store.load_inventory(frozen.audit_id))
    ri = cov["reviewer_independence"]
    assert ri["independent_second_review_count"] >= 1
    assert ri["arbitration_count"] >= 1
    assert ri["corrected_first_reviews"] >= 1
    # candidate is not a reviewer — no candidate alias in reviewer keys
    assert "candidate" not in str(ri).lower() or "not a reviewer" in ri["note_en"].lower()


def test_missingness_categories_separate(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="miss",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    miss = build_missingness_report(
        store.load_inventory(frozen.audit_id),
        task_contract="spread_f_morphology_classification",
    )
    for cat in (
        "structurally_missing",
        "not_applicable",
        "expert_abstained",
        "unavailable_data",
        "corrupted_identity",
    ):
        assert cat in miss["categories"]


def test_development_exposure_from_disagreement(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    # Freeze disagreement analysis on same cohort after reveal → development_exposed
    batch_reveal_and_compare(corpus, "mla1_pilot")
    dstore = MorphologyDisagreementAnalysisStore(tmp_path)
    d = dstore.create_draft(title="da", description="", cohort_ids=["mla1_pilot"])
    dstore.freeze_snapshot(d.analysis_id, corpus)

    rstore = MLDatasetReadinessStore(tmp_path)
    draft = rstore.create_draft(
        title="exp",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = rstore.freeze_audit(draft.audit_id, corpus)
    rows = rstore.load_inventory(frozen.audit_id)
    exposed = [r for r in rows if r.contamination_state == "development_exposed"]
    assert exposed
    # Group propagation: adjacent frames in rel_A unsuitable
    rel_a = [r for r in rows if r.related_frame_group == "rel_A"]
    assert rel_a
    assert all(not r.eligible_untouched_holdout for r in rel_a)


def test_holdout_feasibility_no_split(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="hf",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    rows = store.load_inventory(frozen.audit_id)
    report = assess_holdout_feasibility(rows, audit_id=frozen.audit_id)
    assert report.assessment_kind == "holdout_feasibility_assessment"
    assert "holdout dataset" not in report.note_en.lower() or "not a holdout dataset" in report.note_en.lower()
    # No group appears in both lists as split of same members inconsistently without error
    assert not (set(report.untouched_eligible_groups) & set(report.development_exposed_groups) - set(report.overlapping_groups))
    # Class gap detection present
    assert isinstance(report.classes_absent_from_untouched, list)


def test_gate_f_policy(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="gate",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
        analyst_id="a1",
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    # Typical pilot → E or C
    rec = store.record_gate(
        frozen.audit_id,
        outcome="E_untouched_holdout_not_currently_feasible",
        analyst_id="a1",
        analyst_rationale="Pilot coverage too narrow for untouched holdout.",
        blockers=["C_expand_class_source_date_sequence_coverage"],
    )
    assert rec.authorizes_training is False
    assert rec.authorizes_mlb_manifest_planning_only is False
    assert not validate_gate_record(rec)
    # F without rationale / without feasible holdout fails
    with pytest.raises(ReadinessStoreError):
        store.record_gate(
            frozen.audit_id,
            outcome="F_ready_for_mlb_manifest_planning_only",
            analyst_id="a1",
            analyst_rationale="",
        )


def test_frozen_immutability_and_revision(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="immut",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    before = [r.to_dict() for r in store.load_inventory(frozen.audit_id)]
    inv_hash = frozen.inventory_hash
    items = corpus.load_items("mla1_pilot")
    r1 = corpus.locked_review_for_item("mla1_pilot", items[1].item_id, review_round=1)
    corpus.save_blind_review(
        "mla1_pilot",
        BlindReviewRecord.create(
            reviewer_id="expert_one",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="mla1_pilot",
            item_id=items[1].item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="post-freeze correction",
            prior_review_id=r1.review_id,
            revision_reason="change",
        ),
    )
    after = [r.to_dict() for r in store.load_inventory(frozen.audit_id)]
    assert after == before
    assert store.load_manifest(frozen.audit_id).inventory_hash == inv_hash
    rev = store.create_revision(
        frozen.audit_id,
        corpus,
        revision_reason="see correction",
        analyst_id="a1",
    )
    rev_rows = store.load_inventory(rev.audit_id)
    changed = [r for r in rev_rows if r.item_id == items[1].item_id][0]
    assert changed.morphology == "frequency_spread"


def test_exports_no_abs_no_metrics(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="exp",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    store.record_gate(
        frozen.audit_id,
        outcome="A_collect_more_expert_labels",
        analyst_id="a1",
        analyst_rationale="Need more labels.",
    )
    out = store.export_report(frozen.audit_id)
    md = (out / "readiness_report.md").read_text(encoding="utf-8")
    assert NO_CLAIM_STATEMENT_EN.split(".")[0] in md or "descriptive" in md.lower()
    assert "E:\\" not in md
    assert "/Users/" not in md
    low = md.lower()
    for bad in PROHIBITED_METRICS:
        assert f"{bad}=" not in low
    assert "accuracy:" not in low


def test_worker_cancel_and_teardown(tmp_path: Path, qtbot):
    from ionogram_morphology_lab.ui.ml_data_readiness_page import FreezeReadinessWorker

    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="w",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )

    class Session:
        current_project = type("P", (), {"root": tmp_path})()

    class I18n:
        lang = "en"

        def t(self, k):
            return k

    # Cancel before work completes by pre-cancelling
    worker = FreezeReadinessWorker(
        store,
        corpus,
        mode=FreezeReadinessWorker.MODE_FREEZE,
        audit_id=draft.audit_id,
    )
    worker.cancel()
    worker.start()
    worker.wait(10000)
    assert not worker.isRunning()
    worker.deleteLater()


def test_limited_coverage_warning_present(tmp_path: Path):
    corpus = _build_readiness_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="lim",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["mla1_pilot"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    cov = build_coverage_summary(store.load_inventory(frozen.audit_id))
    # Small pilot may trigger limited coverage depending on unique dates/sources
    warns = cov["correlation_warnings"]["en"]
    assert ADJACENT_FRAME_WARNING_EN in warns or LIMITED_COVERAGE_WARNING_EN in warns


def test_gate_outcomes_defined():
    assert "F_ready_for_mlb_manifest_planning_only" in GATE_OUTCOMES
    assert len(GATE_OUTCOMES) == 6
