"""Phase 4C.2 — Expert Morphology Review Corpus domain, blinding, exports."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from ionogram_morphology_lab.morphology_review_corpus.analytics import (
    descriptive_summary,
    inter_reviewer_descriptive,
    refuse_unsupported_metrics,
)
from ionogram_morphology_lab.morphology_review_corpus.blinding import (
    may_show_candidate,
    queue_columns,
    strip_candidate_fields,
)
from ionogram_morphology_lab.morphology_review_corpus.exports import export_cohort
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash
from ionogram_morphology_lab.morphology_review_corpus.integrity import (
    validate_cohort,
    validate_no_production_ruleengine_wiring,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    HUMAN_MORPHOLOGY_CODES,
    comparison_status,
    morphology_label,
    rationale_required,
    validate_human_morphology,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    AdjudicationRecord,
    BlindReviewRecord,
    CandidateSnapshot,
    ReviewerIdentity,
)
from ionogram_morphology_lab.morphology_review_corpus.sampling import (
    import_manifest,
    random_sample,
    stratified_sample,
)
from ionogram_morphology_lab.morphology_review_corpus.status import status_label
from ionogram_morphology_lab.morphology_review_corpus.store import (
    BlindRevealError,
    FrozenCohortError,
    MorphologyReviewCorpusStore,
)


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _pool(n: int = 10) -> list[dict]:
    return [
        {
            "source_sha256": _sha(i + 1),
            "frame_index": i % 4,
            "source_display_name": f"s{i}.mat",
            "source_inventory_id": f"inv{i}",
            "feature_version": "iml2-0.2.0",
            "candidate_state": (
                "frequency_spread_candidate" if i % 2 == 0 else "range_spread_candidate"
            ),
        }
        for i in range(n)
    ]


def _snap(cohort_id: str, item) -> CandidateSnapshot:
    return CandidateSnapshot(
        cohort_id=cohort_id,
        item_id=item.item_id,
        source_sha256=item.source_sha256,
        frame_index=item.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="ruleshash",
        result_contract_version=2,
        diagnostics_cache_id="diag",
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[{"id": "e1"}],
        result_hash="a" * 64,
        ledger_hash="b" * 64,
        generated_or_cached="cached",
    )


def test_canonical_labels_and_axes():
    assert "frequency_spread" in HUMAN_MORPHOLOGY_CODES
    assert "frequency_spread_candidate" not in HUMAN_MORPHOLOGY_CODES
    validate_human_morphology("mixed_spread")
    with pytest.raises(ValueError):
        validate_human_morphology("frequency_spread_candidate")
    assert morphology_label("range_spread", "ru")
    assert rationale_required(morphology="indeterminate")
    assert rationale_required(morphology="not_assessable")
    assert rationale_required(morphology="frequency_spread", interference_flags=["other"])
    assert status_label("blind_review_locked", "en")
    assert status_label("cohort_frozen", "ru")
    with pytest.raises(ValueError):
        status_label("not_a_real_status", "en")


def test_deterministic_random_and_stratified():
    pool = _pool(12)
    a = random_sample(pool, count=5, seed=7)
    b = random_sample(pool, count=5, seed=7)
    assert [x["source_sha256"] for x in a] == [x["source_sha256"] for x in b]
    c = random_sample(pool, count=5, seed=8)
    assert [x["source_sha256"] for x in a] != [x["source_sha256"] for x in c]
    s = stratified_sample(pool, strata_key="candidate_state", per_stratum=2, seed=1)
    strata = {x["sampling_stratum"] for x in s}
    assert any("frequency" in t for t in strata)


def test_import_manifest_unavailable(tmp_path: Path):
    man = tmp_path / "m.csv"
    man.write_text(
        "source_sha256,frame_index,source_display_name\n"
        f"{_sha(1)},0,ok.mat\n"
        "notasha,1,bad.mat\n",
        encoding="utf-8",
    )
    rows = import_manifest(man)
    store = MorphologyReviewCorpusStore(tmp_path / "proj")
    m = store.create_from_import_manifest(
        man, cohort_id="imp1", sha_exists=lambda s: s == _sha(1)
    )
    items = store.load_items(m.cohort_id)
    assert any(it.item_status == "item_unavailable" for it in items)
    # Original entry retained via unavailable reason
    bad = next(it for it in items if it.item_status == "item_unavailable")
    assert bad.unavailable_reason


def test_freeze_and_reject_mutation(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    m = store.create_from_sampling(
        pool=_pool(6), mode="random", count=3, seed=1, cohort_id="c1", sha_exists=lambda s: True
    )
    assert not m.frozen
    items = store.load_items("c1")
    store.freeze_cohort("c1", candidate_snapshots=[_snap("c1", it) for it in items])
    m2 = store.load_manifest("c1")
    assert m2.frozen
    with pytest.raises(FrozenCohortError):
        store.replace_items_draft("c1", [])
    with pytest.raises(FrozenCohortError):
        store.update_protocol_draft("c1", store.load_protocol("c1"))


def test_cohort_revision(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(4), mode="manual", cohort_id="parent", sha_exists=lambda s: True
    )
    store.freeze_cohort("parent")
    child = store.revise_cohort("parent", reason="add items for pilot expansion")
    assert child.parent_cohort_id == "parent"
    assert not child.frozen
    assert child.revision_reason


def test_blind_lock_reveal_and_leakage(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(4), mode="random", count=2, seed=3, cohort_id="blind", sha_exists=lambda s: True
    )
    items = store.load_items("blind")
    store.freeze_cohort("blind", candidate_snapshots=[_snap("blind", it) for it in items])
    item = items[0]
    assert not may_show_candidate(blind_locked=False)
    assert "candidate_state" not in queue_columns(blind=True)
    assert "candidate_state" in strip_candidate_fields(
        {"x": 1}
    ) or "x" in strip_candidate_fields({"x": 1, "candidate_state": "y"})
    stripped = strip_candidate_fields({"frame_index": 0, "candidate_state": "y", "evidence_ledger": []})
    assert "candidate_state" not in stripped
    assert "evidence_ledger" not in stripped

    with pytest.raises(BlindRevealError):
        store.reveal_and_compare("blind", item.item_id, review_id="nope")

    with pytest.raises(ValueError):
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="blind",
            item_id=item.item_id,
            morphology="indeterminate",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="high",
            confidence="low",
            rationale="",
        )

    rec = BlindReviewRecord.create(
        reviewer_id="r1",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id="blind",
        item_id=item.item_id,
        morphology="frequency_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="low",
        confidence="high",
    )
    saved = store.save_blind_review("blind", rec)
    assert saved.locked
    assert may_show_candidate(blind_locked=True)
    # Strict cohort blinding: complete remaining round-one locks before reveal
    for other in items[1:]:
        store.save_blind_review(
            "blind",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="blind",
                item_id=other.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="complete round-one for strict blinding",
            ),
        )
    cmp = store.reveal_and_compare(
        "blind",
        item.item_id,
        review_id=saved.review_id,
        reviewer_note_codes=["candidate_supports_my_assessment"],
    )
    assert cmp.agreement_status in (
        "exact_agreement",
        "morphology_disagreement",
        "assessability_disagreement",
        "not_comparable",
        "candidate_abstained",
        "human_abstained",
        "both_abstained",
    )
    # Comparison must not alter blind decision
    again = store.locked_review_for_item("blind", item.item_id, review_round=1)
    assert again and again.review_id == saved.review_id
    assert again.morphology == "frequency_spread"

    # Post-reveal revision requires flag+reason
    with pytest.raises(BlindRevealError):
        store.save_blind_review(
            "blind",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="blind",
                item_id=item.item_id,
                morphology="range_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="fix",
                revision_reason="typo",
            ),
        )
    store.save_blind_review(
        "blind",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="blind",
            item_id=item.item_id,
            morphology="range_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
            rationale="fix after reveal",
            revision_reason="typo fix",
            post_reveal_revision=True,
            candidate_revealed_before_this_record=True,
        ),
    )
    cur = store.locked_review_for_item("blind", item.item_id, review_round=1)
    assert cur and cur.morphology == "range_spread"
    assert cur.prior_review_id == saved.review_id


def test_second_review_independence_and_adjudication(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(3), mode="manual", cohort_id="adj", sha_exists=lambda s: True
    )
    items = store.load_items("adj")
    store.freeze_cohort("adj", candidate_snapshots=[_snap("adj", it) for it in items])
    item = items[0]
    r1 = store.save_blind_review(
        "adj",
        BlindReviewRecord.create(
            reviewer_id="alice",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="adj",
            item_id=item.item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
        ),
    )
    with pytest.raises(BlindRevealError):
        store.save_blind_review(
            "adj",
            BlindReviewRecord.create(
                reviewer_id="alice",
                reviewer_role="second_reviewer",
                review_round=2,
                cohort_id="adj",
                item_id=item.item_id,
                morphology="range_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="moderate",
                confidence="moderate",
                rationale="second",
            ),
        )
    vis = store.second_review_visibility("adj", item.item_id, viewer_round=2)
    assert vis["first_review_visible"] is False
    assert vis["candidate_visible"] is False
    r2 = store.save_blind_review(
        "adj",
        BlindReviewRecord.create(
            reviewer_id="bob",
            reviewer_role="second_reviewer",
            review_round=2,
            cohort_id="adj",
            item_id=item.item_id,
            morphology="range_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="moderate",
            confidence="moderate",
            rationale="second",
        ),
    )
    vis2 = store.second_review_visibility("adj", item.item_id, viewer_round=2)
    assert vis2["agreement_visible"] is True
    adj = AdjudicationRecord(
        adjudication_id=str(uuid4()),
        adjudicator_id="carol",
        cohort_id="adj",
        item_id=item.item_id,
        input_review_ids=[r1.review_id, r2.review_id],
        adjudicated_morphology="mixed_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="moderate",
        rationale="Adjudicated expert reference — not ground truth",
    ).with_hash()
    assert adj.label == "adjudicated_expert_reference"
    store.save_adjudication("adj", adj)
    # Candidate still not auto-called ground truth
    assert "ground_truth" not in adj.label


def test_candidate_snapshot_freeze_no_overwrite(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(2), mode="manual", cohort_id="snap", sha_exists=lambda s: True
    )
    item = store.load_items("snap")[0]
    store.freeze_cohort("snap")
    s1 = store.append_candidate_snapshot("snap", _snap("snap", item))
    with pytest.raises(FrozenCohortError):
        store.append_candidate_snapshot(
            "snap",
            CandidateSnapshot(
                **{
                    **s1.to_dict(),
                    "snapshot_hash": "",
                    "ruleset_hash": "other_ruleset",
                    "result_hash": "z" * 64,
                }
            ),
        )
    # Exact reuse OK
    reused = store.append_candidate_snapshot("snap", _snap("snap", item))
    assert reused.result_hash == s1.result_hash


def test_analytics_descriptive_only_no_accuracy(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(4), mode="random", count=2, seed=9, cohort_id="an", sha_exists=lambda s: True
    )
    items = store.load_items("an")
    store.freeze_cohort("an", candidate_snapshots=[_snap("an", it) for it in items])
    for it in items:
        store.save_blind_review(
            "an",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="an",
                item_id=it.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
            ),
        )
    summary = descriptive_summary(store, "an")
    blob = json.dumps(summary)
    assert "accuracy" not in summary
    assert "f1" not in summary
    assert "precision" not in summary
    assert summary["kind"] == "descriptive_summary"
    inter = inter_reviewer_descriptive(store, "an")
    assert inter["defined"] is False  # only one reviewer
    refused = refuse_unsupported_metrics(["accuracy", "f1"])
    assert refused["ok"] is False
    assert "accuracy" in refused["refused"]


def test_exports_utf8_no_abs_no_candidate_leak(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(3), mode="manual", cohort_id="ex", sha_exists=lambda s: True
    )
    items = store.load_items("ex")
    store.freeze_cohort("ex", candidate_snapshots=[_snap("ex", it) for it in items])
    it = items[0]
    saved = None
    for row in items:
        saved = store.save_blind_review(
            "ex",
            BlindReviewRecord.create(
                reviewer_id="r1",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="ex",
                item_id=row.item_id,
                morphology="no_supported_visible_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="moderate",
                rationale="export fixture",
            ),
        )
    assert saved is not None
    # Reveal first item after full round-one (strict default)
    first = store.locked_review_for_item("ex", it.item_id, review_round=1)
    assert first is not None
    store.reveal_and_compare("ex", it.item_id, review_id=first.review_id)
    out = export_cohort(store, "ex")
    blind = (out / "blind_reviews.jsonl").read_text(encoding="utf-8")
    assert "candidate_state" not in blind
    assert "evidence_ledger" not in blind
    assert "E:\\" not in blind and "C:\\" not in blind
    md = (out / "summary.md").read_text(encoding="utf-8")
    assert "Not a scientific validation" in md or "not a scientific" in md.lower()
    bundle = json.loads((out / "cohort_bundle.json").read_text(encoding="utf-8"))
    assert bundle["build_identity"] == "ML-C.1b"
    assert "accuracy" not in bundle.get("summary", {})


def test_hashes_stable_and_integrity(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(3), mode="random", count=2, seed=11, cohort_id="hash", sha_exists=lambda s: True
    )
    items = store.load_items("hash")
    store.freeze_cohort("hash", candidate_snapshots=[_snap("hash", it) for it in items])
    it = items[0]
    store.save_blind_review(
        "hash",
        BlindReviewRecord.create(
            reviewer_id="r1",
            reviewer_role="reviewer",
            review_round=1,
            cohort_id="hash",
            item_id=it.item_id,
            morphology="frequency_spread",
            assessability="assessable",
            interference=["none_supported"],
            ambiguity="low",
            confidence="high",
        ),
    )
    export_cohort(store, "hash")
    errors = validate_cohort(store, "hash")
    assert errors == [], errors
    root = Path(__file__).resolve().parents[1]
    assert validate_no_production_ruleengine_wiring(root) == []


def test_comparison_status_matrix():
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="frequency_spread_candidate",
            candidate_assessability="assessable",
        )
        == "exact_agreement"
    )
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="range_spread_candidate",
        )
        == "morphology_disagreement"
    )
    assert (
        comparison_status(
            human_morphology="indeterminate",
            human_assessability="not_assessable",
            candidate_state="indeterminate",
        )
        == "both_abstained"
    )


def test_portable_paths_rejected_in_records():
    from ionogram_morphology_lab.morphology_review_corpus.hashing import assert_no_absolute_paths

    with pytest.raises(ValueError):
        assert_no_absolute_paths({"path": r"E:\ionog\data\file.mat"})


def test_build_identity_phase_4c2():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity

    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-C.1b"
    assert info["candidate_engine_version"] == "iml-morph-candidate-0.1.1"
    assert info["review_corpus_schema_version"] == 1
    assert info.get("scientifically_validated") is False


def test_reviewer_identity_configurable(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_from_sampling(
        pool=_pool(2), mode="manual", cohort_id="rev", sha_exists=lambda s: True
    )
    store.upsert_reviewer(
        "rev", ReviewerIdentity("id1", "Alias One", role="reviewer", organization="")
    )
    rows = store.list_reviewers("rev")
    assert rows[0].display_alias == "Alias One"
    assert rows[0].reviewer_id == "id1"


def test_schema_serialization_roundtrip():
    rec = BlindReviewRecord.create(
        reviewer_id="r",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id="c",
        item_id="i",
        morphology="mixed_spread",
        assessability="partially_assessable",
        interference=["vertical_interference", "uncertain"],
        ambiguity="moderate",
        confidence="moderate",
        rationale="",
    )
    again = BlindReviewRecord.from_dict(rec.to_dict())
    assert again.record_hash == rec.record_hash
    assert deterministic_hash({k: v for k, v in rec.to_dict().items() if k != "record_hash"}) == rec.record_hash
