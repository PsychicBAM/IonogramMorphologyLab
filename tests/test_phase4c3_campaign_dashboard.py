"""Phase 4C.3 — campaign dashboard progress and descriptive summary."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.morphology_review_campaign.analytics import (
    campaign_descriptive_summary,
    explain_metrics_unavailable,
)
from ionogram_morphology_lab.morphology_review_campaign.exports import (
    export_campaign_readiness,
)
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)


def _make(store: MorphologyReviewCampaignStore, cid: str = "dash1"):
    return store.create_campaign(
        campaign_id=cid,
        display_name="Dash",
        sources=[
            SourceScopeEntry(f"{0xE001:064x}"[-64:], "a.mat", "ia", "2014", True),
            SourceScopeEntry(f"{0xE002:064x}"[-64:], "b.mat", "ib", "2014", True),
        ],
        windows=[TimeWindow(1, 50, 5, "w")],
        sampling_plan=SamplingPlan(method="deterministic_random", seed=3, target_count=5),
        reviewer_plan=ReviewerPlan(
            first_reviewer_id="r1", first_reviewer_alias="A", second_reviewer_optional=True
        ),
        create_linked_cohort=True,
        freeze_cohort=True,
        candidate_snapshots=None,
    )


def test_progress_uses_unique_current_counts(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    _make(store)
    # Freeze already done; add snapshots + reviews
    cohort = store.primary_first_review_cohort("dash1")
    assert cohort
    items = store.corpus.load_items(cohort)
    # Re-freeze path already frozen — inject snapshots via append if empty
    for it in items:
        store.corpus._append_jsonl(
            store.corpus.path_for(cohort) / "candidate_snapshots.jsonl",
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
            ).with_hash().to_dict(),
        )
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
                rationale="dash",
            ),
        )
    for it in items:
        rev = store.corpus.locked_review_for_item(cohort, it.item_id, review_round=1)
        store.corpus.reveal_and_compare(cohort, it.item_id, review_id=rev.review_id)
        # Idempotent second save
        store.corpus.reveal_and_compare(cohort, it.item_id, review_id=rev.review_id)

    prog = campaign_progress(store, "dash1")
    n = prog["unique_real_items"]
    assert n == 5
    assert prog["first_blind_progress"]["completed"] == 5
    assert prog["comparison_progress"]["completed"] == 5
    assert prog["comparison_progress"]["completed"] <= n
    assert prog["invariants"]["comparisons_le_unique"]
    assert prog["second_reviewer_optional"] is True

    summary = campaign_descriptive_summary(store, "dash1")
    assert summary["completed_comparisons"] == 5
    assert "accuracy" not in summary or summary.get("scientific_claim") == "none"
    assert "f1" not in str(summary.get("kind", "")).lower()
    text = explain_metrics_unavailable("ru")
    assert "f1" in text.lower() or "accuracy" in text.lower()

    exp = export_campaign_readiness(store, "dash1")
    assert Path(exp["md_path"]).is_file()
    md = Path(exp["md_path"]).read_text(encoding="utf-8")
    assert "shadow-only" in md.lower() or "shadow" in md.lower()
    assert "E:\\" not in md and "C:\\" not in md
