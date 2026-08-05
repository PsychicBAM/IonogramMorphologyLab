"""Phase 4C.2b.3 — comparison save idempotency and correction."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    project_cohort_comparisons,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import (
    BlindRevealError,
    MorphologyReviewCorpusStore,
)
from ionogram_morphology_lab.morphology_review_corpus.workflow import determine_workflow_stage


def _snap(cid, it, state="frequency_spread_candidate"):
    return CandidateSnapshot(
        cohort_id=cid,
        item_id=it.item_id,
        source_sha256=it.source_sha256,
        frame_index=it.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="x",
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


def _five(tmp_path: Path, cid: str = "idemp") -> MorphologyReviewCorpusStore:
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xAA00 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"a{i}.mat",
                "source_inventory_id": f"ia{i}",
            }
            for i in range(5)
        ],
        cohort_id=cid,
    )
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
    for it in items:
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="idem",
            ),
        )
    return store


def test_repeated_save_no_extra_active_record(tmp_path: Path):
    store = _five(tmp_path)
    it = store.load_items("idemp")[0]
    rev = store.locked_review_for_item("idemp", it.item_id, review_round=1)
    assert rev is not None
    a = store.reveal_and_compare("idemp", it.item_id, review_id=rev.review_id)
    b = store.reveal_and_compare("idemp", it.item_id, review_id=rev.review_id)
    c = store.reveal_and_compare("idemp", it.item_id, review_id=rev.review_id)
    assert a.comparison_id == b.comparison_id == c.comparison_id
    rows = store._read_jsonl(store.path_for("idemp") / "reveal_comparisons.jsonl")
    assert len(rows) == 1
    st = determine_workflow_stage(store, "idemp")
    assert st["counts"]["comparisons"] == 1


def test_correction_requires_reason_and_keeps_count(tmp_path: Path):
    store = _five(tmp_path, "corr")
    it = store.load_items("corr")[0]
    rev = store.locked_review_for_item("corr", it.item_id, review_round=1)
    assert rev is not None
    store.reveal_and_compare("corr", it.item_id, review_id=rev.review_id)
    with pytest.raises(BlindRevealError):
        store.reveal_and_compare(
            "corr",
            it.item_id,
            review_id=rev.review_id,
            comparison_comment="changed note",
            allow_revision=True,
        )
    store.reveal_and_compare(
        "corr",
        it.item_id,
        review_id=rev.review_id,
        comparison_comment="changed note",
        allow_revision=True,
        revision_reason="fix comment",
    )
    rows = store._read_jsonl(store.path_for("corr") / "reveal_comparisons.jsonl")
    assert len(rows) == 2
    proj = project_cohort_comparisons(store, "corr")
    assert proj.current_count == 1
    assert descriptive_summary(store, "corr")["review_completion_progress"]["comparisons"] == 1
    assert rows[-1]["prior_comparison_id"] == rows[0]["comparison_id"]
    assert rows[-1]["revision_reason"] == "fix comment"


def test_five_comparisons_progress_exact(tmp_path: Path):
    store = _five(tmp_path, "all5")
    for it in store.load_items("all5"):
        rev = store.locked_review_for_item("all5", it.item_id, review_round=1)
        assert rev is not None
        store.reveal_and_compare("all5", it.item_id, review_id=rev.review_id)
        store.reveal_and_compare("all5", it.item_id, review_id=rev.review_id)  # noop
    st = determine_workflow_stage(store, "all5")
    sm = descriptive_summary(store, "all5")
    assert st["counts"]["comparisons"] == 5
    assert sm["review_completion_progress"]["comparisons"] == 5
    assert sum(sm["agreement_status_counts"].values()) == 5
    assert sum(sm["candidate_label_distribution_after_reveal"].values()) == 5
    assert st["stage"] == "summary"
