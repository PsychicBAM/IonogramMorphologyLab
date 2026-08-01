from __future__ import annotations

import json
from pathlib import Path

from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.ui import main_window


def test_main_window_has_no_toolbar_language_switcher():
    source = Path(main_window.__file__).read_text(encoding="utf-8")
    assert "act_lang_en" not in source
    assert 'setText("EN")' not in source
    assert 'setText("RU")' not in source


def test_i18n_keys_match_and_include_interface_language():
    i18n_root = Path(main_window.__file__).parents[1] / "i18n"
    en = json.loads((i18n_root / "en.json").read_text(encoding="utf-8"))
    ru = json.loads((i18n_root / "ru.json").read_text(encoding="utf-8"))
    assert set(en) == set(ru)
    assert "settings.interface_language" in en


def test_interface_language_setting_persists(tmp_path):
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("general", "language", "ru")
    settings.save()
    assert SettingsStore(tmp_path / "settings.json").get("general", "language") == "ru"
