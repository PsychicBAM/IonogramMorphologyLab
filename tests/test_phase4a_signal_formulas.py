"""Phase 4A: signal contracts, frame mapping, formulas, feature flag, quantity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_feature_flag_defaults_false():
    from ionogram_morphology_lab.app.settings_store import DEFAULT_SETTINGS

    assert DEFAULT_SETTINGS["analysis"]["scientific_formula_pipeline_enabled"] is False


def test_amp_all_frame_mapping_off_by_one_protection():
    from ionogram_morphology_lab.projects.time_mapping import frame_to_minute, format_hhmm
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import (
        extract_frame_consistent,
        frame_row_range,
    )

    assert frame_row_range(1).row_start == 0
    assert frame_row_range(1).row_end_exclusive == 256
    assert frame_row_range(1440).row_start == 1439 * 256
    assert frame_row_range(1440).row_end_exclusive == 368640
    assert frame_to_minute(421) == 420
    assert format_hhmm(420) == "07:00"
    with pytest.raises(IndexError):
        frame_row_range(0)
    stack = np.arange(3 * 256 * 400, dtype=float).reshape(3 * 256, 400)
    f1, r1 = extract_frame_consistent(stack, 1)
    f3, r3 = extract_frame_consistent(stack, 3)
    assert f1.shape == (256, 400)
    assert np.array_equal(f1, stack[0:256])
    assert np.array_equal(f3, stack[512:768])
    assert r1.matlab_row_start_1based == 1
    assert r3.matlab_row_end_1based == 768


def test_viewer_batch_matlab_same_mapping():
    from ionogram_morphology_lab.importers.adapters import extract_frame_kfu
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent

    stack = np.random.default_rng(0).random((5 * 256, 400))
    for i in (1, 3, 5):
        a = extract_frame_kfu(stack, i)
        b, _ = extract_frame_consistent(stack, i)
        assert np.array_equal(a, b)


def test_wrong_shape_rejected():
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent

    with pytest.raises(ValueError):
        extract_frame_consistent(np.zeros((100, 100)), 1)


def test_phs_all_disabled_when_unverified():
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import (
        phase_automatic_rules_enabled,
        phase_interpretation_message,
    )

    assert phase_automatic_rules_enabled() is False
    en = phase_interpretation_message("en")
    ru = phase_interpretation_message("ru")
    assert "not verified" in en.lower()
    assert "не подтверждена" in ru


def test_signal_contract_matching_synthetic(tmp_path):
    from ionogram_morphology_lab.importers.mat_inventory import VariableInfo
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import match_inventory_to_contracts

    vars_ = [VariableInfo(name="Amp_all", shape=(768, 400), dtype="double")]
    matches = match_inventory_to_contracts(vars_)
    amp = next(m for m in matches if m["variable_name"] == "Amp_all")
    assert amp["present"] and amp["shape_ok"]


def test_formula_registry_required_fields_and_explanations():
    from ionogram_morphology_lab.scientific_outputs.formula_registry import (
        explain_formula,
        validate_registry_structure,
    )

    assert validate_registry_structure() == []
    en = explain_formula("F001", "en")
    ru = explain_formula("F001", "ru")
    assert "What is computed" in en and "Source and page" in en
    assert "Что вычисляется" in ru and "Источник и страница" in ru
    heur = explain_formula("HEUR_IML_TRACE_WIDTH_BINS", "en")
    assert "project heuristic" in heur.lower()


def test_unit_compatibility_and_no_silent_nan():
    from ionogram_morphology_lab.scientific_outputs.formulas.axes import bin_to_mhz
    from ionogram_morphology_lab.scientific_outputs.formulas.virtual_height import (
        assert_nominal_not_true_height,
        virtual_height_from_group_delay,
    )

    q = virtual_height_from_group_delay(float("inf"))
    assert not q.valid
    q2 = bin_to_mhz(10, start_mhz=1.5, step_mhz=0.019, frequency_bins=400, axis_verified=False)
    assert not q2.valid
    with pytest.raises(ValueError):
        assert_nominal_not_true_height("true height profile")


def test_scientific_quantity_serialization():
    from ionogram_morphology_lab.scientific_outputs.quantity import ScientificQuantity

    q = ScientificQuantity(name="frequency", symbol="f", value=2.5, unit="MHz", formula_id="HEUR_BIN_TO_MHZ")
    d = q.to_dict()
    assert d["unit"] == "MHz" and d["formula_id"] == "HEUR_BIN_TO_MHZ"
    assert json.dumps(d)


def test_morphology_regression_unchanged_smoke():
    """Phase 4A must not alter RuleEngine morphology decisions."""
    from ionogram_morphology_lab.rules.engine import RuleEngine

    # Minimal: engine still constructs and feature flag does not auto-enable formula pipeline
    eng = RuleEngine()
    assert eng is not None
    from ionogram_morphology_lab.app.settings_store import SettingsStore

    store = SettingsStore()
    assert store.get("analysis", "scientific_formula_pipeline_enabled", True) is False


def test_raw_signals_page_builds(qapp_optional=None):
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.i18n import get_i18n
    from ionogram_morphology_lab.ui.raw_signals_page import RawSignalsPage
    from ionogram_morphology_lab.ui.session import AppSession

    app = QApplication.instance() or QApplication([])
    page = RawSignalsPage(AppSession(settings=SettingsStore()), get_i18n("en"))
    assert "Raw Numeric Signals" in page.banner.text() or "numeric" in page.banner.text().lower()
    page.i18n.set_language("ru")
    page.retranslate()
    assert "числовые" in page.banner.text().lower()
    page.deleteLater()


def test_real_mat_shape_inventory_if_present():
    mat = ROOT.parent / "ion2013" / "maps201301jan" / "data" / "Am_all_2013-01-01.mat"
    if not mat.is_file():
        pytest.skip("approved MAT not present")
    from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
    from ionogram_morphology_lab.scientific_outputs.signal_contracts import match_inventory_to_contracts

    inv = inventory_mat(mat)
    amp = next(v for v in inv.variables if v.name == "Amp_all")
    assert amp.shape == (368640, 400)
    matches = match_inventory_to_contracts(inv.variables)
    assert next(m for m in matches if m["variable_name"] == "Amp_all")["shape_ok"] is True
