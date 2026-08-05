"""Phase 4C.2b.3 — current-state counts and duplicate repair."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ionogram_morphology_lab.morphology_review_corpus.analytics import descriptive_summary
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    count_consistency,
    project_comparisons,
    repair_comparison_derived_state,
)
from ionogram_morphology_lab.morphology_review_corpus.integrity import validate_cohort
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.morphology_review_corpus.workflow import determine_workflow_stage


def _setup(tmp_path: Path, cid: str = "rep") -> MorphologyReviewCorpusStore:
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xBB00 + i):064x}"[-64:],
                "frame_index": i,
                "source_display_name": f"b{i}.mat",
                "source_inventory_id": f"ib{i}",
            }
            for i in range(5)
        ],
        cohort_id=cid,
    )
    items = store.load_items(cid)
    store.freeze_cohort(
        cid,
        candidate_snapshots=[
            CandidateSnapshot(
                cohort_id=cid,
                item_id=it.item_id,
                source_sha256=it.source_sha256,
                frame_index=it.frame_index,
                candidate_engine_version="iml-morph-candidate-0.1.1",
                ruleset_id="iml-morph-candidate-rules",
                ruleset_hash="x",
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
            for it in items
        ],
    )
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
                rationale="repair",
            ),
        )
    return store


def _legacy_dup_row(base: dict, *, conflict: bool = False) -> dict:
    row = dict(base)
    row["comparison_id"] = str(uuid4())
    row["record_hash"] = "f" * 64
    if conflict:
        row["agreement_status"] = "morphology_disagreement"
        row["human_morphology"] = "range_spread"
    return row


def test_legacy_ten_rows_project_to_five(tmp_path: Path):
    store = _setup(tmp_path, "ten")
    items = store.load_items("ten")
    # Create one real comparison per item via API
    for it in items:
        rev = store.locked_review_for_item("ten", it.item_id, review_round=1)
        assert rev is not None
        store.reveal_and_compare("ten", it.item_id, review_id=rev.review_id)
    # Inject identical legacy duplicates (simulating old non-idempotent saves)
    path = store.path_for("ten") / "reveal_comparisons.jsonl"
    rows = store._read_jsonl(path)
    assert len(rows) == 5
    extras = [_legacy_dup_row(r) for r in rows]
    # One conflicting duplicate on item 0
    extras.append(_legacy_dup_row(rows[0], conflict=True))
    for row in extras:
        store._append_jsonl(path, row)
    assert len(store._read_jsonl(path)) == 11

    proj = project_comparisons(store._read_jsonl(path), eligible_item_ids=[it.item_id for it in items])
    assert proj.current_count == 5
    assert len(proj.identical_duplicate_ids) >= 1

    cons = count_consistency(store, "ten")
    assert cons["comparisons_current"] == 5
    assert cons["comparisons_history"] == 11
    assert cons["comparisons_current"] <= cons["eligible_count"]

    st = determine_workflow_stage(store, "ten")
    sm = descriptive_summary(store, "ten")
    assert st["counts"]["comparisons"] == 5
    assert sm["review_completion_progress"]["comparisons"] == 5
    assert sum(sm["agreement_status_counts"].values()) == 5


def test_repair_preserves_history_and_is_idempotent(tmp_path: Path):
    store = _setup(tmp_path, "fix")
    items = store.load_items("fix")
    for it in items:
        rev = store.locked_review_for_item("fix", it.item_id, review_round=1)
        assert rev is not None
        store.reveal_and_compare("fix", it.item_id, review_id=rev.review_id)
    path = store.path_for("fix") / "reveal_comparisons.jsonl"
    for row in list(store._read_jsonl(path)):
        store._append_jsonl(path, _legacy_dup_row(row))
    before_n = len(store._read_jsonl(path))
    dry = repair_comparison_derived_state(store, "fix", dry_run=True)
    assert dry["applied"] is False
    assert dry["current_count"] == 5
    applied = repair_comparison_derived_state(store, "fix", dry_run=False)
    assert applied["applied"] is True
    assert len(store._read_jsonl(path)) == before_n  # history preserved
    assert (store.path_for("fix") / "comparison_current_state.json").is_file()
    again = repair_comparison_derived_state(store, "fix", dry_run=False)
    assert again["current_count"] == 5
    # Manifest frozen untouched
    m = store.load_manifest("fix")
    assert m.frozen
    info: list[str] = []
    errors = validate_cohort(store, "fix", collect_info=info)
    # Current count within bounds — no hard error for identical dups after projection
    assert not any("exceed eligible" in e for e in errors)


def test_second_review_does_not_change_comparison_count(tmp_path: Path):
    store = _setup(tmp_path, "sec")
    items = store.load_items("sec")
    for it in items:
        rev = store.locked_review_for_item("sec", it.item_id, review_round=1)
        assert rev is not None
        store.reveal_and_compare("sec", it.item_id, review_id=rev.review_id)
    it0 = items[0]
    store.save_blind_review(
        "sec",
        BlindReviewRecord.create(
            reviewer_id="r2",
            reviewer_role="second_reviewer",
            review_round=2,
            cohort_id="sec",
            item_id=it0.item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="second",
            post_reveal_revision=True,
            revision_reason="optional second independent review",
            candidate_revealed_before_this_record=True,
        ),
        allow_same_reviewer_second=False,
    )
    sm = descriptive_summary(store, "sec")
    assert sm["review_completion_progress"]["comparisons"] == 5
    assert sm["completed_blind_reviews_round2"] == 1
