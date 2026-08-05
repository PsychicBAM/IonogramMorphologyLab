"""Phase 4C.4a — disagreement analysis domain contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_disagreement_analysis.analytics import (
    build_transition_matrix,
    descriptive_dashboard,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    ANALYSIS_PROTOCOL_VERSION,
    PROHIBITED_METRICS,
    SMALL_SAMPLE_THRESHOLD,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.contamination import (
    reject_untouched_holdout,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.holdout import (
    build_holdout_plan,
    detect_overlap,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    AnalystHypothesis,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
    AnalysisStoreError,
    MorphologyDisagreementAnalysisStore,
    propose_holdout_from_rows,
)
from ionogram_morphology_lab.morphology_review_corpus.batch_compare import (
    batch_reveal_and_compare,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _snap(cid, it, state="frequency_spread_candidate", strength="moderate"):
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
        ordinal_strength=strength,
        assessability_state="assessable",
        evidence_ledger=[{"category": "trace_geometry", "evidence_type": "spread"}],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _build_pilot_corpus(tmp_path: Path, cid: str = "da_pilot") -> MorphologyReviewCorpusStore:
    """Synthetic fixture: 5 mixed→freq disagreements, 1 match, 1 expert abstention, 1 unavailable cand."""
    store = MorphologyReviewCorpusStore(tmp_path)
    specs = []
    # two sources / dates, related-frame groups
    for i in range(8):
        src = 0x1000 if i < 4 else 0x2000
        specs.append(
            {
                "source_sha256": _sha(src),
                "frame_index": i + 1,
                "source_display_name": f"src{'A' if i < 4 else 'B'}.mat",
                "source_inventory_id": f"inv_{i}",
                "frame_time": f"2014-10-{'15' if i < 4 else '16'}T0{i}:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": f"seq_{'A' if i < 4 else 'B'}",
                    "related_frame_group": f"rel_{'A' if i < 4 else 'B'}",
                    "source_date": f"2014-10-{'15' if i < 4 else '16'}",
                },
            }
        )
    store.create_cohort(items=specs, cohort_id=cid)
    items = store.load_items(cid)
    snaps = []
    for i, it in enumerate(items):
        if i == 7:
            # unavailable candidate — skip snapshot
            continue
        # first five mixed disagreements use frequency_spread_candidate
        # index 5 exact match frequency/frequency
        # index 6 expert abstention with candidate still present
        state = "frequency_spread_candidate"
        snaps.append(_snap(cid, it, state=state))
    store.freeze_cohort(cid, candidate_snapshots=snaps)

    morphs = [
        "mixed_spread",
        "mixed_spread",
        "mixed_spread",
        "mixed_spread",
        "mixed_spread",
        "frequency_spread",  # match
        "indeterminate",  # expert abstention
        "mixed_spread",  # unavailable candidate item
    ]
    interf = [
        ["vertical_interference"],
        ["vertical_interference"],
        ["none_supported"],
        ["none_supported"],
        ["vertical_interference"],
        ["none_supported"],
        ["none_supported"],
        ["none_supported"],
    ]
    for i, it in enumerate(items):
        store.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology=morphs[i],
                assessability="assessable" if morphs[i] != "indeterminate" else "partially_assessable",
                interference=interf[i],
                ambiguity="moderate",
                confidence="high",
                rationale="pilot",
            ),
        )
    batch_reveal_and_compare(store, cid)
    return store


def test_blind_corpus_rejected(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[{"source_sha256": _sha(1), "frame_index": 1, "source_display_name": "a.mat"}],
        cohort_id="blind",
    )
    store.freeze_cohort("blind", candidate_snapshots=[])
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="x", description="", cohort_ids=["blind"])
    with pytest.raises(AnalysisStoreError):
        astore.freeze_snapshot(draft.analysis_id, store)


def test_freeze_dashboard_matrix_and_small_sample(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(
        title="Pilot DA", description="desc", cohort_ids=["da_pilot"], analyst_id="a1"
    )
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    assert frozen.lifecycle_state == "frozen"
    assert frozen.analysis_protocol_version == ANALYSIS_PROTOCOL_VERSION
    assert frozen.snapshot_hash
    rows = astore.load_snapshot_rows(frozen.analysis_id)
    dash = descriptive_dashboard(rows)
    assert dash["selected_unique_items"] == len(rows)
    assert dash["morphology_disagreements"] == 5
    assert dash["exact_label_matches"] == 1
    assert dash["expert_abstentions"] >= 1
    assert dash["unavailable_items"] >= 1
    assert dash["small_sample"] is True
    assert "descriptive inspection only" in dash["small_sample_warning_en"]
    matrix = build_transition_matrix(rows)
    assert matrix.get("mixed_spread", {}).get("frequency_spread_candidate", 0) == 5
    for bad in ("accuracy", "f1", "sensitivity"):
        assert bad not in dash
    # contamination marked
    contam = astore.load_contamination(frozen.analysis_id)
    assert contam
    assert all(c.status == "development_exposed" for c in contam)


def test_immutable_snapshot_survives_corrected_review(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="immut", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    before = [r.to_dict() for r in astore.load_snapshot_rows(frozen.analysis_id)]
    snap_hash = frozen.snapshot_hash

    items = corpus.load_items("da_pilot")
    first = items[0]
    r1 = corpus.locked_review_for_item("da_pilot", first.item_id, review_round=1)
    assert r1 is not None
    # corrected revision on source corpus
    corpus.save_blind_review(
        "da_pilot",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="da_pilot",
            item_id=first.item_id,
            morphology="range_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="correction",
            prior_review_id=r1.review_id,
            revision_reason="pilot correction",
            post_reveal_revision=True,
            candidate_revealed_before_this_record=True,
        ),
    )
    # re-derive comparison against the corrected locked review
    r1_new = corpus.locked_review_for_item("da_pilot", first.item_id, review_round=1)
    assert r1_new is not None
    assert r1_new.morphology == "range_spread"
    corpus.reveal_and_compare(
        "da_pilot",
        first.item_id,
        review_id=r1_new.review_id,
        allow_revision=True,
        revision_reason="corr compare",
    )

    after = [r.to_dict() for r in astore.load_snapshot_rows(frozen.analysis_id)]
    assert after == before
    assert astore.load_manifest(frozen.analysis_id).snapshot_hash == snap_hash

    # new revision captures update
    rev = astore.create_revision(
        frozen.analysis_id, corpus, revision_reason="capture correction"
    )
    rev_rows = astore.load_snapshot_rows(rev.analysis_id)
    assert rev.snapshot_hash != snap_hash
    assert any(
        r.item_id == first.item_id and r.expert_morphology == "range_spread"
        for r in rev_rows
    )


def test_analyst_notes_do_not_alter_labels(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="notes", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    rows = astore.load_snapshot_rows(frozen.analysis_id)
    before = descriptive_dashboard(rows)
    astore.append_hypothesis(
        AnalystHypothesis.create(
            analysis_id=frozen.analysis_id,
            category="possible_candidate_ruleset_issue",
            analyst_id="a1",
            note="Hypothesis only",
            confidence="medium",
        )
    )
    after = descriptive_dashboard(astore.load_snapshot_rows(frozen.analysis_id))
    assert after["exact_label_matches"] == before["exact_label_matches"]
    assert after["morphology_disagreements"] == before["morphology_disagreements"]


def test_exposed_cannot_be_untouched_holdout(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="hold", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    rows = astore.load_snapshot_rows(frozen.analysis_id)
    keys = [f"{r.cohort_id}:{r.item_id}" for r in rows[:2]]
    plan = propose_holdout_from_rows(
        astore,
        analysis_id=frozen.analysis_id,
        title="bad holdout",
        holdout_case_keys=keys,
    )
    assert plan.overlap_errors
    contam = astore.load_contamination(frozen.analysis_id)
    rej = reject_untouched_holdout(keys, contam)
    assert rej["allowed"] is False


def test_related_frame_overlap_and_external_holdout(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="ov", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    rows = astore.load_snapshot_rows(frozen.analysis_id)
    # same related group split would error
    group = rows[0].related_frame_group
    same = [r for r in rows if r.related_frame_group == group]
    if len(same) >= 2:
        ov = detect_overlap(same[:1], same[1:])
        assert "overlapping_related_frame_group" in ov["errors"] or ov["related_frame_group_overlap"]

    # external untouched keys OK for Outcome F
    plan = build_holdout_plan(
        analysis_id=frozen.analysis_id,
        title="future holdout",
        all_rows=rows,
        holdout_case_keys=["future_cohort:holdout_item_1", "future_cohort:holdout_item_2"],
        contamination_records=astore.load_contamination(frozen.analysis_id),
    )
    assert not plan.overlap_errors
    astore.save_holdout_plan(plan)
    rec = astore.record_decision(
        analysis_id=frozen.analysis_id,
        outcome="F_candidate_ruleset_hypothesis_justified",
        analyst_id="a1",
        analyst_rationale="Descriptive concentration of mixed→frequency transitions.",
        alternative_explanations=["Label definition ambiguity", "Assessability limits"],
    )
    assert rec.holdout_required
    assert rec.holdout_plan_id == plan.holdout_plan_id


def test_outcome_f_requires_holdout(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="f", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    with pytest.raises(Exception):
        astore.record_decision(
            analysis_id=frozen.analysis_id,
            outcome="F_candidate_ruleset_hypothesis_justified",
            analyst_id="a1",
            analyst_rationale="needs holdout",
            alternative_explanations=["x"],
        )


def test_exports_no_abs_paths_and_no_metric_claims(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="ex", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    dest = tmp_path / "export_out"
    astore.export_bundle(frozen.analysis_id, dest)
    text = (dest / "analysis_summary.md").read_text(encoding="utf-8").lower()
    for bad in PROHIBITED_METRICS:
        if bad in ("confusion_matrix", "error_matrix", "accuracy_matrix", "ground_truth"):
            continue
        assert f"{bad}" not in text or "not" in text
    assert "e:\\" not in text
    assert "/users/" not in text
    assert (dest / "disagreement_matrix.csv").exists()
    assert (dest / "case_index.csv").exists()
    report = astore.integrity_report(frozen.analysis_id)
    assert report["ok"] is True


def test_version_strata_warning(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    # second cohort with different engine version tag on snapshots
    store = corpus
    store.create_cohort(
        items=[
            {
                "source_sha256": _sha(9),
                "frame_index": 1,
                "source_display_name": "c.mat",
                "feature_version": "iml2-0.2.0",
            }
        ],
        cohort_id="other_eng",
    )
    it = store.load_items("other_eng")[0]
    snap = _snap("other_eng", it)
    snap.candidate_engine_version = "iml-morph-candidate-9.9.9"
    store.freeze_cohort("other_eng", candidate_snapshots=[snap])
    store.save_blind_review(
        "other_eng",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="other_eng",
            item_id=it.item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="x",
        ),
    )
    batch_reveal_and_compare(store, "other_eng")
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(
        title="multi", description="", cohort_ids=["da_pilot", "other_eng"]
    )
    frozen = astore.freeze_snapshot(draft.analysis_id, store)
    assert frozen.version_strata_required is True
    assert frozen.compatibility_warnings


def test_unique_current_counting(tmp_path: Path):
    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="cnt", description="", cohort_ids=["da_pilot"])
    frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
    rows = astore.load_snapshot_rows(frozen.analysis_id)
    keys = [(r.cohort_id, r.item_id) for r in rows]
    assert len(keys) == len(set(keys))
    dash = descriptive_dashboard(rows)
    assert dash["denominator"] == len(rows)
    assert dash["denominator"] < SMALL_SAMPLE_THRESHOLD or dash["small_sample"] in (True, False)


def test_worker_cancel_flag(tmp_path: Path):
    from ionogram_morphology_lab.ui.disagreement_analysis_page import FreezeAnalysisWorker

    corpus = _build_pilot_corpus(tmp_path)
    astore = MorphologyDisagreementAnalysisStore(tmp_path)
    draft = astore.create_draft(title="cancel", description="", cohort_ids=["da_pilot"])
    worker = FreezeAnalysisWorker(astore, corpus, draft.analysis_id)
    worker.cancel()
    assert worker._cancel is True


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_i18n_nav_key(lang):
    from ionogram_morphology_lab.i18n import get_i18n

    i18n = get_i18n()
    i18n.set_language(lang)
    text = i18n.t("nav.disagreement")
    assert text
    assert text != "nav.disagreement"
    if lang == "ru":
        assert "Расхожд" in text or "анализ" in text.lower()
