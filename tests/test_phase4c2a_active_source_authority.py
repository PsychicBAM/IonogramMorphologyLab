"""Phase 4C.2a — authoritative active source; Batch never falls back to first MAT."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source_authority import (
    active_source_label,
    authoritative_active_source,
    batch_mats_from_active,
    freeze_batch_source_snapshot,
)
from ionogram_morphology_lab.ui.session import AppSession


@pytest.fixture
def syn_mats(tmp_path: Path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    assert len(mats) >= 2
    return mats


@pytest.fixture
def session(tmp_path: Path) -> AppSession:
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    return AppSession(settings=settings)


def test_two_source_batch_uses_only_active_b(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("TwoSrc", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    session.add_to_inventory(b, make_active=True)
    assert session.active_mat == b
    mats, err = batch_mats_from_active(session)
    assert err == ""
    assert mats == [b]
    assert a not in mats
    auth = authoritative_active_source(session)
    assert auth.display_name == b.name
    assert auth.is_active and auth.available


def test_batch_blocks_when_no_active_despite_inventory(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("NoActive", language="ru", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=False)
    session.add_to_inventory(syn_mats[1], make_active=False)
    mats, err = batch_mats_from_active(session)
    assert mats == []
    assert err == "active_source_required"


def test_restore_missing_active_does_not_pick_first(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("Restore", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=False)
    session.add_to_inventory(b, make_active=True)
    project.source_paths = [str(a), str(b)]
    project.active_source_path = str(tmp_path / "missing_2014.mat")
    session2 = AppSession(settings=session.settings)
    session2.project = project
    session2.restore_inventory_from_project()
    assert session2.active_mat is None
    assert a in session2.selected_mats or Path(str(a)) in session2.selected_mats
    mats, err = batch_mats_from_active(session2)
    assert mats == []
    assert err in ("active_source_required", "mat_not_active")


def test_switch_a_to_b_updates_authority(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("SwitchAuth", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    rev1 = authoritative_active_source(session).activation_revision
    session.add_to_inventory(b, make_active=True)
    auth = authoritative_active_source(session)
    assert auth.display_name == b.name
    assert auth.activation_revision >= rev1
    mats, _ = batch_mats_from_active(session)
    assert mats == [b]


def test_active_source_label_ru_en(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("Lbl", language="ru", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    auth = authoritative_active_source(session)
    ru = active_source_label(auth, "ru")
    en = active_source_label(auth, "en")
    assert "Активный источник" in ru
    assert "Active source" in en
    assert "доступен" in ru or "недоступен" in ru


def test_frozen_batch_snapshot_identity(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("FreezeBatch", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    frozen = freeze_batch_source_snapshot(session)
    assert frozen["display_name"] == syn_mats[0].name
    assert "activation_revision" in frozen


def test_viewer_ensure_store_resolves_active_b(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("ViewerB", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    session.add_to_inventory(b, make_active=True)
    store = session.ensure_store()
    from ionogram_morphology_lab.ui.active_source import paths_equal

    assert paths_equal(store.source_path, b)


def test_diagnostics_resolve_active_b(session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.active_source import resolve_active_source

    project = create_project("FDB", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    session.add_to_inventory(b, make_active=True)
    snap = resolve_active_source(session)
    assert snap.mat_filename == b.name
    assert snap.is_active
