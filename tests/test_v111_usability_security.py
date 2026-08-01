"""v1.1.1 usability, help search, pack safety, and settings tests."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.app.settings_store import SettingsStore
from ionogram_morphology_lab.help.content import search_help
from ionogram_morphology_lab.reports.export_reports import _md_to_simple_html
from ionogram_morphology_lab.rule_builder.examples import (
    builtin_examples,
    copy_example_to_draft,
)
from ionogram_morphology_lab.rule_builder.nl_preview import preview_rule
from ionogram_morphology_lab.rule_builder.packs import import_pack
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.ui.workflow import evaluate_workflow, next_recommended_step


def _empty_session(tmp_path: Path) -> AppSession:
    settings = SettingsStore(tmp_path / "settings.json")
    return AppSession(settings=settings, project=None)


def test_workflow_no_project_current_step_is_project(tmp_path):
    session = _empty_session(tmp_path)
    steps = evaluate_workflow(session)
    project = next(s for s in steps if s.step_id == "project")
    assert project.status == "current"
    nxt = next_recommended_step(session)
    assert nxt.step_id == "project"
    assert nxt.status == "current"


def test_builtin_examples_count_and_copy_isolation():
    examples = builtin_examples()
    assert len(examples) == 8
    original = examples[0]
    orig_id = original.rule_id
    orig_enabled = original.enabled
    draft = copy_example_to_draft(original, new_id="USER_COPY_TEST")
    assert draft.rule_id == "USER_COPY_TEST"
    assert draft.rule_id != orig_id
    assert original.rule_id == orig_id
    assert original.enabled == orig_enabled
    assert draft.metadata.get("copied_from_example") == orig_id


def test_preview_rule_contains_proposed_result_en_and_ru():
    rule = builtin_examples()[0]
    en = preview_rule(rule, "en")
    ru = preview_rule(rule, "ru")
    assert rule.proposed_result in en
    assert rule.proposed_result in ru


def test_search_help_svoyo_pravilo():
    hits = search_help("своё правило", lang="ru")
    ids = {h["id"] for h in hits}
    assert "rules_nocode" in ids or any("rule" in i for i in ids)


def test_search_help_medlenno():
    hits = search_help("медленно", lang="ru")
    ids = {h["id"] for h in hits}
    assert "cache" in ids or "performance" in ids


def test_search_help_ox_ambiguity():
    hits = search_help("O/X", lang="en")
    ids = {h["id"] for h in hits}
    assert "ox" in ids or "ambiguity" in ids or any("ox" in i for i in ids)


def _minimal_pack_zip(tmp_path: Path, archive_name: str, inner_path: str) -> Path:
    archive = tmp_path / archive_name
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(inner_path, "pack_id: test\nversion: 0.0.1\n")
        z.writestr("rules/r001.yaml", "rule_id: R001\n")
    return archive


def test_import_pack_rejects_path_traversal(tmp_path):
    archive = _minimal_pack_zip(tmp_path, "bad.zip", "../pack.yaml")
    result = import_pack(archive)
    assert result.ok is False
    assert any(".." in e or "Unsafe" in e or "traversal" in e for e in result.errors)


def test_import_pack_rejects_windows_drive_path(tmp_path):
    archive = _minimal_pack_zip(tmp_path, "drive.zip", "C:/pack.yaml")
    result = import_pack(archive)
    assert result.ok is False
    assert any(
        "drive" in e.lower() or "unsafe" in e.lower() or "absolute" in e.lower()
        for e in result.errors
    )


def test_md_to_simple_html_escapes_script():
    md = "# Title\n<script>alert(1)</script>\n- <b>x</b>"
    html = _md_to_simple_html(md, "en")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_settings_default_guided_ux_and_ux_does_not_change_analysis_mode(tmp_path):
    settings = SettingsStore(tmp_path / "settings.json")
    assert settings.get("ux", "interface_mode") == "guided"
    settings.set("analysis", "mode", "fast_preview")
    settings.save()
    before = settings.analysis_mode()
    settings.set("ux", "interface_mode", "expert")
    settings.save()
    reloaded = SettingsStore(tmp_path / "settings.json")
    assert reloaded.get("ux", "interface_mode") == "expert"
    assert reloaded.analysis_mode() == before == "fast_preview"


def test_version_is_1_1_1():
    assert __version__ == "1.1.1"
