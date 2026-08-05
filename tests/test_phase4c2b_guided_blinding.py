"""Phase 4C.2b — guided stages and strict cohort blinding."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_review_corpus.constants import (
    REVEAL_PER_ITEM,
    REVEAL_STRICT_COHORT,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.protocol import CohortProtocol
from ionogram_morphology_lab.morphology_review_corpus.store import (
    FrozenCohortError,
    MorphologyReviewCorpusStore,
)
from ionogram_morphology_lab.morphology_review_corpus.workflow import (
    determine_workflow_stage,
    next_unfinished_blind_item,
    normalize_reveal_policy,
)


def _items(n: int = 2) -> list[dict]:
    return [
        {
            "source_sha256": f"{(0xAABBCC00 + i):064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"g{i}.mat",
            "source_inventory_id": f"invg{i}",
        }
        for i in range(n)
    ]


def _snap(cid, it):
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
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _lock(store, cid, item_id):
    return store.save_blind_review(
        cid,
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id=cid,
            item_id=item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="guided test",
        ),
    )


def test_stage_draft_then_blind_then_summary(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_items(2), sampling_method="manual", cohort_id="g1")
    st = determine_workflow_stage(store, "g1")
    assert st["stage"] == "composition"
    assert st["primary_action"] == "freeze_and_start"
    items = store.load_items("g1")
    store.freeze_cohort("g1", candidate_snapshots=[_snap("g1", it) for it in items])
    st = determine_workflow_stage(store, "g1")
    assert st["stage"] == "blind_review"
    assert st["next_item_id"] == next_unfinished_blind_item(store, "g1")
    for it in items:
        _lock(store, "g1", it.item_id)
    st = determine_workflow_stage(store, "g1")
    assert st["stage"] in ("blind_complete", "comparison")
    assert st["guided_step"] == "comparison"


def test_strict_blinding_blocks_early_reveal(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    proto = CohortProtocol(reveal_policy=REVEAL_STRICT_COHORT)
    store.create_cohort(
        items=_items(2), sampling_method="manual", cohort_id="strict", protocol=proto
    )
    items = store.load_items("strict")
    store.freeze_cohort("strict", candidate_snapshots=[_snap("strict", it) for it in items])
    _lock(store, "strict", items[0].item_id)
    assert not store.can_reveal_candidate("strict", items[0].item_id)
    _lock(store, "strict", items[1].item_id)
    assert store.can_reveal_candidate("strict", items[0].item_id)


def test_per_item_reveal_allows_after_one_lock(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    proto = CohortProtocol(reveal_policy=REVEAL_PER_ITEM)
    store.create_cohort(
        items=_items(2), sampling_method="manual", cohort_id="per", protocol=proto
    )
    items = store.load_items("per")
    store.freeze_cohort("per", candidate_snapshots=[_snap("per", it) for it in items])
    _lock(store, "per", items[0].item_id)
    assert store.can_reveal_candidate("per", items[0].item_id)
    assert not store.can_reveal_candidate("per", items[1].item_id)


def test_legacy_after_blind_lock_maps_to_per_item():
    assert normalize_reveal_policy("after_blind_lock") == REVEAL_PER_ITEM
    assert normalize_reveal_policy(REVEAL_STRICT_COHORT) == REVEAL_STRICT_COHORT


def test_reveal_policy_immutable_when_frozen(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_items(1), sampling_method="manual", cohort_id="pol")
    store.freeze_cohort("pol")
    proto = store.load_protocol("pol")
    proto.reveal_policy = REVEAL_PER_ITEM
    with pytest.raises(FrozenCohortError):
        store.update_protocol_draft("pol", proto)
