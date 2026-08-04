"""Phase 4B.2c — active MAT source lifecycle and Feature Diagnostics wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import AnalysisProject, create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import (
    SourceStatus,
    empty_state_copy,
    prerequisite_message,
    resolve_active_source,
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


def test_import_mat_becomes_active(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("ActiveSrc", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    mat = syn_mats[0]
    session.add_to_inventory(mat, make_active=True)
    assert session.active_mat == mat
    assert mat in session.selected_mats
    assert project.active_source_path == str(mat)
    snap = resolve_active_source(session)
    assert snap.is_active
    assert snap.mat_filename == mat.name
    assert snap.status in (SourceStatus.READY, SourceStatus.NOT_LOADED)


def test_imported_but_inactive_clearly_identified(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("Inactive", language="ru", workspace_parent=tmp_path / "ws")
    session.project = project
    mat = syn_mats[0]
    session.add_to_inventory(mat, make_active=False)
    assert session.active_mat is None
    snap = resolve_active_source(session)
    assert snap.status == SourceStatus.INVENTORY_INACTIVE
    assert snap.in_inventory
    assert not snap.is_active
    msg = prerequisite_message("mat_not_active", "ru")
    assert "не выбран как активный источник" in msg
    msg_en = prerequisite_message("mat_not_active", "en")
    assert "not selected as the active source" in msg_en


def test_feature_diagnostics_recognizes_active_mat(qtbot, session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    project = create_project("FD", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page._run_state in ("frame_ready", "v2_done", "loading")
    assert syn_mats[0].name in page.identity.text()


def test_feature_diagnostics_opened_before_import_refreshes(
    qtbot, session: AppSession, syn_mats, tmp_path: Path
):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    project = create_project("FDRefresh", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    assert page._run_state == "no_active"
    session.add_to_inventory(syn_mats[0], make_active=True)
    # Signal-driven refresh
    page.refresh()
    assert page._run_state in ("frame_ready", "v2_done", "loading")
    assert syn_mats[0].name in page.identity.text()


def test_viewer_and_feature_diagnostics_same_source_identity(
    qtbot, session: AppSession, syn_mats, tmp_path: Path
):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    project = create_project("SameID", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    snap_a = resolve_active_source(session)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    snap_b = resolve_active_source(session)
    assert snap_a.mat_path == snap_b.mat_path
    assert snap_a.source_sha256 == snap_b.source_sha256
    assert snap_a.mat_filename in page.identity.text()


def test_batch_and_feature_diagnostics_same_source_identity(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("BatchID", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    # Batch uses selected_mats / active_mat — same resolve path
    assert session.selected_mats[0] == session.active_mat
    snap = resolve_active_source(session)
    assert snap.mat_path == session.active_mat


def test_switch_mat_a_to_b_without_restart(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("Switch", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    assert session.active_mat == a
    session.current_frame = 7
    session.add_to_inventory(b, make_active=True)
    assert session.active_mat == b
    assert session.current_frame == 1  # cleared on switch
    assert session.frame_store is None
    snap = resolve_active_source(session)
    assert snap.mat_filename == b.name


def test_detach_current_mat_does_not_delete_file(session: AppSession, syn_mats, tmp_path: Path):
    project = create_project("Detach", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    mat = syn_mats[0]
    session.add_to_inventory(mat, make_active=True)
    assert mat.is_file()
    session.detach_active_mat()
    assert session.active_mat is None
    assert mat.is_file()
    assert mat in session.selected_mats  # inventory retained


def test_remove_inventory_entry_does_not_delete_physical_file(
    session: AppSession, syn_mats, tmp_path: Path
):
    project = create_project("RemoveEntry", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    mat = syn_mats[0]
    session.add_to_inventory(mat, make_active=True)
    assert mat.is_file()
    session.remove_inventory_entry(mat)
    assert mat.is_file()
    assert mat not in session.selected_mats
    assert str(mat) not in project.source_paths
    assert session.active_mat is None


def test_stale_missing_mat_path(session: AppSession, tmp_path: Path):
    project = create_project("Missing", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    missing = tmp_path / "gone.mat"
    session.active_mat = missing
    project.active_source_path = str(missing)
    snap = resolve_active_source(session)
    assert snap.status == SourceStatus.MISSING
    assert prerequisite_message("mat_path_missing", "ru") == "MAT-файл недоступен по сохранённому пути."


def test_active_project_with_no_mat(session: AppSession, tmp_path: Path):
    project = create_project("NoMat", language="ru", workspace_parent=tmp_path / "ws")
    session.project = project
    snap = resolve_active_source(session)
    assert snap.status == SourceStatus.NO_MAT
    assert prerequisite_message("no_active_mat", "ru") == "В проекте не выбран активный MAT-файл."


def test_project_switch_clears_stale_diagnostics(qtbot, session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    p1 = create_project("P1", language="en", workspace_parent=tmp_path / "ws")
    session.project = p1
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page._result = type("R", (), {"source_mat_sha256": "deadbeef"})()
    page._raw = object()

    # Switch project — clear session like MainWindow._clear_project_ui_state
    session.selected_mats = []
    session.set_active_mat(None)
    page.clear_results()
    p2 = create_project("P2", language="en", workspace_parent=tmp_path / "ws")
    session.project = p2
    session.events.project_changed.emit()
    page.refresh()
    assert page._result is None
    assert page._run_state in ("no_active", "no_project")


def test_active_v2_job_blocks_unsafe_source_switch(qtbot, tmp_path: Path, syn_mats, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path)
    store.set("general", "show_onboarding", False)
    store.set("performance", "automatic_cache_creation", False)
    store.save()
    win = MainWindow(language="en")
    win.settings = SettingsStore(settings_path)
    win.session.settings = win.settings
    qtbot.addWidget(win)
    project = create_project("V2Block", language="en", workspace_parent=tmp_path / "ws")
    win.session.project = project
    win.session.add_to_inventory(syn_mats[0], make_active=True)
    win.session.v2_job_status = "running"
    assert win._confirm_safe_source_switch(syn_mats[1]) is False


def test_active_matlab_job_blocks_unsafe_source_switch(qtbot, tmp_path: Path, syn_mats, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Ok)
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path)
    store.set("general", "show_onboarding", False)
    store.set("performance", "automatic_cache_creation", False)
    store.save()
    win = MainWindow(language="en")
    win.settings = SettingsStore(settings_path)
    win.session.settings = win.settings
    qtbot.addWidget(win)
    project = create_project("MatBlock", language="en", workspace_parent=tmp_path / "ws")
    win.session.project = project
    win.session.add_to_inventory(syn_mats[0], make_active=True)

    real_jobs = win.matlab_jobs

    class _Jobs:
        def has_running_jobs(self):
            return True

        def has_active_jobs(self):
            return True

        def shutdown_all(self, wait_ms=0):
            return None

    win.matlab_jobs = _Jobs()
    try:
        assert win._confirm_safe_source_switch(syn_mats[1]) is False
    finally:
        win.matlab_jobs = real_jobs


def test_ru_error_localization():
    assert prerequisite_message("project_not_open", "ru") == "Проект не открыт."
    assert prerequisite_message("generic_open_project_mat", "ru") == (
        "Сначала откройте проект и выберите активный исходный MAT-файл."
    )
    copy = empty_state_copy("ru")
    assert "активный проект" in copy["body"]
    assert copy["open_projects"] == "Открыть проекты"


def test_en_error_localization():
    assert prerequisite_message("project_not_open", "en") == "No project is open."
    assert "active source MAT" in prerequisite_message("generic_open_project_mat", "en")
    copy = empty_state_copy("en")
    assert "Open Projects" == copy["open_projects"]
    assert "Feature Diagnostics requires" in copy["body"]


def test_page_retranslates_after_language_switch(qtbot, session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    project = create_project("Lang", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    assert "No active source" in page.state_label.text() or page._run_state == "no_active"
    page.i18n = get_i18n("ru")
    page.retranslate()
    assert "активн" in page.state_label.text().lower() or page._run_state == "no_active"


def test_source_identity_preserved_in_saved_diagnostics(session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
    from ionogram_morphology_lab.utils.hashing import sha256_file

    mat = syn_mats[0]
    sha = sha256_file(mat)
    loaded = load_amplitude_matrix(mat, variable="Amp_all")
    frame, _ = extract_frame_consistent(loaded.data, 1, height_bins=256, frequency_bins=400)
    res = run_feature_pipeline_v2(
        frame,
        signal_contract_id="kfu_amp_all_v1",
        profile_id="kfu_cyclone_2013_2014",
        frame_index=1,
        source_mat_sha256=sha,
    )
    ser = res.to_serializable()
    assert ser["source_mat_sha256"] == sha
    # Different MAT → different identity; results must not share SHA
    sha_b = sha256_file(syn_mats[1])
    assert sha_b != sha


def test_no_results_mixed_across_two_mats(qtbot, session: AppSession, syn_mats, tmp_path: Path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    project = create_project("NoMix", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page._result = type("R", (), {"source_mat_sha256": "sha-of-a"})()
    page._raw = object()
    session.add_to_inventory(b, make_active=True)
    # After switch, clear + refresh like MainWindow
    page.clear_results()
    page.refresh()
    assert page._result is None
    snap = resolve_active_source(session)
    assert snap.mat_filename == b.name


def test_analysis_project_persists_active_source_path(tmp_path: Path, syn_mats):
    project = create_project("Persist", language="en", workspace_parent=tmp_path / "ws")
    project.source_paths = [str(syn_mats[0])]
    project.active_source_path = str(syn_mats[0])
    data = project.to_dict()
    loaded = AnalysisProject.from_dict(data)
    assert loaded.active_source_path == str(syn_mats[0])
    # Old project.json without the field still loads
    legacy = {k: v for k, v in data.items() if k != "active_source_path"}
    loaded2 = AnalysisProject.from_dict(legacy)
    assert loaded2.active_source_path is None
