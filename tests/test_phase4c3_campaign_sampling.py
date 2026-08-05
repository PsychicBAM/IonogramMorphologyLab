"""Phase 4C.3 — deterministic campaign sampling and coverage."""

from __future__ import annotations

from ionogram_morphology_lab.morphology_review_campaign.models import (
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.sampling import (
    apply_sampling,
    build_eligible_pool,
    item_fingerprint,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)


def test_deterministic_sampling_repeatable(tmp_path):
    sources = [
        SourceScopeEntry(f"{0xB001:064x}"[-64:], "s1.mat", "i1", "2014-01", True),
        SourceScopeEntry(f"{0xB002:064x}"[-64:], "s2.mat", "i2", "2014-02", True),
    ]
    windows = [TimeWindow(100, 200, 10, "block")]
    plan = SamplingPlan(method="deterministic_random", seed=99, target_count=5)
    store = MorphologyReviewCampaignStore(tmp_path)
    a = store.preview_sampling(sources=sources, windows=windows, plan=plan)
    b = store.preview_sampling(sources=sources, windows=windows, plan=plan)
    assert a["fingerprints"] == b["fingerprints"]
    assert a["selected_count"] == 5
    assert a["candidate_fields_present"] is False
    assert "accuracy" not in str(a).lower() or "not" in str(a).lower()


def test_source_date_time_coverage():
    sources = [
        SourceScopeEntry(f"{0xC001:064x}"[-64:], "alpha.mat", "ia", "2014-06-01", True),
        SourceScopeEntry(f"{0xC002:064x}"[-64:], "beta.mat", "ib", "2014-07-01", True),
    ]
    windows = [
        TimeWindow(300, 330, 10, "05-07"),
        TimeWindow(600, 620, 10, "10-block"),
    ]
    pool = build_eligible_pool(sources, windows)
    assert len(pool) > 0
    fps = {item_fingerprint(r) for r in pool}
    assert len(fps) == len(pool)
    report = apply_sampling(
        pool, SamplingPlan(method="all_eligible", seed=1, target_count=0)
    )
    assert "alpha.mat" in report["unique_sources"] or any(
        "alpha" in s for s in report["unique_sources"]
    )
    assert report["dates"]
    assert report["time_blocks"]
    # Adjacent-frame warning when step keeps neighbours together
    tight = apply_sampling(
        build_eligible_pool(sources, [TimeWindow(300, 305, 1, "tight")]),
        SamplingPlan(method="all_eligible", seed=1),
    )
    assert tight["adjacent_frame_warnings"]


def test_no_candidate_leakage_in_pool():
    sources = [SourceScopeEntry(f"{0xD001:064x}"[-64:], "x.mat", "ix", "d", True)]
    pool = build_eligible_pool(sources, [TimeWindow(1, 5, 1)])
    for row in pool:
        assert "candidate_state" not in row
        assert "ordinal_strength" not in row
