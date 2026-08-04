#!/usr/bin/env python3
"""Validate Phase 4C.1/4C.1a/4C.1b morphology candidate remains shadow-only and contract-complete."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.morphology_candidate.cache import MorphologyCandidateCache
from ionogram_morphology_lab.morphology_candidate.compatibility import (
    INCOMPLETE_LEGACY_CACHE,
    classify_v2_for_candidate,
)
from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.fixtures import fixture_input, make_v2_ser, _base_features
from ionogram_morphology_lab.morphology_candidate.geometry_review_index import (
    load_geometry_review_corpus,
    save_geometry_review_update_in_place,
)
from ionogram_morphology_lab.morphology_candidate.cache import (
    CACHE_FORMAT,
    MISS_INCOMPATIBLE_CACHE_SCHEMA,
)
from ionogram_morphology_lab.morphology_candidate.presentation import (
    cached_return_status,
    contains_canonical_abstention_enum,
    contains_raw_python_dump,
    format_ledger_rows,
    format_panel_text,
    ledger_headers,
)
from ionogram_morphology_lab.morphology_candidate.status_messages import (
    StatusMessage,
    assert_status_language,
    format_status,
)
from ionogram_morphology_lab.morphology_candidate.types import (
    CANDIDATE_CACHE_SCHEMA_VERSION,
    CANDIDATE_ENGINE_VERSION,
)
from ionogram_morphology_lab.morphology_candidate.reviews import ledger_hash
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset
from ionogram_morphology_lab.morphology_candidate.service import resolve_or_evaluate_candidate
from ionogram_morphology_lab.morphology_candidate.types import ALLOWED_CANDIDATES


def _scan_no_import(path: Path, banned: str) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"{path}: syntax error {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if banned in alias.name:
                    errors.append(f"{path}: imports {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if banned in mod:
                errors.append(f"{path}: from-imports {mod}")
    return errors


def main() -> int:
    errors: list[str] = []

    rs = load_ruleset()
    if not rs.get("provisional") or rs.get("scientifically_validated") or rs.get("production_enabled"):
        errors.append("ruleset flags invalid for shadow mode")

    engine = ROOT / "src" / "ionogram_morphology_lab" / "rules" / "engine.py"
    errors.extend(_scan_no_import(engine, "morphology_candidate"))

    # UI / sequence must not gate candidate on geometry review
    for rel in (
        "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py",
        "src/ionogram_morphology_lab/morphology_candidate/service.py",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        if "geometry_review" in text and (
            "if not geometry" in text.lower()
            or "require_geometry_review" in text
            or "geometry_review_required" in text
        ):
            errors.append(f"{rel}: candidate path appears gated by geometry review")
    page = (ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(encoding="utf-8")
    if "_enrich_sequence_morph_candidates" not in page:
        errors.append("sequence morph enrichment missing")
    if "btn_calc_morph" not in page or "btn_morph_evidence" not in page or "btn_morph_review" not in page:
        errors.append("primary candidate buttons missing")

    # Cache hit: no evaluation, no V2 request
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        cache = MorphologyCandidateCache(td)
        ser = make_v2_ser(
            features=_base_features(
                v2_horizontal_width_elevated_fraction=0.40,
                v2_vertical_width_elevated_fraction=0.02,
                v2_horizontal_contiguous_broadening_length=10,
            )
        )
        a = resolve_or_evaluate_candidate(ser, diagnostics_cache_id="d1", cache=cache)
        b = resolve_or_evaluate_candidate(ser, diagnostics_cache_id="d1", cache=cache)
        if not b.get("cache_hit") or b.get("evaluated"):
            errors.append("candidate cache hit re-evaluated engine")
        if cache.counters.v2_request_count != 0:
            errors.append("candidate cache path incremented v2_request_count")
        if a.get("result") is None:
            errors.append("initial candidate evaluation failed")

    # Incomplete legacy not evaluated as morphology
    legacy = make_v2_ser(features=_base_features())
    del legacy["features"]["v2_coexistence_score"]
    compat = classify_v2_for_candidate(legacy)
    if compat.get("state") != INCOMPLETE_LEGACY_CACHE or compat.get("can_evaluate"):
        errors.append("legacy incomplete cache not detected")

    # Fragmentation ledger + false overseg
    from dataclasses import replace
    from ionogram_morphology_lab.morphology_candidate.types import FeatureValueRef

    inp, _ = fixture_input("freq_strong_h")
    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", False, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef("v2_fragmentation_score", 0.9, "score", True, False)
    r = evaluate_morphology_candidate(replace(inp, features=feats))
    if "severe_fragmentation" not in r.abstention_reasons:
        errors.append("severe_fragmentation reason missing")
    for e in r.evidence_ledger:
        if e.rule_id == "gate_oversegmentation_flag" and e.measured_value is False and e.support_direction == "blocks":
            errors.append("false oversegmentation flag shown as blocking cause")
        if e.rule_id == "gate_fragmentation_score" and e.measured_value != 0.9:
            errors.append("fragmentation gate missing numeric value")

    # Presentation: no raw dicts / no canonical abstention enums; disclaimer not in body
    panel_r = evaluate_morphology_candidate(fixture_input("weak_boundary")[0])
    for lang in ("ru", "en"):
        _st, body = format_panel_text(panel_r.to_dict(), lang=lang, v2_status="cached", candidate_status="cached")
        if contains_raw_python_dump(body):
            errors.append(f"raw python dump in {lang} panel")
        if contains_canonical_abstention_enum(body):
            errors.append(f"canonical abstention enum leaked into {lang} panel")
        from ionogram_morphology_lab.morphology_candidate.labels import disclaimer

        if body.count(disclaimer(lang)) > 0:
            errors.append(f"disclaimer duplicated inside {lang} panel body")

    no_trace = evaluate_morphology_candidate(fixture_input("no_trace")[0]).to_dict()
    _st_ru, body_ru = format_panel_text(no_trace, lang="ru", v2_status="cached", candidate_status="cached")
    if "no_valid_ionospheric_trace" in body_ru or contains_canonical_abstention_enum(body_ru):
        errors.append("RU panel still contains no_valid_ionospheric_trace / canonical enum")
    if "Расчёт не выполнялся" not in cached_return_status("ru", v2_cached=True, candidate_cached=True):
        errors.append("cached-return RU status missing no-computation wording")
    if "No computation was performed" not in cached_return_status("en", v2_cached=True, candidate_cached=True):
        errors.append("cached-return EN status missing no-computation wording")

    # Localized evidence table shares ledger hash with canonical JSON
    ledger = no_trace.get("evidence_ledger") or []
    h = ledger_hash(ledger)
    rows = format_ledger_rows(ledger, "ru")
    if len(rows) != len(ledger):
        errors.append("localized ledger row count mismatch")
    if ledger_hash(ledger) != h:
        errors.append("ledger hash changed after localization")
    hdr = ledger_headers("ru")
    if "Измеренное значение" not in hdr or "Сила" not in hdr:
        errors.append("RU evidence headers incomplete")

    # Page title i18n
    ru_i18n = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    if ru_i18n.get("nav.feature_diagnostics") != "Диагностика следа и геометрии":
        errors.append("RU page title key not localized")

    # Evidence primary action must open identity-bound dialog (not JSON dump)
    page = (ROOT / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(encoding="utf-8")
    if "EvidenceDialog" not in page or "_clear_candidate_presentation" not in page:
        errors.append("Evidence identity binding / clear-on-frame-change missing")
    if "FeaturesTableModel" not in page or "QTableView" not in page:
        errors.append("Features tab model/view missing")
    if "act_copy_evidence_json" not in page or "act_export_evidence_json" not in page:
        errors.append("Evidence JSON overflow actions missing")
    if "act_copy_frag_gates" not in page:
        errors.append("fragmentation gate copy helper missing")
    if "Review corpus overview" not in page and "Обзор проверок" not in page:
        errors.append("review corpus overview action missing")

    if CANDIDATE_ENGINE_VERSION != "iml-morph-candidate-0.1.1":
        errors.append("candidate engine version not bumped to 0.1.1")
    if CANDIDATE_CACHE_SCHEMA_VERSION != 2 or not CACHE_FORMAT.endswith("-v2"):
        errors.append("candidate cache schema not at v2")

    # Status localization
    en_status = format_status(StatusMessage(key="v2_cache_loaded"), "en")
    if assert_status_language(en_status, "en"):
        errors.append("EN v2_cache_loaded status mixed language")
    if "Результат загружен" in en_status:
        errors.append("EN status still contains RU v2 cache phrase")

    # Friendly evidence labels + comparison semantics
    from dataclasses import replace
    from ionogram_morphology_lab.morphology_candidate.types import FeatureValueRef

    inp, _ = fixture_input("oversegmentation")
    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", False, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef(
        "v2_fragmentation_score", 0.91, "score", True, False
    )
    frag_r = evaluate_morphology_candidate(replace(inp, features=feats))
    rows = format_ledger_rows([e.to_dict() for e in frag_r.evidence_ledger], "ru")
    frag_row = next(x for x in rows if x.get("rule_id") == "gate_fragmentation_score")
    if frag_row.get("result") != "порог превышен":
        errors.append("fragmentation row missing threshold-exceeded semantics")
    if "gate_" in frag_row.get("rule", ""):
        errors.append("primary evidence still shows raw rule ids")

    # Geometry review supersession
    with tempfile.TemporaryDirectory() as td:
        base = {
            "review_kind": "geometry_only",
            "source_sha256": "b" * 64,
            "feature_version": "iml2-0.2.0",
            "diagnostics_cache_id": "diagVAL001",
            "status": "acceptable",
            "frame_index": 10,
        }
        p = save_geometry_review_update_in_place(td, dict(base))
        hist = p.parent / "review_f0010_oldvalhist.json"
        hist.write_text(json.dumps({**base, "created_at": "2019-01-01T00:00:00+00:00"}), encoding="utf-8")
        save_geometry_review_update_in_place(td, {**base, "comment": "newer"})
        corpus = load_geometry_review_corpus(td)
        if corpus.logical_reviewed_frames != 1:
            errors.append("supersession: logical frames should be 1")
        if corpus.superseded_reviews < 1:
            errors.append("supersession: older file not marked superseded")
        if corpus.files_found <= corpus.logical_reviewed_frames:
            errors.append("supersession: files_found must exceed logical frames when history exists")

    # Eight-frame audit identities must reference geometry-review JSON fields
    audit = ROOT / "docs" / "PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md"
    if audit.is_file():
        text = audit.read_text(encoding="utf-8")
        if "source_sha256" not in text and "source_sha" not in text:
            errors.append("eight-frame audit missing source identity columns")
        if "review_f" not in text and "review_file" not in text:
            errors.append("eight-frame audit not rebuilt from review JSON identities")
        lowered = text.lower()
        if "8/8 correct" in lowered and "do **not** write" not in lowered and "do not write" not in lowered:
            errors.append("eight-frame audit contains forbidden correctness claim")
    else:
        errors.append("missing PHASE4C1_EIGHT_FRAME_SHADOW_AUDIT.md")

    # Decision-state smoke
    for name in ("freq_strong_h", "no_trace", "blocking_interference", "unrelated_hv"):
        inp, expected = fixture_input(name)
        r = evaluate_morphology_candidate(inp)
        if r.candidate not in ALLOWED_CANDIDATES:
            errors.append(f"{name}: illegal candidate")
        if isinstance(expected, str) and r.candidate != expected:
            errors.append(f"{name}: expected {expected} got {r.candidate}")
        if r.scientifically_validated or r.production_applied:
            errors.append(f"{name}: production/validation flags wrong")

    if errors:
        print("FAIL morphology_candidate_shadow")
        for e in errors:
            print(" -", e)
        return 1
    print("OK morphology_candidate_shadow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
