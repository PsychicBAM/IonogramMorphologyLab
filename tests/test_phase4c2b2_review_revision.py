"""Phase 4C.2b.2 — explicit corrected blind-review revision UX."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.morphology_review_corpus.integrity import validate_cohort
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _page(tmp_path: Path, lang: str = "en"):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
    from ionogram_morphology_lab.ui.expert_review_corpus_page import ExpertReviewCorpusPage
    from ionogram_morphology_lab.ui.session import AppSession

    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    session = AppSession(settings=settings)
    session.project = create_project("Rv4C2B2", language=lang, workspace_parent=tmp_path / "ws")
    session.add_to_inventory(mats[0], make_active=True)
    page = ExpertReviewCorpusPage(session, get_i18n(lang))
    page.retranslate()
    return page, mats[0]


def _snap(cid, it):
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
        candidate_state="frequency_spread_candidate",
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _locked_cohort(page, cid: str = "rev1"):
    store = page._ensure_store()
    assert store is not None
    store.create_cohort(
        items=[{
            "source_sha256": f"{0xCCDDEE01:064x}"[-64:],
            "frame_index": 1,
            "source_display_name": "rev.mat",
            "source_inventory_id": "invrev",
        }],
        sampling_method="manual",
        cohort_id=cid,
    )
    items = store.load_items(cid)
    store.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
    original = BlindReviewRecord.create(
        reviewer_id="r1",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id=cid,
        item_id=items[0].item_id,
        morphology="frequency_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="low",
        confidence="high",
        rationale="original locked",
    )
    store.save_blind_review(cid, original)
    page._cohort_id = cid
    page._load_item(items[0].item_id)
    return store, items[0], original


def test_cancel_creates_no_record(qapp, tmp_path: Path, monkeypatch):
    page, _mat = _page(tmp_path)
    store, item, original = _locked_cohort(page, "cancel")
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    page._begin_corrected_review_revision()
    assert page._pending_review_revision is None
    reviews = store._read_jsonl(store.path_for("cancel") / "blind_reviews.jsonl")
    assert len(reviews) == 1
    assert reviews[0]["review_id"] == original.review_id


def test_correction_requires_reason(qapp, tmp_path: Path, monkeypatch):
    page, _mat = _page(tmp_path)
    _locked_cohort(page, "noreason")
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    warned = []

    def _warn(*a, **k):
        warned.append(a)
        return QMessageBox.Ok

    monkeypatch.setattr(QMessageBox, "warning", _warn)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("   ", True))
    page._begin_corrected_review_revision()
    assert page._pending_review_revision is None
    assert warned


def test_corrected_record_preserves_original(qapp, tmp_path: Path, monkeypatch):
    page, mat = _page(tmp_path)
    store, item, original = _locked_cohort(page, "okrev")
    monkeypatch.setattr(page.ionogram_view, "identity_matches", lambda *a, **k: True)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("fix typo", True))
    monkeypatch.setattr(page, "_ask", lambda *a, **k: True)
    page._begin_corrected_review_revision()
    assert page._pending_review_revision is not None
    # Change morphology in form
    idx = page.morph_combo.findData("range_spread")
    if idx >= 0:
        page.morph_combo.setCurrentIndex(idx)
    page.rationale_edit.setPlainText("corrected rationale")
    page._save_blind()
    rows = store._read_jsonl(store.path_for("okrev") / "blind_reviews.jsonl")
    assert len(rows) == 2
    assert rows[0]["review_id"] == original.review_id
    assert rows[0]["rationale"] == "original locked"
    assert rows[1]["prior_review_id"] == original.review_id
    assert rows[1]["revision_reason"] == "fix typo"
    assert rows[1]["rationale"] == "corrected rationale"
    errors = validate_cohort(store, "okrev")
    assert errors == []


def test_save_without_revision_shows_localized_not_raw(qapp, tmp_path: Path, monkeypatch):
    page, _mat = _page(tmp_path, lang="ru")
    store, item, _orig = _locked_cohort(page, "raw")
    page.ionogram_view._bound_sha = item.source_sha256
    page.ionogram_view._bound_frame = item.frame_index
    seen: list[str] = []

    class _Box(QMessageBox):
        AcceptRole = QMessageBox.AcceptRole
        RejectRole = QMessageBox.RejectRole

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._clicked = None

        def setText(self, t):  # noqa: N802
            seen.append(str(t))
            super().setText(t)

        def exec(self):  # noqa: N802
            return 0

        def clickedButton(self):  # noqa: N802
            return None

    monkeypatch.setattr(
        "ionogram_morphology_lab.ui.expert_review_corpus_page.QMessageBox",
        _Box,
    )
    page._pending_review_revision = None
    page._save_blind()
    assert seen
    assert "revision_reason" not in seen[0]
    assert "Revision of a locked" not in seen[0]
    assert "исправленн" in seen[0].lower() or "зафиксированн" in seen[0].lower()


def test_post_reveal_sets_marker(qapp, tmp_path: Path, monkeypatch):
    page, _mat = _page(tmp_path)
    store, item, original = _locked_cohort(page, "post")
    store.reveal_and_compare("post", item.item_id, review_id=original.review_id)
    monkeypatch.setattr(page.ionogram_view, "identity_matches", lambda *a, **k: True)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("after reveal", True))
    monkeypatch.setattr(page, "_ask", lambda *a, **k: True)
    page._load_item(item.item_id)
    page._begin_corrected_review_revision()
    assert page._pending_review_revision and page._pending_review_revision.get("post_reveal")
    page.rationale_edit.setPlainText("post reveal correction")
    page._save_blind()
    rows = store._read_jsonl(store.path_for("post") / "blind_reviews.jsonl")
    assert len(rows) == 2
    assert rows[-1]["post_reveal_revision"] is True
    assert rows[-1]["revision_reason"] == "after reveal"
