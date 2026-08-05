"""Phase 4C.3 — campaign domain creation and cohort links."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.morphology_review_campaign.constants import (
    CAMPAIGN_DESIGNATION_EN,
)
from ionogram_morphology_lab.morphology_review_campaign.integrity import validate_campaign
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)


def _sources() -> list[SourceScopeEntry]:
    return [
        SourceScopeEntry(
            source_sha256=f"{0xAA01:064x}"[-64:],
            source_display_name="day_a.mat",
            source_inventory_id="inv_a",
            date_hint="2014-03-01",
            available=True,
        ),
        SourceScopeEntry(
            source_sha256=f"{0xAA02:064x}"[-64:],
            source_display_name="day_b.mat",
            source_inventory_id="inv_b",
            date_hint="2014-03-02",
            available=True,
        ),
    ]


def test_campaign_creation_and_cohort_link(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    m = store.create_campaign(
        campaign_id="pilot_dom",
        display_name="Pilot Dom",
        description="domain test",
        created_by="owner",
        project_identity=tmp_path.name,
        sources=_sources(),
        windows=[TimeWindow(300, 360, 10, "morning")],
        sampling_plan=SamplingPlan(
            method="deterministic_random", seed=7, target_count=4
        ),
        reviewer_plan=ReviewerPlan(
            first_reviewer_id="r1",
            first_reviewer_alias="Expert A",
            second_reviewer_optional=True,
        ),
        create_linked_cohort=True,
        freeze_cohort=False,
    )
    assert m.campaign_id == "pilot_dom"
    assert m.designation_en == CAMPAIGN_DESIGNATION_EN
    assert m.state in ("ready", "draft")
    assert m.campaign_hash
    assert m.actual_item_count == 4
    links = store.list_cohort_links("pilot_dom")
    assert len(links) == 1
    assert links[0].cohort_role == "first_review"
    assert links[0].manifest_hash
    assert links[0].cohort_id in store.corpus.list_cohorts()
    # Manifest hash reference matches cohort
    cm = store.corpus.load_manifest(links[0].cohort_id)
    assert cm.manifest_hash == links[0].manifest_hash
    report = validate_campaign(store, "pilot_dom")
    assert report["ok"], report["issues"]


def test_optional_second_reviewer_default(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    m = store.create_campaign(
        campaign_id="opt2",
        display_name="Opt",
        sources=_sources()[:1],
        windows=[TimeWindow(1, 20, 5)],
        sampling_plan=SamplingPlan(method="all_eligible", target_count=0),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1", second_reviewer_optional=True),
    )
    assert m.reviewer_plan.get("second_reviewer_optional") is True
    proto = store.load_protocol("opt2")
    assert proto.second_reviewer_optional is True
    assert proto.scientifically_validated is False
    assert proto.candidate_shadow_only is True


def test_delete_campaign_keeps_cohort(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    store.create_campaign(
        campaign_id="delc",
        display_name="Del",
        sources=_sources()[:1],
        windows=[TimeWindow(1, 10, 2)],
        sampling_plan=SamplingPlan(method="all_eligible"),
        create_linked_cohort=True,
    )
    cohort_id = store.primary_first_review_cohort("delc")
    assert cohort_id
    store.delete_campaign("delc")
    assert "delc" not in store.list_campaigns()
    assert cohort_id in store.corpus.list_cohorts()
