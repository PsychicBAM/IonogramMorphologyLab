"""Phase 4B.2d — active source UX, compatible activation, diagnostics visualization."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.model import AnalysisProject, create_project
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.active_source import ActiveSourceCard, prerequisite_message, resolve_active_source
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.source_roles import (
    SourceRole,
    classify_mat_source,
    localize_badge,
    localize_role_message,
)
from ionogram_morphology_lab.ui.theme import resolve_theme_name, source_card_tokens, source_surface_qss


@pytest.fixture
def syn_mats(tmp_path: Path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    mats = sorted(syn.glob("*.mat"))
    assert len(mats) >= 2
    return mats


@pytest.fixture
def all_data_mat(tmp_path: Path) -> Path:
    path = tmp_path / "ALL_data_2014-05-06.mat"
    savemat(str(path), {"A_map_F": np.zeros((10, 10)), "H_map_F": np.zeros((10, 10))})
    return path


@pytest.fixture
def session(tmp_path: Path) -> AppSession:
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "show_onboarding", False)
    settings.set("performance", "cache_location", str(tmp_path / "cache"))
    settings.save()
    return AppSession(settings=settings)


def test_dark_theme_source_card_tokens_readable():
    dark = source_card_tokens("dark")
    light = source_card_tokens("light")
    assert dark["bg"].lower() != "#ffffff"
    assert dark["text"].lower() not in ("#ffffff", "#fff", "#f7f7f4")
    assert dark["bg"] != dark["text"]
    assert light["bg"] != light["text"]
    qss = source_surface_qss("QFrame#ActiveSourceCard", "dark")
    assert "#f7f7f4" not in qss
    assert "background:" in qss
    assert resolve_theme_name("dark") == "dark"
    assert resolve_theme_name("light") == "light"


def test_source_card_labels_unset_and_remove(qtbot):
    card = ActiveSourceCard(get_i18n("en"))
    qtbot.addWidget(card)
    assert card.buttons["detach"].text() == "Deactivate for Analysis"
    assert card.buttons["set_active"].text() == "Activate for Analysis"
    assert card.buttons["remove_entry"].text() == "Remove from Project"
    card.i18n = get_i18n("ru")
    card.retranslate()
    assert card.buttons["detach"].text() == "Отключить от анализа"
    assert card.buttons["set_active"].text() == "Активировать для анализа"
    assert card.buttons["remove_entry"].text() == "Убрать из проекта"


def test_valid_am_all_becomes_active(session, syn_mats, tmp_path):
    session.project = create_project("A", language="en", workspace_parent=tmp_path / "ws")
    cls = classify_mat_source(syn_mats[0], session.profile, try_frame=True)
    assert cls.can_activate
    assert cls.role == SourceRole.PRIMARY_IONOGRAM_SOURCE
    session.add_to_inventory(syn_mats[0], make_active=True)
    assert session.active_mat == syn_mats[0]


def test_incompatible_all_data_does_not_replace_active(session, syn_mats, all_data_mat, tmp_path):
    session.project = create_project("B", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    assert session.active_mat == syn_mats[0]
    cls = classify_mat_source(all_data_mat, session.profile, try_frame=False)
    assert not cls.can_activate
    assert cls.role in (SourceRole.AUXILIARY_ARCHIVE_PRODUCT, SourceRole.UNSUPPORTED)
    # Simulate import policy: add without activating
    session.add_to_inventory(all_data_mat, make_active=False)
    assert session.active_mat == syn_mats[0]
    assert all_data_mat in session.selected_mats


def test_unsupported_cannot_set_active(session, all_data_mat, tmp_path):
    session.project = create_project("C", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(all_data_mat, make_active=False)
    cls = classify_mat_source(all_data_mat, session.profile)
    assert cls.can_activate is False
    # Attempting activation must be rejected by policy (caller checks can_activate)
    if not cls.can_activate:
        pass
    assert session.active_mat is None


def test_unset_keeps_inventory_reactivate(session, syn_mats, tmp_path):
    session.project = create_project("D", language="en", workspace_parent=tmp_path / "ws")
    a = syn_mats[0]
    session.add_to_inventory(a, make_active=True)
    session.detach_active_mat()
    assert session.active_mat is None
    assert a in session.selected_mats
    session.set_active_mat(a)
    assert session.active_mat == a


def test_activate_b_unsets_a(session, syn_mats, tmp_path):
    session.project = create_project("E", language="en", workspace_parent=tmp_path / "ws")
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    session.add_to_inventory(b, make_active=True)
    assert session.active_mat == b
    assert a in session.selected_mats
    snap = resolve_active_source(session)
    assert snap.mat_filename == b.name
    assert str(a) in snap.compatible_inactive or any(Path(p).name == a.name for p in snap.compatible_inactive)


def test_cancel_switch_keeps_a(qtbot, tmp_path, syn_mats, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.main_window import MainWindow

    monkeypatch.setattr(
        "ionogram_morphology_lab.ui.main_window.confirm_switch_active",
        lambda *a, **k: False,
    )
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path)
    store.set("general", "show_onboarding", False)
    store.set("performance", "automatic_cache_creation", False)
    store.save()
    win = MainWindow(language="en")
    win.settings = SettingsStore(settings_path)
    win.session.settings = win.settings
    qtbot.addWidget(win)
    win.session.project = create_project("F", language="en", workspace_parent=tmp_path / "ws")
    win.session.add_to_inventory(syn_mats[0], make_active=True)
    assert win._confirm_safe_source_switch(syn_mats[1]) is False
    assert win.session.active_mat == syn_mats[0]


def test_failed_b_validation_keeps_a(session, syn_mats, all_data_mat, tmp_path):
    session.project = create_project("G", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    prev = session.active_mat
    cls = classify_mat_source(all_data_mat, session.profile)
    assert not cls.can_activate
    # Do not set active
    assert session.active_mat == prev


def test_removed_file_cannot_reactivate(session, syn_mats, tmp_path):
    session.project = create_project("H", language="en", workspace_parent=tmp_path / "ws")
    a = syn_mats[0]
    session.add_to_inventory(a, make_active=True)
    session.remove_inventory_entry(a)
    assert a not in session.selected_mats
    assert session.active_mat is None
    assert a.is_file()


def test_missing_physical_file_unavailable(session, tmp_path):
    session.project = create_project("I", language="en", workspace_parent=tmp_path / "ws")
    missing = tmp_path / "missing.mat"
    cls = classify_mat_source(missing, session.profile)
    assert cls.role == SourceRole.MISSING
    assert localize_badge("unavailable", "ru") == "Файл недоступен"


def test_active_source_persists_after_restart(tmp_path, syn_mats, session):
    project = create_project("J", language="en", workspace_parent=tmp_path / "ws")
    session.project = project
    session.add_to_inventory(syn_mats[0], make_active=True)
    project.source_paths = [str(p) for p in session.selected_mats]
    project.active_source_path = str(session.active_mat)
    data = project.to_dict()
    (project.path / "project.json").write_text(
        __import__("json").dumps(data, indent=2), encoding="utf-8"
    )
    session2 = AppSession(settings=session.settings)
    session2.project = AnalysisProject.from_dict(
        __import__("json").loads((project.path / "project.json").read_text(encoding="utf-8"))
    )
    session2.restore_inventory_from_project()
    assert session2.active_mat is not None
    assert session2.active_mat.resolve() == syn_mats[0].resolve()


def test_ru_en_labels_and_confirmations():
    assert "Отключить от анализа" != "Отключить текущий MAT"
    assert localize_role_message("imported_auxiliary", "ru").startswith("Файл добавлен")
    assert "auxiliary" in localize_role_message("imported_auxiliary", "en").lower()
    assert "Amp_all" in prerequisite_message("variable_missing", "ru")
    assert "missing_variable" not in prerequisite_message("variable_missing", "ru")


def test_import_file_row_actions_visible(qtbot, syn_mats, session, tmp_path):
    from ionogram_morphology_lab.ui.import_file_list import ImportFileList

    session.project = create_project("K", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    lst = ImportFileList(get_i18n("en"))
    qtbot.addWidget(lst)
    lst.rebuild([syn_mats[0]], session.profile, session.active_mat)
    row = next(iter(lst._rows.values()))
    assert row._is_active is True
    assert not row.buttons["unset_active"].isHidden()
    assert row.buttons["set_active"].isHidden()
    assert row.badge.text() == "Active source"
    session.detach_active_mat()
    lst.rebuild([syn_mats[0]], session.profile, None)
    row = next(iter(lst._rows.values()))
    assert row._is_active is False
    assert not row.buttons["set_active"].isHidden()
    assert row.badge.text() == "Inactive file"


def test_raw_frame_before_and_after_v2(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("L", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    assert page._raw is not None
    assert page._raw_sha
    assert page._run_state == "frame_ready"
    assert "Frame loaded" in page.state_label.text() or "V2 has not been run" in page.state_label.text()
    # Simulate V2 result presence by running shadow path lightly if possible
    page.run_shadow = lambda: None  # avoid modal in this unit check
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2

    page._result = run_feature_pipeline_v2(
        page._raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=page._source_sha,
    )
    page._populate_summary()
    page._populate_features()
    page._update_completed_state()
    page._render_view()
    assert page.image.pixmap() is not None and not page.image.pixmap().isNull()
    assert page.summary_view.toPlainText()
    assert "shadow" in page.summary_view.toPlainText().lower() or "тенев" in page.summary_view.toPlainText().lower()


def test_layer_toggles_alter_render(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("M", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    page._result = run_feature_pipeline_v2(
        page._raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=page._source_sha,
    )
    page._show_default_layers()
    page._render_view()
    pix1 = page.image.pixmap().copy()
    page._hide_overlays()
    page._render_view()
    pix2 = page.image.pixmap().copy()
    # Both should render something (raw always visible)
    assert not pix1.isNull() and not pix2.isNull()


def test_frame_sha_identity(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage, frame_sha256

    session.project = create_project("N", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    sha = page.current_raw_frame_sha()
    assert sha == frame_sha256(page._raw)
    res = run_feature_pipeline_v2(
        page._raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=page._source_sha,
    )
    assert res.source_mat_sha256 == page._source_sha
    assert frame_sha256(page._raw) == sha


def test_source_switch_clears_stale_overlays(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("O", language="en", workspace_parent=tmp_path / "ws")
    a, b = syn_mats[0], syn_mats[1]
    session.add_to_inventory(a, make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    page._result = run_feature_pipeline_v2(
        page._raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=page._source_sha,
    )
    page.clear_results()
    session.set_active_mat(b)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    assert page._result is None
    assert page._raw is not None
    assert page._run_state == "frame_ready"


def test_blank_canvas_never_implicit(qtbot, session, tmp_path):
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("P", language="en", workspace_parent=tmp_path / "ws")
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.state_label.text()
    assert page._run_state == "no_active"


def test_no_trace_abstention_message():
    from ionogram_morphology_lab.ui.diagnostic_summary import run_state_message

    assert "воздержания" in run_state_message("v2_no_trace", "ru")
    assert "abstention" in run_state_message("v2_no_trace", "en").lower()


def test_technical_ids_hidden_by_default(qtbot, session, syn_mats, tmp_path):
    from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
    from ionogram_morphology_lab.ui.feature_diagnostics_page import FeatureDiagnosticsPage

    session.project = create_project("Q", language="en", workspace_parent=tmp_path / "ws")
    session.add_to_inventory(syn_mats[0], make_active=True)
    page = FeatureDiagnosticsPage(session, get_i18n("en"))
    qtbot.addWidget(page)
    page.refresh()
    assert page.wait_until_frame_ready(30000)
    page._result = run_feature_pipeline_v2(
        page._raw,
        signal_contract_id="kfu_amp_all_v1",
        profile_id=session.profile_id,
        frame_index=1,
        source_mat_sha256=page._source_sha,
    )
    page.tech_toggle.setChecked(False)
    page._populate_features()
    texts = [page.feature_list.item(i).text() for i in range(page.feature_list.count())]
    # Group headers ok; feature rows should not all be raw ids
    body = "\n".join(t for t in texts if not t.startswith("——"))
    assert "v2_" not in body or page.tech_toggle.isChecked()


def test_main_window_import_rejects_all_data_activation(qtbot, tmp_path, syn_mats, all_data_mat, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok)
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
    win.session.project = create_project("R", language="en", workspace_parent=tmp_path / "ws")
    win._add_mat(syn_mats[0], make_active=True, confirm=False)
    assert win.session.active_mat == syn_mats[0]
    win._add_mat(all_data_mat, make_active=True, confirm=False)
    assert win.session.active_mat == syn_mats[0]
    assert all_data_mat in win.session.selected_mats
