"""Phase 4C.3 — Resume Work routing."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.resume import resume_work
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)


def _campaign(store, cid="res1", freeze=True):
    snaps_holder = {}

    def _create():
        # preview first to know items after create
        m = store.create_campaign(
            campaign_id=cid,
            display_name="Resume",
            sources=[
                SourceScopeEntry(f"{0xF001:064x}"[-64:], "r.mat", "ir", "2014", True)
            ],
            windows=[TimeWindow(1, 40, 5)],
            sampling_plan=SamplingPlan(
                method="deterministic_random", seed=11, target_count=3
            ),
            reviewer_plan=ReviewerPlan(
                first_reviewer_id="r1", second_reviewer_optional=True
            ),
            create_linked_cohort=True,
            freeze_cohort=False,
        )
        cohort = store.primary_first_review_cohort(cid)
        items = store.corpus.load_items(cohort)
        snaps = [
            CandidateSnapshot(
                cohort_id=cohort,
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
        ]
        if freeze:
            store.corpus.freeze_cohort(cohort, candidate_snapshots=snaps)
        snaps_holder["cohort"] = cohort
        snaps_holder["items"] = items
        return m

    return _create(), snaps_holder


def test_resume_routes_to_first_blind(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    _campaign(store, "res_blind")
    plan = resume_work(store, "res_blind")
    assert plan["action"] == "first_blind_review"
    assert plan["item_id"]
    assert plan["cohort_id"]
    assert "blind" in plan["message_en"].lower()


def test_resume_routes_to_comparison_after_blinds(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    _, hold = _campaign(store, "res_cmp")
    cohort = hold["cohort"]
    for it in hold["items"]:
        store.corpus.save_blind_review(
            cohort,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cohort,
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="r",
            ),
        )
    plan = resume_work(store, "res_cmp")
    assert plan["action"] == "batch_reveal_compare"
    assert plan["primary_action"] == "batch_reveal_compare"
    assert plan["tab_hint"] == "guided"
    assert "reveal" in plan["message_en"].lower() or "calculat" in plan["message_en"].lower()
    assert "locked" in plan["message_en"].lower() or "not change" in plan["message_en"].lower()


def test_resume_summary_when_complete(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    _, hold = _campaign(store, "res_sum")
    cohort = hold["cohort"]
    for it in hold["items"]:
        store.corpus.save_blind_review(
            cohort,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cohort,
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="r",
            ),
        )
    for it in hold["items"]:
        rev = store.corpus.locked_review_for_item(cohort, it.item_id, review_round=1)
        store.corpus.reveal_and_compare(cohort, it.item_id, review_id=rev.review_id)
    plan = resume_work(store, "res_sum")
    assert plan["action"] == "summary_export"


def test_second_review_only_when_assigned(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    _, hold = _campaign(store, "res_sec")
    cohort = hold["cohort"]
    for it in hold["items"]:
        store.corpus.save_blind_review(
            cohort,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cohort,
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="r",
            ),
        )
    for it in hold["items"]:
        rev = store.corpus.locked_review_for_item(cohort, it.item_id, review_round=1)
        store.corpus.reveal_and_compare(cohort, it.item_id, review_id=rev.review_id)
    # Without assignment → summary
    assert resume_work(store, "res_sec")["action"] == "summary_export"
    # With assignment flag → second review
    plan = resume_work(store, "res_sec", second_review_assigned=True)
    assert plan["action"] == "second_review"
