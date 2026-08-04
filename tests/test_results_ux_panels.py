"""Results UX: pipeline panel, diffuse explanation, scientific status."""

from __future__ import annotations

from ionogram_morphology_lab.ui.analysis_pipeline_panel import DEFAULT_PIPELINE_COMPONENTS
from ionogram_morphology_lab.ui.diffuse_explanation import explain_diffuse_unspecified
from ionogram_morphology_lab.ui.scientific_status import (
    insufficient_examples_message,
    scientific_status_label,
    scientific_status_token,
)


def test_pipeline_components_declare_matlab_and_ml_disabled() -> None:
    by_key = {row[0]: row for row in DEFAULT_PIPELINE_COMPONENTS}
    assert by_key["rule_engine"][3] == "Active"
    assert by_key["matlab"][3] == "Disabled"
    assert by_key["ml"][3] == "Disabled"
    assert by_key["atlas_images"][3] == "Unavailable"
    assert by_key["atlas_meta"][3] == "Active"


def test_diffuse_unspecified_explains_thresholds_ru() -> None:
    rec = {
        "candidate_morphology": "diffuse_unspecified",
        "measured_features": {
            "median_horizontal_width": 5.2,
            "median_vertical_width": 5.1,
            "horizontal_broadening_persistence": 0.28,
            "vertical_broadening_persistence": 0.27,
            "frequency_evidence_passed": 0.0,
            "range_evidence_passed": 0.0,
            "frequency_evidence_absolute": 0.0,
            "range_evidence_absolute": 0.0,
            "colocated_spread_fraction": 0.05,
        },
        "interference_status": "present",
        "near_threshold_rules": ["R001_near_threshold"],
        "abstention_reason": "near_threshold_frequency",
        "disagreement_flags": ["near_threshold_frequency"],
    }
    text = explain_diffuse_unspecified(rec, "ru")
    assert "тип не определён" in text
    assert "порог 6.0" in text
    assert "R001_near_threshold" in text
    assert "автоматический кандидат" in text.lower() or "Автоматический кандидат" in text


def test_scientific_status_defaults_to_automatic_candidate() -> None:
    assert scientific_status_token({}) == "automatic-candidate"
    assert scientific_status_label("automatic-candidate", "en") == "Automatic candidate"
    assert scientific_status_label("owner-reviewed", "ru") == "Проверено владельцем"
    assert "Insufficient" in insufficient_examples_message("en")
    assert "недостаточно" in insufficient_examples_message("ru")
