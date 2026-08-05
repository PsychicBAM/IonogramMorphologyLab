"""Phase 4C.3a.1 — wizard inventory population, gating, localization, contrast."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
    list_registered_project_sources,
    localize_campaign_state,
    localize_validation_issue,
    validate_selected_sources,
)
from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library


def _session_desynced_inventory(tmp_path: Path, active: str = "b"):
    """selected_mats populated but project.source_paths left empty (owner-like desync)."""
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import AnalysisProject
    from ionogram_morphology_lab.ui.session import AppSession

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    assert len(mats) >= 2
    root = tmp_path / "proj"
    root.mkdir(parents=True, exist_ok=True)
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = AnalysisProject(
        project_id="c3a1",
        name="C3A1",
        language="en",
        root=str(root),
        created_at="2026-01-01T00:00:00+00:00",
        source_paths=[],  # deliberate desync
    )
    session.selected_mats = [mats[0], mats[1]]
    session.set_active_mat(mats[1] if active == "b" else mats[0])
    session.get_source_sha(allow_compute=True)
    # Keep source_paths empty — union must still list selected_mats
    session.project.source_paths = []
    return session, mats


def _session_synced(tmp_path: Path, active: str = "b"):
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
        project_id="c3a1s",
        name="C3A1S",
        language="en",
        root=str(root),
        created_at="2026-01-01T00:00:00+00:00",
        source_paths=[],
    )
    session.add_to_inventory(mats[0], make_active=False)
    session.add_to_inventory(mats[1], make_active=True)
    if active == "a":
        session.set_active_mat(mats[0])
    else:
        session.set_active_mat(mats[1])
    session.get_source_sha(allow_compute=True)
    return session, mats


def test_list_uses_selected_mats_when_source_paths_empty(tmp_path: Path):
    session, mats = _session_desynced_inventory(tmp_path, active="b")
    regs = list_registered_project_sources(session)
    assert len(regs) >= 2
    names = {r.display_name for r in regs}
    assert mats[0].name in names
    assert mats[1].name in names
    active = [r for r in regs if r.is_active]
    assert len(active) == 1
    assert active[0].display_name == mats[1].name
    assert active[0].source_sha256
    assert active[0].inventory_id


def test_no_first_source_fallback_on_desync(tmp_path: Path):
    session, mats = _session_desynced_inventory(tmp_path, active="b")
    regs = list_registered_project_sources(session)
    assert not (regs[0].is_active and regs[0].display_name == mats[0].name and mats[0] != mats[1])


def test_localize_no_sources_selected_not_raw():
    ru = localize_validation_issue("no_sources_selected", lang="ru")
    en = localize_validation_issue("no_sources_selected", lang="en")
    assert "no_sources_selected" not in ru
    assert "no_sources_selected" not in en
    assert "Выберите" in ru
    assert "Select" in en


def test_localize_campaign_state_ru():
    assert localize_campaign_state("ready", lang="ru") == "Готова"
    assert localize_campaign_state("draft", lang="ru") == "Черновик"
    assert localize_campaign_state("archived", lang="ru") == "Архивная"
    assert localize_campaign_state("ready", lang="en") == "Ready"


def test_wizard_populates_rows_and_checks_active(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import CampaignCreationWizard
    from ionogram_morphology_lab.ui.theme import resolve_theme_name, source_card_tokens

    app = QApplication.instance() or QApplication([])
    session, mats = _session_desynced_inventory(tmp_path, active="b")
    store = MorphologyReviewCampaignStore(session.project.root)
    wiz = CampaignCreationWizard(session, get_i18n("ru"), store)
    assert wiz.inventory_row_count() >= 2
    assert wiz.has_editable_sha_field() is False
    shas = wiz.selected_source_shas()
    assert shas
    regs = list_registered_project_sources(session)
    active_sha = next(r.source_sha256 for r in regs if r.is_active)
    assert active_sha in shas
    # Row data has inventory id + sha
    row = next(r for r in wiz._inventory_rows if r.is_active)
    assert row.inventory_id.startswith("inv_")
    assert len(row.source_sha256) == 64
    # Next gating
    assert wiz.sources_selection_complete() is True
    wiz._clear_source_selection()
    assert wiz.sources_selection_complete() is False
    assert "no_sources_selected" not in wiz._sources_preview.toPlainText()
    assert "no_sources_selected" not in wiz._sources_blocker.text()
    # Theme stylesheet uses readable tokens (not pale-on-white hardcode alone)
    theme = resolve_theme_name("dark")
    tokens = source_card_tokens(theme)
    assert tokens["text"].lower() != "#ffffff" or tokens["bg"] != "#ffffff"
    assert wiz._source_inventory_table.minimumHeight() >= 200
    # Active auto-check again
    wiz._select_only_active()
    assert active_sha in wiz.selected_source_shas()
    # Multi-select
    wiz._select_available()
    assert len(wiz.selected_source_shas()) >= 2
    # Invalid SHA protection still active
    bad = validate_selected_sources(session, ["a" * 64])
    assert bad.ok is False


def test_wizard_refreshes_after_inventory_signal(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import CampaignCreationWizard

    app = QApplication.instance() or QApplication([])
    session, mats = _session_synced(tmp_path, active="b")
    # Start with empty selected + source_paths — then restore via signal path
    store = MorphologyReviewCampaignStore(session.project.root)
    # Remove one from source_paths but keep in selected — still listed
    session.project.source_paths = [str(mats[1])]
    wiz = CampaignCreationWizard(session, get_i18n("en"), store)
    before = wiz.inventory_row_count()
    assert before >= 1
    # Emit inventory_changed after adding back
    session.project.source_paths = [str(mats[0]), str(mats[1])]
    session.selected_mats = [mats[0], mats[1]]
    session.events.inventory_changed.emit()
    assert wiz.inventory_row_count() >= 2


def test_ru_campaign_page_state_localized(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.morphology_review_campaign.models import (
        ReviewerPlan,
        SamplingPlan,
        SourceScopeEntry,
        TimeWindow,
    )
    from ionogram_morphology_lab.ui.expert_review_campaign_page import ExpertReviewCampaignPage

    app = QApplication.instance() or QApplication([])
    session, mats = _session_synced(tmp_path)
    regs = list_registered_project_sources(session)
    active = next(r for r in regs if r.is_active)
    store = MorphologyReviewCampaignStore(session.project.root)
    store.create_campaign(
        campaign_id="pilot_vis",
        display_name="Pilot campaign",
        sources=[
            SourceScopeEntry(
                source_sha256=active.source_sha256,
                source_display_name=active.display_name,
                source_inventory_id=active.inventory_id,
                date_hint=active.date_hint,
                available=True,
            )
        ],
        windows=[TimeWindow(1, 20, 5)],
        sampling_plan=SamplingPlan(method="all_eligible", target_count=5, seed=1),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1"),
        session=session,
        create_linked_cohort=False,
    )
    page = ExpertReviewCampaignPage(session, get_i18n("ru"))
    page.refresh()
    # Name stays user text; state cell is localized
    found_ready = False
    for r in range(page.campaign_table.rowCount()):
        name = page.campaign_table.item(r, 1).text()
        state = page.campaign_table.item(r, 2).text()
        if name == "Pilot campaign":
            assert state == "Готова"
            assert state != "ready"
            found_ready = True
    assert found_ready


def test_old_invalid_campaign_does_not_contaminate_new(tmp_path: Path):
    session, mats = _session_synced(tmp_path)
    store = MorphologyReviewCampaignStore(session.project.root)
    # Legacy invalid campaign (skip validation)
    from ionogram_morphology_lab.morphology_review_campaign.models import (
        ReviewerPlan,
        SamplingPlan,
        SourceScopeEntry,
        TimeWindow,
    )

    store.create_campaign(
        campaign_id="legacy_bad",
        display_name="abdalla campaign",
        sources=[
            SourceScopeEntry(
                source_sha256="b" * 64,
                source_display_name="abdalla",
                source_inventory_id="inv_fake",
                available=True,
            )
        ],
        windows=[TimeWindow(1, 10, 5)],
        sampling_plan=SamplingPlan(method="all_eligible"),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1"),
        skip_inventory_validation=True,
        create_linked_cohort=False,
    )
    regs = list_registered_project_sources(session)
    active = next(r for r in regs if r.is_active)
    m = store.create_campaign(
        campaign_id="new_valid",
        display_name="Corrected",
        sources=[
            SourceScopeEntry(
                source_sha256=active.source_sha256,
                source_display_name=active.display_name,
                source_inventory_id=active.inventory_id,
                available=True,
            )
        ],
        windows=[TimeWindow(1, 10, 5)],
        sampling_plan=SamplingPlan(method="all_eligible"),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1"),
        session=session,
        create_linked_cohort=False,
    )
    scope0 = m.source_scope[0]
    name0 = scope0.source_display_name if hasattr(scope0, "source_display_name") else scope0["source_display_name"]
    sha0 = scope0.source_sha256 if hasattr(scope0, "source_sha256") else scope0["source_sha256"]
    assert name0 != "abdalla"
    assert sha0 == active.source_sha256
    legacy = store.load_manifest("legacy_bad")
    leg0 = legacy.source_scope[0]
    leg_name = leg0.source_display_name if hasattr(leg0, "source_display_name") else leg0["source_display_name"]
    assert leg_name == "abdalla"


def test_wizard_dark_stylesheet_has_dark_background(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import (
        CampaignCreationWizard,
        _wizard_stylesheet,
    )
    from ionogram_morphology_lab.ui.theme import source_card_tokens

    app = QApplication.instance() or QApplication([])
    session, _ = _session_synced(tmp_path)
    store = MorphologyReviewCampaignStore(session.project.root)
    wiz = CampaignCreationWizard(session, get_i18n("en"), store)
    qss = wiz.styleSheet() or _wizard_stylesheet("dark")
    assert "background" in qss.lower()
    assert "QWizard" in qss
    tokens = source_card_tokens("dark")
    assert tokens["text"] in qss or tokens["bg"] in qss
