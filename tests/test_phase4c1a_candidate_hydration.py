"""Phase 4C.1a — cache hydration, compatibility, UI presentation, sequence decoupling."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.morphology_candidate.cache import (
    MorphologyCandidateCache,
    make_candidate_cache_key,
)
from ionogram_morphology_lab.morphology_candidate.compatibility import (
    INCOMPLETE_LEGACY_CACHE,
    classify_v2_for_candidate,
)
from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.fixtures import fixture_input, make_v2_ser, _base_features
from ionogram_morphology_lab.morphology_candidate.presentation import (
    contains_raw_python_dump,
    format_panel_text,
)
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash
from ionogram_morphology_lab.morphology_candidate.service import (
    geometry_review_status_for_frame,
    resolve_or_evaluate_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_cache_hydration_no_reeval(tmp_path: Path):
    inp, _ = fixture_input("freq_strong_h")
    rs = load_ruleset()
    cache = MorphologyCandidateCache(tmp_path)
    ser = make_v2_ser(
        frame_index=inp.frame_index,
        source_sha=inp.source_sha256,
        features=_base_features(
            v2_horizontal_width_elevated_fraction=0.40,
            v2_vertical_width_elevated_fraction=0.02,
            v2_horizontal_contiguous_broadening_length=10,
            v2_median_local_horizontal_width_bins=4,
        ),
    )
    out1 = resolve_or_evaluate_candidate(
        ser,
        diagnostics_cache_id=inp.diagnostics_cache_id,
        cache=cache,
        profile_id=inp.profile_id,
        signal_contract_id=inp.signal_contract_id,
        force=False,
    )
    assert out1["evaluated"] is True
    assert out1["status"] == "candidate_new"
    evals = cache.counters.candidate_engine_evaluation_count
    v2_req = cache.counters.v2_request_count
    out2 = resolve_or_evaluate_candidate(
        ser,
        diagnostics_cache_id=inp.diagnostics_cache_id,
        cache=cache,
        profile_id=inp.profile_id,
        signal_contract_id=inp.signal_contract_id,
        force=False,
    )
    assert out2["cache_hit"] is True
    assert out2["evaluated"] is False
    assert out2["status"] == "candidate_cached"
    assert cache.counters.candidate_engine_evaluation_count == evals
    assert cache.counters.v2_request_count == v2_req == 0


def test_geometry_unreviewed_still_gets_candidate(tmp_path: Path):
    assert geometry_review_status_for_frame(str(tmp_path), source_sha256="a" * 64, frame_index=5) == (
        "geometry_unreviewed"
    )
    cache = MorphologyCandidateCache(tmp_path)
    ser = make_v2_ser(
        features=_base_features(
            v2_horizontal_width_elevated_fraction=0.40,
            v2_vertical_width_elevated_fraction=0.02,
            v2_horizontal_contiguous_broadening_length=10,
        )
    )
    out = resolve_or_evaluate_candidate(
        ser, diagnostics_cache_id="diag1", cache=cache, profile_id="p", signal_contract_id="c"
    )
    assert out["result"] is not None
    assert out["result"]["candidate"] == "frequency_spread_candidate"


def test_legacy_incomplete_v2_not_evaluated(tmp_path: Path):
    ser = make_v2_ser(features=_base_features())
    del ser["features"]["v2_coexistence_score"]
    del ser["features"]["v2_horizontal_width_elevated_fraction"]
    compat = classify_v2_for_candidate(ser)
    assert compat["state"] == INCOMPLETE_LEGACY_CACHE
    assert compat["can_evaluate"] is False
    cache = MorphologyCandidateCache(tmp_path)
    out = resolve_or_evaluate_candidate(ser, diagnostics_cache_id="x", cache=cache)
    assert out["evaluated"] is False
    assert out["result"] is None
    assert cache.counters.candidate_engine_evaluation_count == 0


def test_missing_features_do_not_create_blocking_interference():
    from ionogram_morphology_lab.morphology_candidate.from_v2 import assess_interference, _feat_ref

    features = {
        "v2_interference_level": _feat_ref({}, "v2_interference_level"),
    }
    inter = assess_interference(features)
    assert inter.level == "unavailable"
    assert inter.level != "blocking"


def test_false_overseg_flag_not_blocking_cause():
    inp, _ = fixture_input("oversegmentation")
    # Force overseg false but high fragmentation
    from dataclasses import replace
    from ionogram_morphology_lab.morphology_candidate.types import FeatureValueRef

    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", 0, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef(
        "v2_fragmentation_score", 0.9, "score", True, False
    )
    inp2 = replace(inp, features=feats, ambiguity_flags=())
    r = evaluate_morphology_candidate(inp2)
    assert "severe_fragmentation" in r.abstention_reasons
    assert "oversegmentation_suspected" not in r.abstention_reasons
    for e in r.evidence_ledger:
        if e.feature_id == "v2_oversegmentation_suspected":
            assert e.measured_value in {False, 0, 0.0}
            assert e.support_direction == "neutral"
        if e.rule_id == "gate_fragmentation_score":
            assert e.measured_value == 0.9
            assert e.support_direction == "blocks"


def test_panel_presentation_no_raw_dicts():
    inp, _ = fixture_input("freq_strong_h")
    r = evaluate_morphology_candidate(inp).to_dict()
    for lang in ("ru", "en"):
        status, body = format_panel_text(
            r, lang=lang, v2_status="cached", candidate_status="cached"
        )
        assert not contains_raw_python_dump(status)
        assert not contains_raw_python_dump(body)
        assert "{" not in body or "supported" not in body  # no dict dumps
        assert "()" not in body
        # disclaimer once externally — body should not include it
        from ionogram_morphology_lab.morphology_candidate.labels import disclaimer

        assert body.count(disclaimer(lang)) == 0


def test_production_rule_engine_untouched_by_candidate_import():
    engine = ROOT / "src" / "ionogram_morphology_lab" / "rules" / "engine.py"
    tree = ast.parse(engine.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "morphology_candidate" in node.module:
            pytest.fail("RuleEngine imports morphology_candidate")


def test_ui_sequence_path_not_gated_by_geometry_review():
    page = ROOT / "src" / "ionogram_morphology_lab" / "ui" / "feature_diagnostics_page.py"
    text = page.read_text(encoding="utf-8")
    # Enrichment must exist and must not require geometry review for eligibility
    assert "_enrich_sequence_morph_candidates" in text
    assert "geometry_review_status_for_frame" in text
    # Geometry reviews remain available (save/overview) but must not gate candidates
    assert "save_geometry_review_update_in_place" in text or "geometry_reviews" in text
    assert "if geometry_review" not in text.lower().replace("_", "")
    svc = (ROOT / "src" / "ionogram_morphology_lab" / "morphology_candidate" / "service.py").read_text(
        encoding="utf-8"
    )
    assert "never gates" in svc.lower() or "Informational only" in svc


def test_bare_directory_not_cache_hit(tmp_path: Path):
    cache = MorphologyCandidateCache(tmp_path)
    rs = load_ruleset()
    key = make_candidate_cache_key(
        source_sha256="a" * 64,
        frame_index=1,
        profile_id="p",
        signal_contract_id="c",
        feature_version=FEATURE_VERSION,
        diagnostics_cache_id="d",
        ruleset_version=rs["ruleset_version"],
        ruleset_hash=ruleset_hash(rs),
    )
    d = cache._dir(key)
    d.mkdir(parents=True, exist_ok=True)
    lu = cache.lookup(key)
    assert lu.hit is False
    assert lu.miss_reason == "corrupt_result"
