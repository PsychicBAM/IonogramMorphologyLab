"""Phase 4C.2a.1 — draft add/remove/clear and exact Viewer identity."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.morphology_review_corpus.project_items import (
    current_viewer_frame_item,
)
from ionogram_morphology_lab.morphology_review_corpus.store import (
    FrozenCohortError,
    MorphologyReviewCorpusStore,
)
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.session import AppSession


@pytest.fixture
def session(tmp_path: Path) -> AppSession:
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    s = AppSession(settings=settings)
    s.project = create_project("DraftEdit", language="en", workspace_parent=tmp_path / "ws")
    s.add_to_inventory(mats[0], make_active=True)
    s.current_frame = 2
    return s


def test_add_remove_viewer_frame_exact_identity(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    item = current_viewer_frame_item(session)
    store.create_cohort(items=[], sampling_method="manual", cohort_id="d1")
    assert not store.draft_contains_identity("d1", item["source_sha256"], item["frame_index"])
    r = store.add_items_to_draft("d1", [item])
    assert r["added"] == 1
    assert store.load_manifest("d1").item_count == 1
    assert store.draft_contains_identity("d1", item["source_sha256"], int(item["frame_index"]))
    # duplicate rejected
    r2 = store.add_items_to_draft("d1", [item])
    assert r2["added"] == 0
    assert r2["duplicates"]
    rem = store.remove_items_from_draft(
        "d1",
        identities=[(item["source_sha256"], int(item["frame_index"]))],
    )
    assert rem["removed_count"] == 1
    assert store.load_manifest("d1").item_count == 0
    assert not store.draft_contains_identity("d1", item["source_sha256"], int(item["frame_index"]))
    audit = (store.path_for("d1") / "audit_log.jsonl").read_text(encoding="utf-8")
    assert "item_addition" in audit
    assert "item_removal" in audit


def test_remove_selected_and_clear_draft(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    items = []
    for fr in (1, 2, 3):
        session.current_frame = fr
        items.append(current_viewer_frame_item(session))
    store.create_cohort(items=items, sampling_method="manual", cohort_id="d2")
    ids = [it.item_id for it in store.load_items("d2")]
    store.remove_items_from_draft("d2", item_ids=ids[:2])
    assert store.load_manifest("d2").item_count == 1
    store.clear_draft("d2")
    assert store.load_manifest("d2").item_count == 0
    assert (store.path_for("d2") / "protocol.json").is_file()
    audit = (store.path_for("d2") / "audit_log.jsonl").read_text(encoding="utf-8")
    assert "draft_clear" in audit


def test_frozen_rejects_draft_mutations(session: AppSession):
    store = MorphologyReviewCorpusStore(session.project.root)
    item = current_viewer_frame_item(session)
    store.create_cohort(items=[item], sampling_method="manual", cohort_id="fz")
    store.freeze_cohort("fz")
    with pytest.raises(FrozenCohortError):
        store.add_items_to_draft("fz", [item])
    with pytest.raises(FrozenCohortError):
        store.remove_items_from_draft("fz", item_ids=["x"])
    with pytest.raises(FrozenCohortError):
        store.clear_draft("fz")
    with pytest.raises(FrozenCohortError):
        store.delete_draft("fz")
