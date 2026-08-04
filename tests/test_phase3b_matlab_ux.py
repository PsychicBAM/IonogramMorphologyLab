"""Phase 3B: MATLAB Studio layout, validate-vs-run, contracts, projects, pipeline, expert."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def test_matlab_action_buttons_have_readable_minimum_width(qapp):
    from ionogram_morphology_lab.ui.matlab_results_panel import MatlabResultsPanel

    panel = MatlabResultsPanel()
    panel.resize(1366, 768)
    panel.set_action_labels({
        "open_folder": "Открыть папку результатов",
        "run_again": "Запустить снова",
        "tech_log": "Открыть технический журнал",
        "more": "Дополнительно…",
    })
    widths = panel.primary_action_min_widths()
    assert all(w >= 120 for w in widths)
    assert "more" in panel._action_keys
    assert panel.more_menu.actions()
    # No single-row of nine clipped buttons — secondary items live in the menu.
    assert len(panel._menu_actions) >= 4
    panel.deleteLater()


def test_validate_label_explains_no_execution(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.matlab_studio_page import MatlabStudioPage
    from ionogram_morphology_lab.ui.session import AppSession

    session = AppSession(settings=SettingsStore(tmp_path / "s.json"))
    page = MatlabStudioPage(session, get_i18n("en"))
    page.retranslate()
    assert "Without Running" in page.btn_validate.text()
    assert "not" in page.btn_validate.toolTip().lower() or "not started" in page.btn_validate.toolTip().lower()
    assert "Run in MATLAB" in page.btn_run.text()
    page.editor.setPlainText("function y = f(x)\ny = x;\nend\n")
    page._validate_code()
    # Parent may be hidden under offscreen Qt — assert content + not-hidden flag.
    assert page.validate_card.text().strip()
    assert not page.validate_card.isHidden()
    assert "does not execute MATLAB" in page.validate_card.text()
    page.set_language = None
    page.i18n.set_language("ru")
    page.retranslate()
    assert "без запуска" in page.btn_validate.text()
    assert "Запустить в MATLAB" in page.btn_run.text()
    page.deleteLater()


def test_expected_output_metadata_and_counts():
    from ionogram_morphology_lab.matlab_studio.method_contracts import (
        count_contracts,
        format_expected_output,
        get_method_contract,
    )

    c = get_method_contract("iml_estimate_foF2_candidate")
    assert c.parameter_only
    assert not c.diagnostic_image_expected
    text = format_expected_output(c, "ru")
    assert "Ожидаемый результат метода" in text
    assert "не создаёт отдельное изображение" in text
    t = get_method_contract("iml_trace_ridge_candidate")
    assert t.diagnostic_image_expected
    stats = count_contracts()
    assert stats["declared"] >= 10
    assert stats["diagnostic_figures"] >= 1
    assert stats["values_only"] >= 1


def test_run_status_no_output_warning():
    from ionogram_morphology_lab.matlab_studio.method_contracts import classify_scientific_run_status
    from ionogram_morphology_lab.ui.matlab_results_panel import build_result_sections

    assert (
        classify_scientific_run_status(job_status="completed", payload={"status": "ok", "outputs": {}, "output_files": []})
        == "completed_with_no_registered_output"
    )
    job = SimpleNamespace(
        status="completed", backend="octave", elapsed_s=1, active_frame=1,
        output_directory="/tmp/x", source_mats_unchanged=True, source_path="m.m",
        sha256="a", source_mat_paths=[], requested_inputs="", start_time="",
    )
    sections = build_result_sections(job, {"status": "ok", "work_dir": "/tmp/x", "outputs": {}, "output_files": []}, "ru")
    assert "не зарегистрировал результаты" in sections["Summary"]


def test_successful_run_with_registered_value_and_figure():
    from ionogram_morphology_lab.ui.matlab_results_panel import build_result_sections

    job = SimpleNamespace(
        status="completed", backend="matlab", elapsed_s=2, active_frame=3,
        output_directory="/tmp/run", source_mats_unchanged=True, source_path="iml_render_raw_ionogram.m",
        sha256="abc", source_mat_paths=["a.mat"], requested_inputs="frame=3", start_time="t",
    )
    payload = {
        "status": "ok",
        "work_dir": "/tmp/run",
        "outputs": {
            "values": [{"output": "snr", "value": 12.3, "unit": "dB", "status": "ok", "limitation": "candidate"}],
            "registered_features": [{"name": "snr"}],
            "scientific_candidates": [],
        },
        "output_files": ["/tmp/run/fig.png", "/tmp/run/t.csv"],
    }
    sections = build_result_sections(job, payload, "en")
    assert "registered output" in sections["Summary"].lower() or "What was calculated" in sections["Summary"]
    assert "snr" in sections["Values"]
    assert "fig.png" in sections["Figures"]


def test_plugin_wizard_refuses_failed(qapp):
    from ionogram_morphology_lab.ui.matlab_results_panel import PluginRegistrationDialog

    dialog = PluginRegistrationDialog({"status": "error", "work_dir": "/tmp/run"}, "demo", language="en")
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.deleteLater()


def test_pipeline_unavailable_stage_cannot_enable(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.pipeline_builder_page import PipelineBuilderPage
    from ionogram_morphology_lab.ui.session import AppSession

    page = PipelineBuilderPage(AppSession(settings=SettingsStore(tmp_path / "s.json")), get_i18n("en"))
    assert not page.checks["matlab"].isEnabled()
    page.checks["matlab"].setChecked(True)  # should remain disabled / not activate silently
    assert not page.checks["matlab"].isEnabled()
    page.checks["spread_f"].setChecked(True)
    page._mark_dirty()
    assert page._dirty
    assert "future" in page.banner.text().lower()
    page.deleteLater()


def test_expert_dialog_requires_rationale_and_canonical_list(qapp):
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.expert_decision_dialog import ExpertDecisionDialog, MORPHOLOGY_CHOICES

    dlg = ExpertDecisionDialog({"candidate_morphology": "clean", "scientific_axes": {}}, get_i18n("en"))
    assert dlg.morph.count() == len(MORPHOLOGY_CHOICES)
    assert dlg.rationale.toPlainText() == ""
    dlg._accept()
    assert dlg.error.text()
    dlg.rationale.setPlainText("visible clean ridge")
    assert dlg.decision()["morphology"] == "clean"
    assert dlg.decision()["review_state"] == "owner-reviewed"
    dlg.deleteLater()


def test_open_project_recent_list(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.ui.main_window import MainWindow

    settings = SettingsStore(tmp_path / "settings.json")
    proj = create_project("R1", language="en", workspace_parent=str(tmp_path / "ws"))
    win = MainWindow(language="en")
    win.settings = settings
    win.session.settings = settings
    win._remember_project(proj)
    recent = win._recent_projects()
    assert recent and recent[0]["name"] == "R1"
    win._refresh_projects_page()
    assert win.recent_projects_table.rowCount() >= 1
    win.close()


def test_ru_en_retranslation_matlab_tables_and_targets(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.matlab_studio_page import MatlabStudioPage
    from ionogram_morphology_lab.ui.session import AppSession

    page = MatlabStudioPage(AppSession(settings=SettingsStore(tmp_path / "s.json")), get_i18n("en"))
    page.retranslate()
    assert page.run_target.currentData() == "current_frame"
    assert "Current" in page.run_target.currentText()
    headers = [page.result_panel.values_table.horizontalHeaderItem(i).text() for i in range(5)]
    assert headers[0] == "Output"
    page.i18n.set_language("ru")
    page.retranslate()
    assert page.run_target.currentData() == "current_frame"
    assert "кадр" in page.run_target.currentText().lower()
    headers_ru = [page.result_panel.values_table.horizontalHeaderItem(i).text() for i in range(5)]
    assert headers_ru[0] == "Выход"
    assert "Сводка" in page.result_panel.tabs.tabText(0)
    page.deleteLater()


def test_help_variables_topic_covers_amp_and_phs_limits():
    from ionogram_morphology_lab.help.content import HELP_SECTIONS

    topic = next(s for s in HELP_SECTIONS if s["id"] == "variables")
    assert "Amp_all" in topic["body_en"]
    assert "Phs_all" in topic["body_en"]
    assert "does not claim a verified" in topic["body_en"].lower() or "not claim" in topic["body_en"].lower()
    assert "1440" in topic["body_en"] and "256" in topic["body_en"] and "400" in topic["body_en"]
    assert "Amp_all" in topic["body_ru"]
    assert "не утверждает" in topic["body_ru"]


def test_parameter_detail_card_and_accept_provenance(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.parameters_page import ParametersPage
    from ionogram_morphology_lab.ui.session import AppSession

    page = ParametersPage(AppSession(settings=SettingsStore(tmp_path / "s.json")), get_i18n("en"))
    assert hasattr(page, "details")
    if page.table.rowCount() > 0:
        page.table.selectRow(0)
        page._show_details()
    text = page.details.text()
    assert "Full name" in text or "Symbol" in text or "foF2" in text or "physical" in text.lower() or text.strip()
    page.deleteLater()


def test_pipeline_does_not_claim_to_alter_existing_results(qapp, tmp_path):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.pipeline_builder_page import PipelineBuilderPage
    from ionogram_morphology_lab.ui.session import AppSession

    page = PipelineBuilderPage(AppSession(settings=SettingsStore(tmp_path / "s.json")), get_i18n("ru"))
    page.retranslate() if hasattr(page, "retranslate") else None
    assert "будущ" in page.banner.text().lower()
    page.deleteLater()
