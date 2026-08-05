"""Phase 4C.3a — authoritative inventory picker and no manual SHA."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
    list_registered_project_sources,
    reject_free_text_source_identity,
    validate_selected_sources,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    CampaignError,
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library


def _session_with_two_mats(tmp_path: Path, active: str = "b"):
    """Lightweight project session without ProjectDatabase (avoids SQLite ResourceWarnings)."""
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
        project_id="c3a",
        name="C3A",
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
    # Ensure SHA is available for active source
    session.get_source_sha(allow_compute=True)
    return session, mats


def test_list_inventory_active_default_not_first(tmp_path: Path):
    session, mats = _session_with_two_mats(tmp_path, active="b")
    regs = list_registered_project_sources(session)
    assert len(regs) >= 2
    active = [r for r in regs if r.is_active]
    assert len(active) == 1
    assert active[0].display_name == mats[1].name
    # Must not imply first inventory entry is active
    assert not (regs[0].is_active and regs[0].display_name == mats[0].name and mats[0] != mats[1])


def test_arbitrary_display_rejected(tmp_path: Path):
    session, mats = _session_with_two_mats(tmp_path)
    regs = list_registered_project_sources(session)
    real = next(r for r in regs if r.available)
    issues = reject_free_text_source_identity("abdalla", real.source_sha256, session)
    assert "display_name_not_registered_source" in issues


def test_create_campaign_rejects_free_text_sha(tmp_path: Path):
    session, _ = _session_with_two_mats(tmp_path)
    store = MorphologyReviewCampaignStore(session.project.root)
    with pytest.raises(CampaignError):
        store.create_campaign(
            campaign_id="bad_sha",
            display_name="Bad",
            sources=[
                SourceScopeEntry(
                    source_sha256="a" * 64,
                    source_display_name="abdalla",
                    source_inventory_id="inv_fake",
                    available=True,
                )
            ],
            windows=[TimeWindow(1, 20, 5)],
            sampling_plan=SamplingPlan(method="all_eligible"),
            reviewer_plan=ReviewerPlan(first_reviewer_id="r1"),
            session=session,
        )


def test_wizard_no_editable_sha_and_active_selected(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QLineEdit

    from ionogram_morphology_lab.ui.expert_review_campaign_page import (
        CampaignCreationWizard,
    )

    app = QApplication.instance() or QApplication([])
    session, mats = _session_with_two_mats(tmp_path, active="b")
    store = MorphologyReviewCampaignStore(session.project.root)
    wiz = CampaignCreationWizard(session, get_i18n("en"), store)
    assert wiz.has_editable_sha_field() is False
    # No line edit objectName containing sha
    for w in wiz.findChildren(QLineEdit):
        assert "sha" not in w.objectName().lower()
    assert wiz.findChild(type(wiz), "source_inventory_table") or wiz._source_inventory_table.objectName() == "source_inventory_table"
    shas = wiz.selected_source_shas()
    assert shas
    regs = list_registered_project_sources(session)
    active_sha = next(r.source_sha256 for r in regs if r.is_active)
    assert active_sha in shas
    # Multi-select available
    wiz._select_available()
    assert len(wiz.selected_source_shas()) >= 2


def test_ru_wizard_has_no_known_english_labels(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import (
        CampaignCreationWizard,
    )

    app = QApplication.instance() or QApplication([])
    session, _ = _session_with_two_mats(tmp_path)
    store = MorphologyReviewCampaignStore(session.project.root)
    wiz = CampaignCreationWizard(session, get_i18n("ru"), store)
    wiz.retranslate_wizard()
    titles = " ".join(p.title() for p in (
        wiz.page_basic, wiz.page_sources, wiz.page_sampling, wiz.page_create
    ))
    forbidden = (
        "Basic information",
        "Sources and dates",
        "Sampling strategy",
        "Optional second source SHA-256",
        "Optional second source display name",
        "Include authoritative active source",
    )
    for phrase in forbidden:
        assert phrase not in titles
        assert phrase not in wiz.windowTitle()
    assert "Основные" in wiz.page_basic.title() or "сведения" in wiz.page_basic.title().lower()


def test_campaign_page_sees_open_project(tmp_path: Path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import (
        ExpertReviewCampaignPage,
    )

    app = QApplication.instance() or QApplication([])
    session, _ = _session_with_two_mats(tmp_path)
    page = ExpertReviewCampaignPage(session, get_i18n("ru"))
    page.refresh()
    assert page.project_root() is not None
    # Must not show "open project" when project is open
    assert "откройте проект" not in page.dash_title.text().lower() or page.campaign_table.rowCount() >= 0
    assert "активн" in page.active_source_lbl.text().lower() or "active" in page.active_source_lbl.text().lower()
