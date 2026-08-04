"""Acceptance tests for product simplification (classification, i18n, nav, batch, storage, icon)."""

from __future__ import annotations

import struct

import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.i18n import get_i18n
from ionogram_morphology_lab.projects.batch_selection import (
    select_frame_range,
    select_full_day,
    select_time_range,
)
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.scientific_outputs.result_schema import normalize_morphology
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.ui.presenters import morphology_label
from ionogram_morphology_lab.utils.paths import app_root

FORBIDDEN_RU_UI_TOKENS = [
    "profile_dependent",
    "source_disabled",
    "build_cache",
    "export_reports",
    "full_pipeline",
    "day_interval",
    "Frequency axis",
    "Range axis",
    "Time mapping",
    "no_visible_ambiguity",
    "uncalibrated",
]


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys

    return QApplication.instance() or QApplication(sys.argv)


def test_clean_trace_not_automatic_mixed():
    feats = extract_features(generate_synthetic_case("smooth_trace")).values
    res = RuleEngine().evaluate(feats)
    assert normalize_morphology(res.candidate_morphology) == "clean"
    assert res.candidate_morphology != "mixed"
    assert res.activated_rules


def test_mixed_requires_both_axes_and_trace():
    feats = extract_features(generate_synthetic_case("mixed_diffuse")).values
    res = RuleEngine().evaluate(feats)
    if res.candidate_morphology == "mixed":
        assert feats["frequency_evidence_absolute"] >= 1.0
        assert feats["range_evidence_absolute"] >= 1.0
        assert feats["colocated_spread_fraction"] >= 0.20


def test_result_display_localized_not_raw_token():
    assert morphology_label("clean", "ru") == "Явное рассеяние не обнаружено"
    assert morphology_label("mixed_spread", "ru") == "Возможно смешанное F-рассеяние"
    assert morphology_label("frequency_spread", "en") == "Possible frequency F-spread"
    assert morphology_label("diffuse_unspecified", "ru") == (
        "Наблюдается диффузная структура, тип не определён"
    )
    assert morphology_label("interference_dominated", "ru") == "Оценка ограничена помехами"
    assert normalize_morphology("none") == "clean"
    assert normalize_morphology("diffuse") == "diffuse_unspecified"


def _collect_visible_strings(win) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton, QCheckBox, QGroupBox, QTabWidget

    texts: list[str] = []
    for i in range(win.nav.topLevelItemCount()):
        item = win.nav.topLevelItem(i)
        texts.append(item.text(0))
        for j in range(item.childCount()):
            texts.append(item.child(j).text(0))
    for action in win.actions.values():
        texts.append(action.text())
    for cls in (QLabel, QPushButton, QCheckBox, QGroupBox):
        for w in win.findChildren(cls):
            try:
                texts.append(w.text())
            except Exception:  # noqa: BLE001
                pass
    tabs = win.findChildren(QTabWidget)
    for tab in tabs:
        for i in range(tab.count()):
            texts.append(tab.tabText(i))
    return "\n".join(t for t in texts if t)


def test_russian_main_pages_hide_forbidden_tokens(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="ru")
    win.retranslate()
    blob = _collect_visible_strings(win)
    for token in FORBIDDEN_RU_UI_TOKENS:
        assert token not in blob, f"Untranslated token visible in RU UI: {token}"
    # Top-bar language status indicator must be gone (Settings may still label the language combo).
    assert "Язык интерфейса: ru" not in blob
    assert "Interface language: en" not in blob
    assert not hasattr(win, "lang_indicator")


def test_guided_mode_hides_expert_methods(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    win.settings.set("ux", "interface_mode", "guided")
    win._apply_ux_mode()
    assert win.nav_items["models"].isHidden()
    assert win.nav_items["pipeline"].isHidden()
    assert not win.nav_items["batch"].isHidden()
    win.settings.set("ux", "interface_mode", "expert")
    win._apply_ux_mode()
    assert not win.nav_items["models"].isHidden()


def test_nav_group_expand_persists(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    group = win.nav_groups["methods"]
    group.setExpanded(False)
    win._save_nav_group_state(group)
    saved = win.settings.get("ux", "nav_groups_expanded", {})
    assert saved.get("methods") is False


def test_batch_selection_modes_frame_counts():
    n = 1440
    assert len(select_frame_range(1, 10, 1, n).frame_ids) == 10
    assert len(select_frame_range(1, 10, 2, n).frame_ids) == 5
    every = select_full_day(10, n)
    assert every.frame_ids[0] == 1
    assert every.frame_ids[1] - every.frame_ids[0] == 10
    tr = select_time_range("05:00", "07:00", 10, n)
    assert tr.frame_ids
    assert tr.frame_ids[0] <= tr.frame_ids[-1]


def test_batch_start_disabled_without_project(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    win = MainWindow(language="en")
    win.session.project = None
    win.session.selected_mats = []
    win._refresh_batch_preview()
    assert win.btn_batch_start.isEnabled() is False


def test_storage_paths_cyrillic_spaces(tmp_path):
    cyr = tmp_path / "Проекты IML" / "кэш data"
    cyr.mkdir(parents=True)
    store = SettingsStore(tmp_path / "settings.json")
    store.set("performance", "cache_location", str(cyr))
    store.save()
    assert store.cache_dir().exists()
    assert "Проекты" in str(store.cache_dir()) or store.cache_dir() == cyr.resolve()


def test_cache_cleanup_never_deletes_source_mat(tmp_path, qapp, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from ionogram_morphology_lab.ui.main_window import MainWindow

    mat_outside = tmp_path / "source.mat"
    mat_outside.write_bytes(b"MAT-outside")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "derived.bin").write_bytes(b"x")
    mat_inside = cache / "accidentally.mat"
    mat_inside.write_bytes(b"MAT-inside")

    win = MainWindow(language="en")
    win.settings.set("performance", "cache_location", str(cache))
    win.settings.save()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok)
    win._clear_cache()

    assert mat_outside.exists()
    assert mat_outside.read_bytes() == b"MAT-outside"
    assert mat_inside.exists(), "MAT under cache must still be preserved"
    assert not (cache / "derived.bin").exists()


def test_icon_embedded_assets_present():
    ico = app_root() / "assets" / "IonogramMorphologyLab.ico"
    assert ico.exists()
    data = ico.read_bytes()
    assert len(data) > 1000
    reserved, itype, count = struct.unpack_from("<HHH", data, 0)
    assert reserved == 0 and itype == 1 and count >= 7


def test_shortcut_script_points_to_exe_or_module():
    script = (app_root() / "scripts" / "create_desktop_shortcut.ps1").read_text(encoding="utf-8")
    assert "IonogramMorphologyLab.exe" in script
    assert "Desktop" in script


def test_parameter_status_i18n_localized():
    ru = get_i18n("ru")
    assert "профил" in ru.t("params.state_profile").lower()
    assert "источник" in ru.t("params.state_disabled").lower()
    assert ru.t("params.state.unavailable") == "Недоступно"
    assert "эксперт" in ru.t("params.state.pending").lower()
    for key in (
        "params.state_profile",
        "params.state_disabled",
        "params.state.unavailable",
        "params.state.pending",
    ):
        assert "profile_dependent" not in ru.t(key)
        assert "source_disabled" not in ru.t(key)
