from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from ionogram_morphology_lab.ui.matlab_results_panel import (
    PluginRegistrationDialog,
    build_result_sections,
    classify_output_files,
)


def _job(**values):
    base = dict(
        status="completed", backend="octave", elapsed_s=1.25, active_frame=3,
        output_directory="/tmp/matlab-run", source_mats_unchanged=True,
        source_path="method.m", sha256="abc", source_mat_paths=["input.mat"],
        requested_inputs="frame=3", start_time="2026-01-01T00:00:00Z",
    )
    base.update(values)
    return SimpleNamespace(**base)


def test_successful_result_sections_show_provenance_and_destinations():
    payload = {
        "status": "ok", "work_dir": "/tmp/matlab-run",
        "outputs": {"registered_features": [{"name": "foF2"}], "scientific_candidates": [{"id": "c1"}]},
        "output_files": ["/tmp/plot.png", "/tmp/table.csv", "/tmp/result.mat"],
    }
    sections = build_result_sections(_job(), payload)
    assert "SHA-256: abc" in sections["Provenance"]
    assert "foF2" in sections["Registered Features"]
    assert "c1" in sections["Scientific Candidates"]
    assert "not automatically inserted into main Results" in sections["Summary"]


def test_failed_result_sections_keep_error_and_integrity():
    sections = build_result_sections(
        _job(status="failed", source_mats_unchanged=False),
        {"status": "error", "error_message": "line 12: bad input", "work_dir": "/tmp/run"},
    )
    assert "line 12" in sections["Warnings and Errors"]
    assert "SHA-256 changed" in sections["Summary"]


def test_figure_file_listing_groups_known_artifacts():
    grouped = classify_output_files(["a.png", "b.csv", "c.mat", "d.txt"])
    assert grouped == {"figures": ["a.png"], "tables": ["b.csv"], "matrices": ["c.mat"], "other": ["d.txt"]}


def test_plugin_wizard_refuses_failed_or_incomplete_run():
    app = QApplication.instance() or QApplication([])
    dialog = PluginRegistrationDialog({"status": "error", "work_dir": "/tmp/run"}, "demo")
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    dialog.deleteLater()
    assert app is not None


def test_matlab_payload_never_implies_main_results_insertion():
    sections = build_result_sections(
        _job(),
        {
            "status": "ok",
            "work_dir": "/tmp/run",
            "outputs": {"registered_features": [{"name": "x"}]},
            "output_files": [],
        },
    )
    assert "not automatically inserted into main Results" in sections["Summary"]


def test_method_comparison_shows_session_matlab_candidates_without_run(qapp=None):
    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.method_comparison_page import MethodComparisonPage
    from ionogram_morphology_lab.ui.session import AppSession

    app = QApplication.instance() or QApplication([])
    session = AppSession(settings=SettingsStore())
    session.matlab_comparison_candidates = [
        {
            "method": "MATLAB Studio",
            "layer": "F",
            "morphology": "frequency_spread",
            "status": "matlab_candidate",
        }
    ]
    page = MethodComparisonPage(session, get_i18n("en"))
    page.refresh()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "MATLAB Studio"
    assert page.table.item(0, 2).text() == "frequency_spread"
    assert session.last_results == []
    page.deleteLater()
    assert app is not None
