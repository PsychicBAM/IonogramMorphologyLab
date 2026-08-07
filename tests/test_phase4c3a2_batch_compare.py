"""Phase ML-A.1 — batch reveal + automatic comparison derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_campaign.resume import resume_work
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.morphology_review_corpus.batch_compare import (
    BatchCompareError,
    batch_reveal_and_compare,
    can_batch_reveal_and_compare,
)
from ionogram_morphology_lab.morphology_review_corpus.current_state import (
    project_cohort_comparisons,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import comparison_status
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.morphology_review_corpus.workflow import determine_workflow_stage


def _snap(cid, it, state="frequency_spread_candidate", available=True):
    if not available:
        return None
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


def _five(
    tmp_path: Path,
    cid: str = "b5",
    *,
    lock: bool = True,
    morph: str = "frequency_spread",
    cand_state: str = "frequency_spread_candidate",
    skip_snap_for: set[int] | None = None,
) -> MorphologyReviewCorpusStore:
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{(0xAA10 + i):064x}"[-64:],
                "frame_index": i + 1,
                "source_display_name": f"a{i}.mat",
                "source_inventory_id": f"ia{i}",
            }
            for i in range(5)
        ],
        cohort_id=cid,
    )
    items = store.load_items(cid)
    snaps = []
    skip = skip_snap_for or set()
    for i, it in enumerate(items):
        if i in skip:
            continue
        snaps.append(_snap(cid, it, state=cand_state))
    store.freeze_cohort(cid, candidate_snapshots=snaps)
    if lock:
        for it in items:
            store.save_blind_review(
                cid,
                BlindReviewRecord.create(
                    reviewer_id="r1",
                    reviewer_role="reviewer",
                    review_round=1,
                    cohort_id=cid,
                    item_id=it.item_id,
                    morphology=morph,
                    assessability="assessable" if morph != "not_assessable" else "not_assessable",
                    interference=["none_supported"],
                    ambiguity="low",
                    confidence="high",
                    rationale="batch",
                ),
            )
    return store


def test_batch_blocked_before_blind_complete(tmp_path: Path):
    store = _five(tmp_path, "blk", lock=False)
    ready = can_batch_reveal_and_compare(store, "blk")
    assert ready["allowed"] is False
    assert ready["blocked_reason"] == "blind_round_incomplete"
    with pytest.raises(BatchCompareError):
        batch_reveal_and_compare(store, "blk")


def test_batch_visible_after_blind_complete(tmp_path: Path):
    store = _five(tmp_path, "vis")
    ready = can_batch_reveal_and_compare(store, "vis")
    assert ready["allowed"] is True
    stage = determine_workflow_stage(store, "vis")
    assert stage["primary_action"] == "batch_reveal_compare"


def test_batch_derives_all_and_idempotent(tmp_path: Path):
    store = _five(tmp_path, "all")
    a = batch_reveal_and_compare(store, "all")
    assert a["compared_count"] == 5
    assert a["eligible_count"] == 5
    assert a["open_summary"] is True
    assert a["compared_count"] <= a["eligible_count"]
    b = batch_reveal_and_compare(store, "all")
    assert b["compared_count"] == 5
    assert b["reused_count"] == 5
    assert b["created_count"] == 0
    proj = project_cohort_comparisons(store, "all")
    assert proj.current_count == 5
    assert len(proj.history_rows) == 5


def test_derivation_statuses(tmp_path: Path):
    # exact
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="frequency_spread_candidate",
            candidate_assessability="assessable",
            candidate_available=True,
        )
        == "exact_agreement"
    )
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="range_spread_candidate",
            candidate_assessability="assessable",
            candidate_available=True,
        )
        == "morphology_disagreement"
    )
    assert (
        comparison_status(
            human_morphology="indeterminate",
            human_assessability="assessable",
            candidate_state="frequency_spread_candidate",
            candidate_available=True,
        )
        == "human_abstained"
    )
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="indeterminate_candidate",
            candidate_available=True,
        )
        == "candidate_abstained"
    )
    assert (
        comparison_status(
            human_morphology="not_assessable",
            human_assessability="not_assessable",
            candidate_state="frequency_spread_candidate",
            candidate_available=True,
        )
        == "not_comparable"
    )
    store = _five(tmp_path, "unav", skip_snap_for={2})
    result = batch_reveal_and_compare(store, "unav")
    assert result["compared_count"] == 5
    assert result["unavailable_count"] >= 1
    assert "недоступен" in result["message_ru"] or result["unavailable_count"] >= 1


def test_optional_note_does_not_change_count_or_status(tmp_path: Path):
    store = _five(tmp_path, "note")
    batch_reveal_and_compare(store, "note")
    it = store.load_items("note")[0]
    before = store.current_comparison_for_item("note", it.item_id)
    assert before is not None
    status = before.agreement_status
    after = store.save_post_comparison_note("note", it.item_id, note="optional inspection")
    assert after.agreement_status == status
    proj = project_cohort_comparisons(store, "note")
    assert proj.current_count == 5
    assert len(proj.history_rows) == 6  # one note revision append


def test_per_item_reveal_derives_without_advancing(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import AnalysisProject
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage
    from ionogram_morphology_lab.ui.session import AppSession

    app = QApplication.instance() or QApplication([])
    store = _five(tmp_path / "ui", "pi")
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = AnalysisProject(
        project_id="p",
        name="P",
        language="en",
        root=str(tmp_path / "ui"),
        created_at="2026-01-01T00:00:00+00:00",
        source_paths=[],
    )
    page = ExpertReviewCorpusPage(session, get_i18n("en"))
    page._cohort_id = "pi"
    items = store.load_items("pi")
    page._load_item(items[0].item_id)
    page._reveal_candidate()
    assert page._current_item_id == items[0].item_id  # no auto next
    assert store.current_comparison_for_item("pi", items[0].item_id) is not None
    assert store.current_comparison_for_item("pi", items[1].item_id) is None
    text = page.compare_state_label.text().lower()
    assert "calculat" in text or "сравнен" in text or "agreement" in text or "совпад" in text


def test_batch_confirmation_strings_localized():
    i18n = get_i18n("en")
    i18n.set_language("ru")
    assert "Показать кандидатов" in i18n.t("expert_corpus.batch_reveal_compare")
    assert "не изменятся" in i18n.t("expert_corpus.batch_confirm")
    assert i18n.t("expert_corpus.batch_confirm_yes") == "Показать и рассчитать"
    assert "no_sources_selected" not in i18n.t("expert_corpus.batch_confirm")
    i18n.set_language("en")
    assert "Reveal Candidates" in i18n.t("expert_corpus.batch_reveal_compare")
    assert "will not change" in i18n.t("expert_corpus.batch_confirm").lower()


def test_campaign_resume_routes_to_batch(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    m = store.create_campaign(
        campaign_id="res_batch",
        display_name="Resume batch",
        sources=[SourceScopeEntry(f"{0xF101:064x}"[-64:], "r.mat", "ir", "2014", True)],
        windows=[TimeWindow(1, 40, 5)],
        sampling_plan=SamplingPlan(method="deterministic_random", seed=3, target_count=3),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1", second_reviewer_optional=True),
        create_linked_cohort=True,
        freeze_cohort=False,
        skip_inventory_validation=True,
    )
    cohort = store.primary_first_review_cohort("res_batch")
    items = store.corpus.load_items(cohort)
    snaps = [_snap(cohort, it) for it in items]
    store.corpus.freeze_cohort(cohort, candidate_snapshots=snaps)
    for it in items:
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
    plan = resume_work(store, "res_batch")
    assert plan["action"] == "batch_reveal_compare"
    assert plan["tab_hint"] == "guided"


def test_strict_blinding_before_batch(tmp_path: Path):
    store = _five(tmp_path, "strict", lock=False)
    # Lock all but one
    items = store.load_items("strict")
    for it in items[:-1]:
        store.save_blind_review(
            "strict",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="strict",
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="partial",
            ),
        )
    assert can_batch_reveal_and_compare(store, "strict")["allowed"] is False
    assert store.can_reveal_candidate("strict", items[0].item_id) is False


def test_build_identity_4c3a2():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity

    ident = collect_build_identity()
    assert ident["release_phase"] == "ML-B.1d"
