"""Phase 4C.2b — editable revision must not inherit parent reviews/statuses."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _items(n: int = 3) -> list[dict]:
    return [
        {
            "source_sha256": f"{(0xABCDEF01 + i):064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"real_{i}.mat",
            "source_inventory_id": f"inv_{i}",
            "feature_version": "iml2-0.2.0",
            "frame_time": f"10:0{i}:00",
        }
        for i in range(n)
    ]


def _snap(cid: str, it) -> CandidateSnapshot:
    return CandidateSnapshot(
        cohort_id=cid,
        item_id=it.item_id,
        source_sha256=it.source_sha256,
        frame_index=it.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="frozen",
        result_contract_version=2,
        diagnostics_cache_id="n/a",
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def test_child_revision_has_empty_reviews_and_pending_status(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_items(3), sampling_method="manual", cohort_id="parent")
    items = store.load_items("parent")
    store.freeze_cohort("parent", candidate_snapshots=[_snap("parent", it) for it in items])
    parent_bytes = (store.path_for("parent") / "cohort_manifest.json").read_bytes()
    parent_item_ids = {it.item_id for it in items}

    # Parent: several blind reviews + one comparison
    for it in items[:2]:
        store.save_blind_review(
            "parent",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="parent",
                item_id=it.item_id,
                morphology="range_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="parent locked review",
            ),
        )
    # third still pending on parent
    store.save_blind_review(
        "parent",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="parent",
            item_id=items[2].item_id,
            morphology="range_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="complete round for strict policy",
        ),
    )
    r0 = store.locked_review_for_item("parent", items[0].item_id, review_round=1)
    assert r0 is not None
    store.reveal_and_compare(
        "parent",
        items[0].item_id,
        review_id=r0.review_id,
        reviewer_note_codes=["candidate_differs_from_my_assessment"],
        comparison_comment="parent comparison",
    )
    assert store._read_jsonl(store.path_for("parent") / "blind_reviews.jsonl")
    assert store._read_jsonl(store.path_for("parent") / "reveal_comparisons.jsonl")

    child = store.create_editable_revision("parent", reason="owner QA revision integrity")
    # Parent unchanged
    assert (store.path_for("parent") / "cohort_manifest.json").read_bytes() == parent_bytes
    assert store._read_jsonl(store.path_for("parent") / "blind_reviews.jsonl")
    assert store._read_jsonl(store.path_for("parent") / "reveal_comparisons.jsonl")

    # Child JSONLs empty
    assert (store.path_for(child.cohort_id) / "blind_reviews.jsonl").read_text(
        encoding="utf-8"
    ).strip() == ""
    assert (store.path_for(child.cohort_id) / "reveal_comparisons.jsonl").read_text(
        encoding="utf-8"
    ).strip() == ""
    assert (store.path_for(child.cohort_id) / "adjudications.jsonl").read_text(
        encoding="utf-8"
    ).strip() == ""

    child_items = store.load_items(child.cohort_id)
    assert len(child_items) == 3
    assert all(it.item_status == "item_pending" for it in child_items)
    assert parent_item_ids.isdisjoint({it.item_id for it in child_items})
    assert all(it.parent_item_id for it in child_items)

    # Queue-equivalent: no locked reviews
    for it in child_items:
        assert store.locked_review_for_item(child.cohort_id, it.item_id, review_round=1) is None
        assert not store.can_reveal_candidate(child.cohort_id, it.item_id)

    summary = descriptive_summary(store, child.cohort_id)
    assert summary["completed_blind_reviews_round1"] == 0
    assert summary["review_completion_progress"]["comparisons"] == 0

    # Lookups isolated by cohort_id — parent item_id must not resolve on child
    leaked = store.locked_review_for_item(child.cohort_id, items[0].item_id, review_round=1)
    assert leaked is None


def test_repair_revision_integrity(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="parent")
    store.freeze_cohort("parent")
    child = store.create_editable_revision("parent", reason="repair test")
    # Simulate leakage: write a rogue review + completed status with parent item id
    parent_item = store.load_items("parent")[0]
    child_items = store.load_items(child.cohort_id)
    # Force shared id + completed status
    rows = []
    for i, it in enumerate(child_items):
        d = it.to_dict()
        if i == 0:
            d["item_id"] = parent_item.item_id
            d["item_status"] = "blind_review_locked"
        rows.append(d)
    store._rewrite_jsonl(store.path_for(child.cohort_id) / "items.jsonl", rows)
    (store.path_for(child.cohort_id) / "blind_reviews.jsonl").write_text(
        '{"cohort_id":"%s","item_id":"x","review_id":"bad"}\n' % child.cohort_id,
        encoding="utf-8",
    )
    assert store.detect_revision_leakage(child.cohort_id)
    parent_hash = store.load_manifest("parent").manifest_hash
    result = store.repair_revision_integrity(child.cohort_id)
    assert result["repaired"]
    assert store.load_manifest("parent").manifest_hash == parent_hash
    assert (store.path_for(child.cohort_id) / "blind_reviews.jsonl").read_text(
        encoding="utf-8"
    ).strip() == ""
    for it in store.load_items(child.cohort_id):
        assert it.item_status in ("item_pending", "item_unavailable")
        assert it.item_id != parent_item.item_id
