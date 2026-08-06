"""Phase 4C.3 — campaign integrity, RU/EN, unavailable items."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_campaign.constants import (
    CAMPAIGN_DESIGNATION_RU,
)
from ionogram_morphology_lab.morphology_review_campaign.integrity import validate_campaign
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)


def test_validator_passes_synthetic_campaign(tmp_path: Path):
    store = MorphologyReviewCampaignStore(tmp_path)
    store.create_campaign(
        campaign_id="val1",
        display_name="Val",
        sources=[
            SourceScopeEntry(f"{0xA101:064x}"[-64:], "v.mat", "iv", "2014", True),
            SourceScopeEntry(
                f"{0xA102:064x}"[-64:], "missing.mat", "im", "2014", available=False
            ),
        ],
        windows=[TimeWindow(1, 30, 5)],
        sampling_plan=SamplingPlan(method="all_eligible"),
        reviewer_plan=ReviewerPlan(first_reviewer_id="r1", second_reviewer_optional=True),
    )
    report = validate_campaign(store, "val1")
    assert report["ok"], report["issues"]
    prog = campaign_progress(store, "val1")
    # Unavailable source frames counted
    assert prog["unavailable_items"] >= 1


def test_ru_en_designation_and_nav_keys():
    en = get_i18n("en")
    assert "Campaign" in en.t("nav.campaigns") or "campaign" in en.t("nav.campaigns").lower()
    ru = get_i18n("ru")
    assert "Кампании" in ru.t("nav.campaigns")
    assert "не обязателен" in ru.t("campaign.second_optional").lower()
    # Restore EN for other tests sharing the singleton
    get_i18n("en")
    assert CAMPAIGN_DESIGNATION_RU


def test_build_identity_phase():
    from ionogram_morphology_lab.ui.build_identity import collect_build_identity

    ident = collect_build_identity(compute_sha=False)
    assert ident["release_phase"] == "ML-A.1a.2"
    assert ident["shadow_only"] is True
    assert ident["scientifically_validated"] is False


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_campaign_page_retranslate(lang, tmp_path: Path):
    """UI retranslate without opening ProjectDatabase (avoids SQLite ResourceWarnings)."""
    pytest.importorskip("PySide6")
    from types import SimpleNamespace

    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.ui.expert_review_campaign_page import (
        ExpertReviewCampaignPage,
    )

    app = QApplication.instance() or QApplication([])
    # Lightweight stand-in — no SQLite project DB
    session = SimpleNamespace(
        project=SimpleNamespace(root=str(tmp_path / "proj"), path=str(tmp_path / "proj"))
    )
    (tmp_path / "proj").mkdir(parents=True, exist_ok=True)
    page = ExpertReviewCampaignPage(session, get_i18n(lang))
    page.retranslate()
    assert page.btn_resume.text()
    assert page.title.text()
    # No blank primary CTA
    assert len(page.btn_resume.text().strip()) > 2
