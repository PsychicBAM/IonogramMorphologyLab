"""Viewer jump interval, playback speed, loop, and RU labeling."""

from __future__ import annotations

import pytest


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    import sys

    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def win_ru(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    w = MainWindow(language="ru")
    w.retranslate()
    return w


@pytest.fixture
def win_en(qapp):
    from ionogram_morphology_lab.ui.main_window import MainWindow

    w = MainWindow(language="en")
    w.retranslate()
    return w


def test_jump_interval_has_visible_label_and_unit(win_ru):
    assert "Шаг перехода" in win_ru.jump_label.text()
    assert "мин" in win_ru.jump_unit.text()
    assert win_ru.jump_combo.toolTip()
    assert win_ru.jump_label.accessibleName()


def test_playback_speed_has_visible_label_and_unit(win_ru):
    assert "Скорость воспроизведения" in win_ru.speed_label.text()
    assert "кадр/с" in win_ru.speed_unit.text()
    assert win_ru.speed_combo.toolTip()
    assert win_ru.speed_label.accessibleName()


def test_en_viewer_labels(win_en):
    assert "Jump interval" in win_en.jump_label.text()
    assert "min" in win_en.jump_unit.text()
    assert "Playback speed" in win_en.speed_label.text()
    assert "frames/s" in win_en.speed_unit.text()
    assert "Loop playback" in win_en.loop_chk.text()


def test_loop_renamed_ru(win_ru):
    assert win_ru.loop_chk.text() == "Повторять воспроизведение"
    assert "последнего" in win_ru.loop_chk.toolTip().lower() or "первого" in win_ru.loop_chk.toolTip()


def test_jump_interval_changes_n_behavior(win_ru):
    win_ru._viewer_ready = True
    win_ru._viewer_n_frames = 200
    win_ru.session.current_frame = 50
    win_ru.jump_combo.setCurrentText("10")
    assert win_ru._jump_minutes() == 10
    win_ru.jump_combo.setCurrentText("30")
    assert win_ru._jump_minutes() == 30
    assert win_ru.settings.get("viewer", "navigation_jump_minutes") == 30


def test_playback_speed_changes_timer_interval(win_ru):
    win_ru._viewer_ready = True
    win_ru._viewer_n_frames = 20
    win_ru.session.current_frame = 1
    win_ru.speed_combo.setCurrentText("2")
    assert abs(win_ru._playback_interval_ms() - 500) < 1
    win_ru.speed_combo.setCurrentText("5")
    assert abs(win_ru._playback_interval_ms() - 200) < 1
    assert float(win_ru.settings.get("viewer", "playback_speed")) == 5.0


def test_loop_disabled_stops_at_end(win_ru):
    win_ru._viewer_ready = True
    win_ru._viewer_n_frames = 5
    win_ru.session.current_frame = 5
    win_ru.loop_chk.setChecked(False)
    win_ru._play_timer.start(1000)
    win_ru._playback_tick()
    assert not win_ru._play_timer.isActive()
    assert win_ru.session.current_frame == 5


def test_loop_enabled_wraps_to_beginning(win_ru):
    win_ru._viewer_ready = True
    win_ru._viewer_n_frames = 5
    win_ru.session.current_frame = 5
    win_ru.loop_chk.setChecked(True)
    # Avoid expensive render path
    win_ru.go_to_frame = lambda fid, render=False: setattr(win_ru.session, "current_frame", max(1, min(fid, 5))) or True
    win_ru._playback_tick()
    assert win_ru.session.current_frame == 1


def test_russian_viewer_no_unlabeled_numeric_controls(win_ru):
    """Jump/speed combos must sit next to visible labels — not bare numbers alone."""
    assert win_ru.jump_label.isVisible() or win_ru.jump_label.text()
    assert win_ru.speed_label.isVisible() or win_ru.speed_label.text()
    assert win_ru.jump_label.text().strip()
    assert win_ru.speed_label.text().strip()
    # Combo current texts are numeric by design; labels provide meaning.
    assert win_ru.jump_combo.currentText().isdigit() or win_ru.jump_combo.currentText().replace(".", "", 1).isdigit()
