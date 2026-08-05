"""Phase 4C.2a.1 — editable revision, archive visibility, legacy synthetic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_review_corpus.integrity import validate_cohort
from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
    CorpusLifecycleError,
    is_archived,
    is_legacy_synthetic_cohort,
    load_workspace,
)
from ionogram_morphology_lab.morphology_review_corpus.models import BlindReviewRecord
from ionogram_morphology_lab.morphology_review_corpus.store import (
    FrozenCohortError,
    MorphologyReviewCorpusStore,
)


def _realish_items(n: int = 3) -> list[dict]:
    # Non-zero-leading SHAs so fixtures are not legacy-synthetic
    return [
        {
            "source_sha256": f"{(0xABCDEF00 + i):064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"real_{i}.mat",
            "source_inventory_id": f"inv_real_{i}",
            "feature_version": "iml2-0.2.0",
            "frame_time": f"12:0{i}:00",
        }
        for i in range(n)
    ]


def _legacy_items(n: int = 3) -> list[dict]:
    return [
        {
            "source_sha256": f"{i+1:064x}"[-64:],
            "frame_index": i,
            "source_display_name": f"pilot_frame_{i}",
            "source_inventory_id": f"pilot_inv_{i}",
            "feature_version": "iml2-0.2.0",
            "inclusion_reason": "synthetic developer placeholder",
        }
        for i in range(n)
    ]


def test_editable_revision_preserves_parent(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_realish_items(3), sampling_method="manual", cohort_id="parent")
    items = store.load_items("parent")
    store.freeze_cohort("parent")
    parent_hash = store.load_manifest("parent").manifest_hash
    parent_bytes = (store.path_for("parent") / "cohort_manifest.json").read_bytes()
    # lock a blind review on parent
    it = items[0]
    rec = BlindReviewRecord.create(
        reviewer_id="r1",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id="parent",
        item_id=it.item_id,
        morphology="frequency_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="low",
        confidence="high",
        rationale="parent review must not copy",
    )
    store.save_blind_review("parent", rec)
    parent_bytes_after_review = (store.path_for("parent") / "cohort_manifest.json").read_bytes()
    # manifest scientific fields unchanged by review append (item status is in items.jsonl)
    assert parent_bytes_after_review == parent_bytes

    with pytest.raises(CorpusLifecycleError):
        store.create_editable_revision("parent", reason="")

    child = store.create_editable_revision("parent", reason="extend sample for pilot QA")
    assert child.cohort_id != "parent"
    assert child.parent_cohort_id == "parent"
    assert child.revision_number == 1
    assert child.revision_reason == "extend sample for pilot QA"
    assert child.created_from_manifest_hash == parent_hash
    assert not child.frozen
    assert child.item_count == 3
    # reviews not copied
    child_reviews = (store.path_for(child.cohort_id) / "blind_reviews.jsonl").read_text(
        encoding="utf-8"
    ).strip()
    assert child_reviews == ""
    assert (store.path_for("parent") / "cohort_manifest.json").read_bytes() == parent_bytes
    assert validate_cohort(store, "parent") == []
    # mutate child
    store.add_items_to_draft(
        child.cohort_id,
        [
            {
                "source_sha256": f"{0xDEADBEEF:064x}"[-64:],
                "frame_index": 9,
                "source_display_name": "extra.mat",
                "source_inventory_id": "inv_extra",
            }
        ],
    )
    assert store.load_manifest(child.cohort_id).item_count == 4
    assert (store.path_for("parent") / "cohort_manifest.json").read_bytes() == parent_bytes
    store.freeze_cohort(child.cohort_id)
    child_m = store.load_manifest(child.cohort_id)
    assert child_m.frozen
    assert child_m.manifest_hash != parent_hash
    assert validate_cohort(store, child.cohort_id) == []


def test_archive_workspace_only(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(items=_realish_items(2), sampling_method="manual", cohort_id="arch")
    store.freeze_cohort("arch")
    h = store.load_manifest("arch").manifest_hash
    store.archive_cohort("arch")
    assert is_archived(tmp_path, "arch")
    assert store.load_manifest("arch").manifest_hash == h
    assert store.load_manifest("arch").frozen
    ws = load_workspace(tmp_path)
    assert "arch" in ws["archived_cohort_ids"]
    store.unarchive_cohort("arch")
    assert not is_archived(tmp_path, "arch")
    assert store.load_manifest("arch").frozen
    assert store.load_manifest("arch").manifest_hash == h


def test_legacy_synthetic_detection(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    m = store.create_cohort(
        items=_legacy_items(3), sampling_method="manual", cohort_id="legacy_pilot"
    )
    assert m.legacy_synthetic
    items = store.load_items("legacy_pilot")
    assert is_legacy_synthetic_cohort(m, items)
    info: list[str] = []
    errs = validate_cohort(store, "legacy_pilot", collect_info=info)
    assert errs == [] or all("failed" not in e for e in errs)
    assert any("legacy_synthetic" in x for x in info)
    # real corpus with word pilot in name is not synthetic
    real = store.create_cohort(
        items=[
            {
                "source_sha256": f"{0x1111222233334444:064x}"[-64:],
                "frame_index": 0,
                "source_display_name": "pilot_campaign_2014.mat",
                "source_inventory_id": "inv_campaign",
            }
        ],
        sampling_method="manual",
        cohort_id="pilot_real",
    )
    assert not real.legacy_synthetic
    # no silent deletion
    assert "legacy_pilot" in store.list_cohorts()
    store.archive_cohort("legacy_pilot")
    assert is_archived(tmp_path, "legacy_pilot")


def test_selection_does_not_leak_across_projects(tmp_path: Path):
    from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
        get_selected_cohort,
        set_selected_cohort,
    )

    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p1.mkdir()
    p2.mkdir()
    s1 = MorphologyReviewCorpusStore(p1)
    s2 = MorphologyReviewCorpusStore(p2)
    s1.create_cohort(items=_realish_items(1), sampling_method="manual", cohort_id="c1")
    s2.create_cohort(items=_realish_items(1), sampling_method="manual", cohort_id="c2")
    set_selected_cohort(p1, "c1")
    set_selected_cohort(p2, "c2")
    assert get_selected_cohort(p1) == "c1"
    assert get_selected_cohort(p2) == "c2"
    assert get_selected_cohort(p1) != get_selected_cohort(p2)
