from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

from ionogram_morphology_lab.i18n import I18n
from ionogram_morphology_lab.matlab_studio.builtin_library import list_builtin_methods
from ionogram_morphology_lab.projects.model import create_project, new_run
from ionogram_morphology_lab.projects.pipeline import analyze_frame
from ionogram_morphology_lab.rendering.overlays import overlay_legend
from ionogram_morphology_lab.rule_builder.codegen import (
    generate_matlab_function,
    generate_python_rule,
)
from ionogram_morphology_lab.rule_builder.model import ScientificRule, filter_rules_by_status
from ionogram_morphology_lab.rule_builder.packs import import_pack, validate_pack
from ionogram_morphology_lab.rule_builder.store import RuleStore
from ionogram_morphology_lab.rule_builder.testing import confusion_vs_labels, threshold_sweep
from ionogram_morphology_lab.scientific_outputs import (
    AMBIGUITY_VALUES,
    LAYER_VALUES,
    MORPHOLOGY_VALUES,
    ParameterEstimate,
    ScientificFrameResult,
    migrate_legacy_morphology,
)
from ionogram_morphology_lab.synthetic.generator import generate_synthetic_case
from ionogram_morphology_lab.utils.paths import app_root


def test_taxonomy_axes_and_legacy_migration():
    assert "E" in LAYER_VALUES
    assert "frequency_spread" in MORPHOLOGY_VALUES
    assert "possible_O_X" in AMBIGUITY_VALUES
    assert len({LAYER_VALUES, MORPHOLOGY_VALUES, AMBIGUITY_VALUES}) == 3
    assert migrate_legacy_morphology("frequency") == ("frequency_spread", "indeterminate")
    result = ScientificFrameResult(layer="E", morphology="frequency", ambiguity="possible_ox")
    assert result.morphology == "frequency_spread"
    assert "ionogram_type" not in result.to_dict()


def test_parameter_estimate_preserves_estimation_context():
    estimate = ParameterEstimate("foF2", 6.1, unit="MHz", estimation_method="trace endpoint")
    payload = estimate.to_dict()
    assert payload["unit"] == "MHz"
    assert payload["estimation_method"] == "trace endpoint"
    assert payload["limitation"]


def test_es_registry_does_not_activate_unsupported_letter_list():
    registry = app_root() / "knowledge_base" / "ES_SUBTYPE_SOURCE_REGISTRY.csv"
    assert registry.is_file()
    rows = list(csv.DictReader(registry.open(encoding="utf-8")))
    invented_active = [
        row
        for row in rows
        if row.get("implementation_status") == "active"
        and "letter" in row.get("source_term", "").lower()
        and not row.get("source_id")
    ]
    assert not invented_active, "Unsupported Es letter lists must not be active."


def test_builtin_methods_and_required_detectors_exist():
    assert len(list_builtin_methods()) >= 70
    required = {
        "iml_detect_e_layer_candidate",
        "iml_detect_es_candidate",
        "iml_detect_f2_candidate",
        "iml_detect_frequency_spread_candidate",
        "iml_detect_vertical_interference",
        "iml_detect_possible_ox_pattern",
    }
    assert required <= {method.method_id for method in list_builtin_methods()}


def test_rule_store_codegen_and_status_filtering(tmp_path):
    rule = ScientificRule(
        rule_id="candidate_frequency",
        category="morphology",
        conditions=[{"feature": "width", "operator": "gte", "value": 4.0}],
        outputs={"morphology": "frequency_spread"},
        status="source_verified",
    )
    store = RuleStore(tmp_path / "rules")
    store.save_rule(rule, "initial local candidate rule")
    assert [r.rule_id for r in store.list_rules()] == ["candidate_frequency"]
    store.disable_rule("candidate_frequency")
    assert not store.list_rules()[0].enabled
    assert "def candidate_frequency" in generate_python_rule(rule)
    assert "function fired = candidate_frequency" in generate_matlab_function(rule)

    strict = filter_rules_by_status(
        [
            ScientificRule(rule_id="ok", status="source_verified"),
            ScientificRule(rule_id="draft", status="draft"),
        ],
        "scientific_strict",
    )
    assert [r.rule_id for r in strict] == ["ok"]


def test_rule_packs_are_valid_and_broken_archives_are_isolated(tmp_path):
    pack = app_root() / "rule_packs" / "iml-core-spread-f"
    assert validate_pack(pack).ok
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("../escape.txt", "not allowed")
    result = import_pack(broken)
    assert not result.ok
    assert any("Unsafe archive path" in err for err in result.errors)
    assert not (tmp_path / "escape.txt").exists()


def test_rule_testing_helpers_report_development_behavior():
    rule = ScientificRule(
        rule_id="threshold_candidate",
        conditions=[{"feature": "width", "operator": "gte", "value": 4.0}],
    )
    rows = [{"width": 3.0, "label": "negative"}, {"width": 6.0, "label": "positive"}]
    sweep = threshold_sweep(rule, rows, "width", [3.0, 5.0])
    assert [row["fired"] for row in sweep] == [2, 1]
    assert confusion_vs_labels(rule, rows) == {"negative:negative": 1, "positive:positive": 1}


def test_pipeline_emits_separate_scientific_axes_for_synthetic_development_frame(tmp_path):
    # Synthetic input exercises the pipeline; it is not scientific validation evidence.
    from ionogram_morphology_lab.instrument_profiles.schema import InstrumentProfile, save_profile

    profile = InstrumentProfile(
        profile_id="v11_synthetic_profile",
        profile_name="v1.1 synthetic development profile",
        frames_per_file=1,
        height_bins=256,
        frequency_bins=400,
        frequency_start_mhz=1.5,
        frequency_step_mhz=0.019,
        expected_amplitude_shape=[256, 400],
        profile_verification_status="user-defined-unverified",
    )
    profile_path = save_profile(profile)
    try:
        project = create_project("v11_axes", workspace_parent=tmp_path, profile_id=profile.profile_id)
        record = analyze_frame(
            generate_synthetic_case("horizontally_diffuse"),
            project=project,
            run=new_run(project),
            source_path="synthetic_development_only",
            source_sha256="",
            frame_index=1,
            profile_id=profile.profile_id,
        )
    finally:
        profile_path.unlink(missing_ok=True)
    axes = record["scientific_axes"]
    assert {"layer", "morphology"} <= axes.keys(), (
        "Synthetic input only checks pipeline structure; it is not scientific validation."
    )


def test_overlay_navigation_and_i18n_contracts_remain_available():
    assert all({"color", "linestyle", "pattern"} <= row.keys() for row in overlay_legend())
    source = (app_root() / "src" / "ionogram_morphology_lab" / "ui" / "main_window.py").read_text(
        encoding="utf-8"
    )
    for key in ("parameters", "rules", "rule_test", "compare", "pipeline"):
        assert f'("{key}",' in source
    assert set(I18n("en").keys()) == set(I18n("ru").keys())
