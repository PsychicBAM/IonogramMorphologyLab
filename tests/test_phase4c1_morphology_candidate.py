"""Phase 4C.1 — shadow morphology candidate engine tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_candidate.cache import (
    MorphologyCandidateCache,
    make_candidate_cache_key,
)
from ionogram_morphology_lab.morphology_candidate.engine import (
    CANDIDATE_ENGINE_VERSION,
    evaluate_morphology_candidate,
)
from ionogram_morphology_lab.morphology_candidate.fixtures import FIXTURE_NAMES, fixture_input
from ionogram_morphology_lab.morphology_candidate.labels import CANDIDATE_LABELS, disclaimer
from ionogram_morphology_lab.morphology_candidate.reviews import (
    geometry_reviews_dir,
    save_morphology_review,
)
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash
from ionogram_morphology_lab.morphology_candidate.types import (
    ALLOWED_CANDIDATES,
    MorphologyCandidateReview,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_matrix(name: str):
    inp, expected = fixture_input(name)
    # Immutability: evaluate must not alter feature mapping values
    before = {k: (v.value, v.valid, v.missing) for k, v in inp.features.items()}
    result = evaluate_morphology_candidate(inp)
    after = {k: (v.value, v.valid, v.missing) for k, v in inp.features.items()}
    assert before == after
    assert result.candidate in ALLOWED_CANDIDATES
    assert result.provisional is True
    assert result.shadow_mode is True
    assert result.scientifically_validated is False
    assert result.production_applied is False
    assert result.evidence_ledger
    assert "%" not in result.human_explanation_en or "candidate" in result.human_explanation_en.lower()
    if isinstance(expected, set):
        assert result.candidate in expected
    else:
        assert result.candidate == expected
    if result.abstained:
        assert result.abstention_reasons
    if result.candidate == "mixed_spread_candidate":
        assert result.h_evidence.supported and result.v_evidence.supported
        assert result.coexistence_summary.get("coexistence_supported")
    if name == "no_trace":
        assert result.candidate == "not_assessable"
        assert result.candidate not in {
            "frequency_spread_candidate",
            "range_spread_candidate",
            "mixed_spread_candidate",
        }
    if name == "vertical_interference":
        assert result.candidate != "range_spread_candidate"
    if name == "floor_clutter_v":
        assert result.candidate != "range_spread_candidate"
    if name == "secondary_echo_h":
        assert result.candidate != "frequency_spread_candidate"
    if name == "unrelated_hv":
        assert result.candidate != "mixed_spread_candidate"
    if name == "missing_neighbours":
        assert result.temporal_summary.get("present") is False
    if name == "oversegmentation":
        assert "oversegmentation_suspected" in result.abstention_reasons or (
            "both_oversegmentation_and_fragmentation" in result.abstention_reasons
        )
        # False overseg flag must never be the sole blocking ledger cause
        for e in result.evidence_ledger:
            if e.rule_id == "gate_oversegmentation_flag" and e.measured_value is False:
                assert e.support_direction != "blocks" or e.measured_value is True
        frag_entries = [e for e in result.evidence_ledger if e.rule_id == "gate_fragmentation_score"]
        assert frag_entries
        assert frag_entries[0].measured_value is not None


def test_deterministic_hash_stable():
    inp, _ = fixture_input("freq_strong_h")
    a = evaluate_morphology_candidate(inp)
    b = evaluate_morphology_candidate(inp)
    assert a.result_hash == b.result_hash
    assert a.candidate == b.candidate


def test_identity_mismatch_rejects():
    inp, _ = fixture_input("freq_strong_h")
    r = evaluate_morphology_candidate(inp, expected_v2_identity="deadbeef")
    assert r.candidate == "not_assessable"
    assert "geometry_result_identity_mismatch" in r.abstention_reasons


def test_cache_invalidation_on_ruleset_change(tmp_path: Path):
    inp, _ = fixture_input("freq_strong_h")
    rs = load_ruleset()
    result = evaluate_morphology_candidate(inp, ruleset=rs)
    cache = MorphologyCandidateCache(tmp_path)
    key = make_candidate_cache_key(
        source_sha256=inp.source_sha256,
        frame_index=inp.frame_index,
        profile_id=inp.profile_id,
        signal_contract_id=inp.signal_contract_id,
        feature_version=inp.feature_version,
        diagnostics_cache_id=inp.diagnostics_cache_id,
        ruleset_version=rs["ruleset_version"],
        ruleset_hash=ruleset_hash(rs),
    )
    cache.put(key, result)
    assert cache.get(key) is not None
    bad = make_candidate_cache_key(
        source_sha256=inp.source_sha256,
        frame_index=inp.frame_index,
        profile_id=inp.profile_id,
        signal_contract_id=inp.signal_contract_id,
        feature_version=inp.feature_version,
        diagnostics_cache_id=inp.diagnostics_cache_id,
        ruleset_version=rs["ruleset_version"],
        ruleset_hash="0" * 64,
    )
    assert cache.get(bad) is None
    # V2 cache root sibling untouched conceptually — morph lives under morphology_candidates/
    assert (tmp_path / "morphology_candidates").is_dir()
    assert not (tmp_path / "v2_features").exists()


def test_morphology_review_separate_from_geometry(tmp_path: Path):
    geo = geometry_reviews_dir(tmp_path)
    geo.mkdir(parents=True)
    sentinel = geo / "review_f0001_geometry.json"
    sentinel.write_text('{"review_kind":"geometry_only"}', encoding="utf-8")
    before = {p.name for p in geo.glob("*.json")}
    review = MorphologyCandidateReview(
        source_sha256="a" * 64,
        frame_index=1,
        feature_version="iml2-0.2.0",
        diagnostics_cache_id="x",
        ruleset_version="0.1.0",
        ruleset_hash="h",
        candidate_result_hash="r",
        displayed_candidate="frequency_spread_candidate",
        reviewer_decision="agree_frequency",
        confirmed_ground_truth=False,
    )
    path = save_morphology_review(tmp_path, review)
    assert "morphology_reviews" in str(path)
    assert path.is_file()
    after = {p.name for p in geo.glob("*.json")}
    assert before == after
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["review_kind"] == "morphology_candidate_review"
    assert data["confirmed_ground_truth"] is False


def test_ru_en_labels_and_disclaimer():
    for cand in ALLOWED_CANDIDATES:
        assert cand in CANDIDATE_LABELS
        assert CANDIDATE_LABELS[cand]["ru"]
        assert CANDIDATE_LABELS[cand]["en"]
    assert "теневом" in disclaimer("ru").lower() or "предварительный" in disclaimer("ru").lower()
    assert "provisional" in disclaimer("en").lower()
    assert "candidate" in disclaimer("en").lower() or "shadow" in disclaimer("en").lower()


def test_ruleset_flags():
    rs = load_ruleset()
    assert rs["provisional"] is True
    assert rs["scientifically_validated"] is False
    assert rs["production_enabled"] is False
    assert CANDIDATE_ENGINE_VERSION in rs["candidate_engine_version"] or rs["candidate_engine_version"] == CANDIDATE_ENGINE_VERSION
    assert "iml2-0.2.0" in rs["compatible_feature_versions"]


def test_production_rule_engine_does_not_import_candidate():
    engine_path = ROOT / "src" / "ionogram_morphology_lab" / "rules" / "engine.py"
    tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", None) or ""
            names = [a.name for a in getattr(node, "names", [])]
            blob = mod + " ".join(names)
            assert "morphology_candidate" not in blob
    # Also scan pipeline production path
    pipe = ROOT / "src" / "ionogram_morphology_lab" / "projects" / "pipeline.py"
    text = pipe.read_text(encoding="utf-8")
    # pipeline may import V2 for shadow but must not import candidate engine into RuleEngine path
    # Strict: RuleEngine class file untouched regarding candidate
    assert "morphology_candidate" not in text or "evaluate_morphology_candidate" not in text


def test_interference_separate_axis():
    inp, _ = fixture_input("blocking_interference")
    r = evaluate_morphology_candidate(inp)
    assert r.interference.level == "blocking"
    assert r.candidate == "not_assessable"
    assert r.candidate not in {
        "frequency_spread_candidate",
        "range_spread_candidate",
        "mixed_spread_candidate",
    }
