from __future__ import annotations

import hashlib

from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS, SettingsStore
from ionogram_morphology_lab.ui.matlab_studio_page import (
    MATLAB_TRUST_WARNING,
    file_sha256,
    requires_trust_confirmation,
)


def test_file_sha256(tmp_path):
    script = tmp_path / "method.m"
    script.write_bytes(b"disp('trusted only')\n")
    assert file_sha256(script) == hashlib.sha256(script.read_bytes()).hexdigest()


def test_only_builtin_source_with_builtin_trust_skips_confirmation():
    assert requires_trust_confirmation("builtin", "builtin") is False
    assert requires_trust_confirmation("imported", "user") is True
    assert requires_trust_confirmation("user_copy", "user_tested") is True
    assert requires_trust_confirmation("rule_pack", "builtin") is True


def test_warning_text_and_settings_defaults(tmp_path):
    assert MATLAB_TRUST_WARNING == (
        "MATLAB scripts run with your operating-system user permissions. Only run scripts you trust."
    )
    assert DEFAULT_SETTINGS["matlab"]["first_trust_warning_ack"] is False
    assert DEFAULT_SETTINGS["matlab"]["builtin_trust_acknowledged"] is False
    settings = SettingsStore(tmp_path / "settings.json")
    assert settings.get("matlab", "first_trust_warning_ack") is False
    assert settings.get("matlab", "builtin_trust_acknowledged") is False
