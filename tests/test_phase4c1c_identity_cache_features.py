"""Phase 4C.1c — evidence identity, cache schema, features model, status i18n."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

from ionogram_morphology_lab.morphology_candidate.cache import (
    CACHE_FORMAT,
    MISS_INCOMPATIBLE_CACHE_SCHEMA,
    MISS_INCOMPATIBLE_LEDGER_SCHEMA,
    MorphologyCandidateCache,
    make_candidate_cache_key,
    validate_candidate_cache_payload,
)
from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.fixtures import fixture_input, make_v2_ser, _base_features
from ionogram_morphology_lab.morphology_candidate.presentation import (
    contains_canonical_abstention_enum,
    format_ledger_rows,
    format_panel_text,
    rule_label,
)
from ionogram_morphology_lab.morphology_candidate.reviews import ledger_hash
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash
from ionogram_morphology_lab.morphology_candidate.service import resolve_or_evaluate_candidate
from ionogram_morphology_lab.morphology_candidate.status_messages import (
    StatusMessage,
    assert_status_language,
    format_status,
)
from ionogram_morphology_lab.morphology_candidate.types import (
    CANDIDATE_CACHE_SCHEMA_VERSION,
    CANDIDATE_ENGINE_VERSION,
    EVIDENCE_LEDGER_SCHEMA_VERSION,
    FeatureValueRef,
)
from ionogram_morphology_lab.ui.evidence_dialog import evidence_identity_from_result
from ionogram_morphology_lab.ui.features_table_model import FeaturesTableModel


ROOT = Path(__file__).resolve().parents[1]


def _frag_result():
    inp, _ = fixture_input("oversegmentation")
    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", False, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef(
        "v2_fragmentation_score", 0.91, "score", True, False
    )
    return evaluate_morphology_candidate(replace(inp, features=feats))


def test_engine_version_bumped_schema_constants():
    assert CANDIDATE_ENGINE_VERSION == "iml-morph-candidate-0.1.1"
    assert CANDIDATE_CACHE_SCHEMA_VERSION == 2
    assert EVIDENCE_LEDGER_SCHEMA_VERSION == 2
    assert CACHE_FORMAT.endswith("-v2")


def test_comparison_result_semantics_not_ambiguous():
    r = _frag_result()
    rows = format_ledger_rows([e.to_dict() for e in r.evidence_ledger], "ru")
    over = next(x for x in rows if x["rule_id"] == "gate_oversegmentation_flag")
    frag = next(x for x in rows if x["rule_id"] == "gate_fragmentation_score")
    assert over["data_validity"] == "Данные допустимы"
    assert over["result"] == "условие не сработало"
    assert over["effect"] == "Нейтрально"
    assert frag["result"] == "порог превышен"
    assert frag["effect"] == "Блокирует"
    assert "Допустимо" not in frag["result"]


def test_evidence_friendly_labels_hide_raw_ids_by_default():
    r = _frag_result()
    rows = format_ledger_rows([e.to_dict() for e in r.evidence_ledger], "ru", show_technical_ids=False)
    for row in rows:
        assert "gate_" not in row["rule"]
        assert not row["feature"].startswith("v2_")
        assert "['" not in row["value"]
        assert "not_assessable" not in row["value"]
    tech = format_ledger_rows([e.to_dict() for e in r.evidence_ledger], "en", show_technical_ids=True)
    assert any("gate_fragmentation_score" in x["rule"] for x in tech)


def test_old_combined_overseg_ledger_rejected():
    r = _frag_result().to_dict()
    r["evidence_ledger"] = [
        {
            "rule_id": "gate_oversegmentation",
            "feature_id": "v2_oversegmentation_suspected",
            "measured_value": True,
            "unit": "flag",
            "validity": "valid",
            "threshold_or_interval": True,
            "comparison": "==true",
            "support_direction": "blocks",
            "evidence_strength": "strong",
        }
    ]
    r["abstention_reasons"] = ["severe_fragmentation"]
    r["evidence_ledger_schema_version"] = 1
    r["candidate_cache_schema_version"] = 1
    key = make_candidate_cache_key(
        source_sha256=r["source_sha256"],
        frame_index=r["frame_index"],
        profile_id="p",
        signal_contract_id="c",
        feature_version=r["feature_version"],
        diagnostics_cache_id=r["diagnostics_cache_id"],
        ruleset_version=r["ruleset_version"],
        ruleset_hash=r["ruleset_hash"],
    )
    miss = validate_candidate_cache_payload(r, key)
    assert miss in {MISS_INCOMPATIBLE_LEDGER_SCHEMA, MISS_INCOMPATIBLE_CACHE_SCHEMA}


def test_legacy_v1_cache_dir_rejected(tmp_path: Path):
    rs = load_ruleset()
    r = _frag_result()
    payload = r.to_dict()
    key = make_candidate_cache_key(
        source_sha256=payload["source_sha256"],
        frame_index=payload["frame_index"],
        profile_id="p",
        signal_contract_id="c",
        feature_version=payload["feature_version"],
        diagnostics_cache_id=payload["diagnostics_cache_id"],
        ruleset_version=str(rs.get("ruleset_version")),
        ruleset_hash=ruleset_hash(rs),
    )
    cache = MorphologyCandidateCache(tmp_path)
    # Write a v1-shaped entry under legacy digest
    from ionogram_morphology_lab.morphology_candidate.cache import _legacy_v1_digest

    legacy = _legacy_v1_digest(key)
    d = tmp_path / "morphology_candidates" / legacy[:24]
    d.mkdir(parents=True)
    meta = {
        "cache_format": "iml-morph-candidate-cache-v1",
        "digest": legacy,
        "key": {
            "source_sha256": key.source_sha256,
            "frame_index": key.frame_index,
            "diagnostics_cache_id": key.diagnostics_cache_id,
            "ruleset_hash": key.ruleset_hash,
            "candidate_engine_version": "iml-morph-candidate-0.1.0",
        },
        "ruleset_hash": key.ruleset_hash,
        "candidate_engine_version": "iml-morph-candidate-0.1.0",
        "result_hash": payload.get("result_hash"),
    }
    old = dict(payload)
    old["candidate_engine_version"] = "iml-morph-candidate-0.1.0"
    old["candidate_cache_schema_version"] = 1
    old["evidence_ledger_schema_version"] = 1
    old["evidence_ledger"] = [
        {
            "rule_id": "gate_oversegmentation",
            "feature_id": "v2_oversegmentation_suspected",
            "measured_value": True,
            "unit": "flag",
            "validity": "valid",
            "threshold_or_interval": True,
            "comparison": "==true",
            "support_direction": "blocks",
            "evidence_strength": "strong",
            "human_explanation_en": "",
            "human_explanation_ru": "",
            "technical_explanation": "",
            "spatial_support_identity": "",
            "branch_identity": "",
            "interference_adjustment": "none",
            "quality_adjustment": "none",
            "temporal_adjustment": "none",
        }
    ]
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (d / "result.json").write_text(json.dumps(old, default=str), encoding="utf-8")
    lu = cache.lookup(key)
    assert not lu.hit
    assert lu.miss_reason == MISS_INCOMPATIBLE_CACHE_SCHEMA


def test_current_split_ledger_accepted_and_cached(tmp_path: Path):
    cache = MorphologyCandidateCache(tmp_path)
    ser = make_v2_ser(
        features=_base_features(
            v2_oversegmentation_suspected=False,
            v2_fragmentation_score=0.9,
            v2_horizontal_width_elevated_fraction=0.01,
            v2_vertical_width_elevated_fraction=0.01,
        )
    )
    out = resolve_or_evaluate_candidate(ser, diagnostics_cache_id="diagC1C", cache=cache)
    assert out.get("evaluated")
    assert out["result"] is not None
    assert out["result"]["candidate_cache_schema_version"] == 2
    rule_ids = {e["rule_id"] for e in out["result"]["evidence_ledger"]}
    assert "gate_oversegmentation_flag" in rule_ids
    assert "gate_fragmentation_score" in rule_ids
    assert "gate_oversegmentation" not in rule_ids
    out2 = resolve_or_evaluate_candidate(ser, diagnostics_cache_id="diagC1C", cache=cache)
    assert out2.get("cache_hit")
    assert not out2.get("evaluated")
    assert cache.counters.v2_request_count == 0


def test_evidence_identity_changes_with_frame():
    a = _frag_result().to_dict()
    a["frame_index"] = 421
    a["result_hash"] = "aaa"
    b = dict(a)
    b["frame_index"] = 1431
    b["result_hash"] = "bbb"
    ia = evidence_identity_from_result(a)
    ib = evidence_identity_from_result(b)
    assert ia["frame_index"] == 421
    assert ib["frame_index"] == 1431
    assert ia["candidate_result_hash"] != ib["candidate_result_hash"]


def test_features_model_no_eager_widgets_and_fast():
    ser = make_v2_ser(features=_base_features())
    # Expand to ~93 synthetic ids if needed
    feats = dict(ser["features"])
    for i in range(90):
        feats[f"v2_synth_{i:03d}"] = {"value": i, "unit": "n", "valid": True}
    ser["features"] = feats
    model = FeaturesTableModel()
    t0 = time.perf_counter()
    model.load_from_serializable(ser)
    dt = time.perf_counter() - t0
    assert model.rowCount() >= 90
    assert dt < 0.5
    t1 = time.perf_counter()
    model.load_from_serializable(ser)
    assert time.perf_counter() - t1 < 0.1


def test_status_retranslates_without_cyrillic_in_en():
    msg = StatusMessage(key="cached_return_both")
    en = format_status(msg, "en")
    ru = format_status(msg, "ru")
    assert "No computation was performed" in en
    assert "Расчёт не выполнялся" in ru
    assert assert_status_language(en, "en") == []
    assert "Результат загружен" not in en


def test_rule_label_localized():
    assert rule_label("gate_quality_status", "ru") == "Проверка качества"
    assert rule_label("gate_quality_status", "en") == "Quality gate"


def test_panel_still_has_no_canonical_enums():
    r = evaluate_morphology_candidate(fixture_input("no_trace")[0]).to_dict()
    _st, body = format_panel_text(r, lang="ru", v2_status="cached", candidate_status="cached")
    assert not contains_canonical_abstention_enum(body)


def test_features_tab_uses_model_view_not_93_widgets():
    page = (ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(
        encoding="utf-8"
    )
    assert "FeaturesTableModel" in page
    assert "QTableView" in page
    assert "EvidenceDialog" in page
    assert "_clear_candidate_presentation" in page


def test_production_rule_engine_untouched():
    engine = ROOT / "src/ionogram_morphology_lab/rules/engine.py"
    assert "morphology_candidate" not in engine.read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_ledger_hash_stable_after_localization(lang):
    r = _frag_result()
    ledger = [e.to_dict() for e in r.evidence_ledger]
    h = ledger_hash(ledger)
    _ = format_ledger_rows(ledger, lang)
    assert ledger_hash(ledger) == h
