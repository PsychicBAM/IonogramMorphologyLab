"""Phase 4C.3a — invalid campaign repair and hydration gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
    list_registered_project_sources,
    validate_selected_sources,
)
from ionogram_morphology_lab.morphology_review_campaign.repair import (
    inspect_campaign_source_bindings,
    repair_campaign_source_mapping,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.build_identity import collect_build_identity


def _session(tmp_path: Path):
    """Lightweight project session without ProjectDatabase (avoids SQLite ResourceWarnings)."""
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import AnalysisProject
    from ionogram_morphology_lab.ui.session import AppSession

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    root = tmp_path / "proj"
    root.mkdir(parents=True, exist_ok=True)
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = AnalysisProject(
        project_id="rep",
        name="REP",
        language="en",
        root=str(root),
        created_at="2026-01-01T00:00:00+00:00",
        source_paths=[],
    )
    session.add_to_inventory(mats[0], make_active=True)
    session.add_to_inventory(mats[1], make_active=False)
    session.set_active_mat(mats[0])
    session.get_source_sha(allow_compute=True)
    return session, mats


def test_repair_creates_corrected_without_mutating_frozen_original(tmp_path: Path):
    session, mats = _session(tmp_path)
    store = MorphologyReviewCampaignStore(session.project.root)
    # Legacy invalid campaign written directly (simulates defective wizard)
    cid = "legacy_bad"
    d = store.path_for(cid)
    d.mkdir(parents=True)
    (d / "exports").mkdir()
    fake_sha = "b" * 64
    campaign = {
        "campaign_id": cid,
        "display_name": "Bad",
        "designation_en": "Pilot",
        "designation_ru": "Пилот",
        "description": "",
        "state": "ready",
        "created_at_utc": "2026-01-01T00:00:00+00:00",
        "created_by": "owner",
        "schema_version": 1,
        "protocol_version": 1,
        "project_identity": "REP",
        "source_scope": [
            {
                "source_sha256": fake_sha,
                "source_display_name": "abdalla",
                "source_inventory_id": "inv_fake",
                "date_hint": "",
                "available": True,
            }
        ],
        "time_windows": [{"start_frame": 1, "end_frame": 30, "step": 5, "label": "w"}],
        "target_review_count": 3,
        "actual_item_count": 0,
        "reviewer_plan": {"first_reviewer_id": "r1", "second_reviewer_optional": True},
        "reveal_policy": "strict_cohort_blinding",
        "sampling_plan": {"method": "all_eligible", "seed": 1, "target_count": 0},
        "grouping_plan": {},
        "selected_item_fingerprints": [],
        "protocol_hash": "a" * 64,
        "campaign_hash": "",
        "build_identity": "4C.3",
        "shadow_only": True,
        "scientifically_validated": False,
    }
    from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

    payload = dict(campaign)
    payload.pop("campaign_hash", None)
    campaign["campaign_hash"] = deterministic_hash(payload)
    (d / "campaign.json").write_text(json.dumps(campaign, indent=2), encoding="utf-8")
    (d / "campaign_protocol.json").write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "reveal_policy": "strict_cohort_blinding",
                "designation_en": "Pilot",
                "designation_ru": "Пилот",
                "second_reviewer_optional": True,
                "candidate_shadow_only": True,
                "scientifically_validated": False,
                "protocol_hash": "a" * 64,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Create a frozen linked cohort with invalid SHA items
    items = [
        {
            "source_sha256": fake_sha,
            "frame_index": i,
            "source_display_name": "abdalla",
            "source_inventory_id": "inv_fake",
        }
        for i in range(1, 4)
    ]
    cm = store.corpus.create_cohort(cohort_id=f"{cid}_first", items=items)
    store.corpus.freeze_cohort(cm.cohort_id)
    frozen_hash = store.corpus.load_manifest(cm.cohort_id).manifest_hash
    from ionogram_morphology_lab.morphology_review_campaign.models import CohortLink

    link = CohortLink.create(
        campaign_id=cid,
        cohort_id=cm.cohort_id,
        cohort_role="first_review",
        manifest_hash=frozen_hash,
    )
    store._append_jsonl(d / "cohort_links.jsonl", link.to_dict())

    insp = inspect_campaign_source_bindings(store, cid, session)
    assert insp["needs_repair"]
    regs = list_registered_project_sources(session)
    mapped = [r.source_sha256 for r in regs if r.available][:1]
    report = repair_campaign_source_mapping(store, cid, session, mapped_shas=mapped)
    assert report["repaired"]
    assert report["corrected_campaign_id"] != cid
    # Original frozen cohort unchanged
    assert store.corpus.load_manifest(cm.cohort_id).manifest_hash == frozen_hash
    assert store.load_manifest(cid).state == "archived"
    # Corrected has real inventory name, not abdalla
    corr = store.load_manifest(report["corrected_campaign_id"])
    names = [s.get("source_display_name") for s in corr.source_scope]
    assert "abdalla" not in names
    assert all(n.endswith(".mat") for n in names)


def test_valid_source_validation_and_preview_identities(tmp_path: Path):
    session, _ = _session(tmp_path)
    regs = [r for r in list_registered_project_sources(session) if r.available]
    assert len(regs) >= 1
    result = validate_selected_sources(session, [regs[0].source_sha256])
    assert result.ok
    assert result.sources[0].source_display_name == regs[0].display_name
    assert result.sources[0].source_inventory_id == regs[0].inventory_id

    store = MorphologyReviewCampaignStore(session.project.root)
    m = store.create_campaign(
        campaign_id="good1",
        display_name="Good",
        sources=result.sources,
        windows=[TimeWindow(1, 40, 10)],
        sampling_plan=SamplingPlan(method="deterministic_random", seed=5, target_count=3),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1", first_reviewer_alias="Expert A"),
        session=session,
    )
    # Reviewer alias must not become source display name
    assert m.source_scope[0]["source_display_name"] != "Expert A"
    assert m.source_scope[0]["source_display_name"].endswith(".mat")


def test_build_identity_4c3a():
    ident = collect_build_identity(compute_sha=False)
    assert ident["release_phase"] == "4C.3a.2"
    assert ident["shadow_only"] is True


def test_review_blocks_unregistered_sha(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.review_ionogram_view import ReviewIonogramView

    app = QApplication.instance() or QApplication([])
    session, _ = _session(tmp_path)
    view = ReviewIonogramView()
    ok = view.load_item(
        session,
        source_sha256="c" * 64,
        frame_index=1,
        display_name="abdalla",
        lang="ru",
    )
    assert ok is False
    assert "несовпадение" in view.status.text().lower() or "sha" in view.status.text().lower()
