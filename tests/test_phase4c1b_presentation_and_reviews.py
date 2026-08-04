"""Phase 4C.1b — localized panel, evidence table, review supersession."""

from __future__ import annotations

import json
from pathlib import Path

from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.fixtures import fixture_input
from ionogram_morphology_lab.morphology_candidate.geometry_review_index import (
    load_geometry_review_corpus,
    save_geometry_review_update_in_place,
)
from ionogram_morphology_lab.morphology_candidate.presentation import (
    cached_return_status,
    contains_canonical_abstention_enum,
    contains_raw_python_dump,
    format_ledger_rows,
    format_panel_text,
    fragmentation_gate_rows,
    ledger_headers,
)
from ionogram_morphology_lab.morphology_candidate.reviews import ledger_hash
from ionogram_morphology_lab.morphology_candidate.types import FeatureValueRef
from dataclasses import replace


def test_ru_panel_has_no_canonical_abstention_enum():
    inp, _ = fixture_input("no_trace")
    r = evaluate_morphology_candidate(inp).to_dict()
    _st, body = format_panel_text(r, lang="ru", v2_status="cached", candidate_status="cached")
    assert "no_valid_ionospheric_trace" not in body
    assert not contains_canonical_abstention_enum(body)
    assert "допустимый ионосферный след" in body.lower() or "след отсутствует" in body.lower()
    # Stored human explanation may also be localized now
    assert "no_valid_ionospheric_trace" not in r["human_explanation_ru"]


def test_en_panel_no_raw_dict():
    inp, _ = fixture_input("freq_strong_h")
    r = evaluate_morphology_candidate(inp).to_dict()
    _st, body = format_panel_text(r, lang="en", v2_status="cached", candidate_status="new")
    assert not contains_raw_python_dump(body)
    assert "{'supported'" not in body


def test_cached_return_status_wording():
    ru = cached_return_status("ru", v2_cached=True, candidate_cached=True)
    en = cached_return_status("en", v2_cached=True, candidate_cached=True)
    assert "Расчёт не выполнялся" in ru
    assert "No computation was performed" in en
    st, _ = format_panel_text(
        evaluate_morphology_candidate(fixture_input("freq_strong_h")[0]).to_dict(),
        lang="en",
        v2_status="cached",
        candidate_status="cached",
    )
    assert "No computation was performed" in st


def test_evidence_ledger_localized_and_hash_stable():
    inp, _ = fixture_input("oversegmentation")
    from ionogram_morphology_lab.morphology_candidate.types import FeatureValueRef

    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", False, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef(
        "v2_fragmentation_score", 0.91, "score", True, False
    )
    r = evaluate_morphology_candidate(replace(inp, features=feats, ambiguity_flags=()))
    ledger = [e.to_dict() for e in r.evidence_ledger]
    h1 = ledger_hash(ledger)
    rows_ru = format_ledger_rows(ledger, "ru")
    rows_en = format_ledger_rows(ledger, "en")
    assert len(rows_ru) == len(ledger) == len(rows_en)
    hdr = ledger_headers("ru")
    assert "Измеренное значение" in hdr
    assert "Сила" in hdr
    # Localized values for booleans
    over = next(x for x in rows_ru if x.get("rule_id") == "gate_oversegmentation_flag")
    assert over["value"] == "нет"
    assert over["effect"] == "Нейтрально"
    assert over["result"] == "условие не сработало"
    frag = next(x for x in rows_ru if x.get("rule_id") == "gate_fragmentation_score")
    assert "0.91" in frag["value"]
    assert frag["effect"] == "Блокирует"
    assert frag["result"] == "порог превышен"
    assert "severe_fragmentation" in r.abstention_reasons
    assert h1 == ledger_hash(ledger)


def test_fragmentation_gate_export_rows():
    inp, _ = fixture_input("oversegmentation")
    feats = dict(inp.features)
    feats["v2_oversegmentation_suspected"] = FeatureValueRef(
        "v2_oversegmentation_suspected", False, "flag", True, False
    )
    feats["v2_fragmentation_score"] = FeatureValueRef(
        "v2_fragmentation_score", 0.88, "score", True, False
    )
    r = evaluate_morphology_candidate(replace(inp, features=feats))
    rows = fragmentation_gate_rows([e.to_dict() for e in r.evidence_ledger])
    assert len(rows) == 2
    by_id = {x["rule_id"]: x for x in rows}
    assert by_id["gate_oversegmentation_flag"]["measured_value"] is False
    assert by_id["gate_oversegmentation_flag"]["support_direction"] == "neutral"
    assert by_id["gate_fragmentation_score"]["measured_value"] == 0.88
    assert by_id["gate_fragmentation_score"]["support_direction"] == "blocks"


def test_geometry_review_supersession_logical_counts(tmp_path: Path):
    # Two saves for same identity + one other frame
    base = {
        "review_kind": "geometry_only",
        "source_sha256": "a" * 64,
        "feature_version": "iml2-0.2.0",
        "diagnostics_cache_id": "diagAAA111",
        "status": "acceptable",
        "not_morphology_ground_truth": True,
    }
    p1 = save_geometry_review_update_in_place(tmp_path, {**base, "frame_index": 421, "comment": "first"})
    # Force a second distinct historical file for same identity
    hist = p1.parent / "review_f0421_oldhist000.json"
    hist.write_text(
        json.dumps({**base, "frame_index": 421, "comment": "old", "created_at": "2020-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    save_geometry_review_update_in_place(tmp_path, {**base, "frame_index": 421, "comment": "second"})
    save_geometry_review_update_in_place(
        tmp_path, {**base, "frame_index": 720, "diagnostics_cache_id": "diagBBB222"}
    )
    corpus = load_geometry_review_corpus(tmp_path)
    assert corpus.files_found >= 3
    assert corpus.logical_reviewed_frames == 2
    assert corpus.current_reviews == 2
    assert corpus.superseded_reviews >= 1
    # Must not count 3 files as 3 independent frames
    assert corpus.logical_reviewed_frames < corpus.files_found


def test_workspace_geometry_corpus_reports_files_and_logical_separately():
    root = Path(__file__).resolve().parents[1]
    proj = root / "workspaces" / "IML_Project_65064ddf202b"
    if not (proj / "feature_diagnostics" / "geometry_reviews").is_dir():
        return
    corpus = load_geometry_review_corpus(proj)
    assert corpus.files_found == 9
    # Never treat file count alone as the independent-frame metric in reports
    summary = corpus.to_dict()
    assert "review_files_found" in summary
    assert "logical_reviewed_frames" in summary
    assert "superseded_reviews" in summary
    assert corpus.logical_reviewed_frames <= corpus.files_found
    assert corpus.current_reviews + corpus.superseded_reviews == corpus.files_found


def test_page_title_i18n_keys():
    root = Path(__file__).resolve().parents[1]
    ru = json.loads((root / "src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    en = json.loads((root / "src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    assert ru["nav.feature_diagnostics"] == "Диагностика следа и геометрии"
    assert en["nav.feature_diagnostics"] == "Trace and Geometry Diagnostics"


def test_evidence_primary_opens_table_not_json():
    root = Path(__file__).resolve().parents[1]
    page = (root / "src/ionogram_morphology_lab/ui/feature_diagnostics_page.py").read_text(encoding="utf-8")
    # Primary Evidence path uses identity-bound EvidenceDialog; raw JSON only via More…
    assert "EvidenceDialog" in page
    assert "act_copy_evidence_json" in page
    assert "act_export_evidence_json" in page
    idx = page.index("def _open_morph_evidence")
    chunk = page[idx : idx + 1200]
    assert "EvidenceDialog" in chunk
    assert "setPlainText(json.dumps" not in chunk
    ev = (root / "src/ionogram_morphology_lab/ui/evidence_dialog.py").read_text(encoding="utf-8")
    assert "QTableWidget" in ev
    assert "Show technical IDs" in ev or "technical" in ev.lower()


def test_real_export_fragmentation_trigger_and_false_overseg():
    """Real V2 export (2014-10-15 frame 1431) must report severe_fragmentation correctly."""
    root = Path(__file__).resolve().parents[1]
    feat = root / "docs/_phase4b3_iml2-0.2.0_diagnostics/Am_all_2014-10-15/frame_1431/features.json"
    if not feat.is_file():
        return
    from ionogram_morphology_lab.morphology_candidate.from_v2 import build_candidate_input_from_v2
    from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset

    ser = json.loads(feat.read_text(encoding="utf-8"))
    rs = load_ruleset()
    inp = build_candidate_input_from_v2(
        ser, diagnostics_cache_id="qa", required_feature_ids=list(rs.get("required_feature_ids") or [])
    )
    r = evaluate_morphology_candidate(inp, ruleset=rs)
    assert "severe_fragmentation" in r.abstention_reasons
    assert "oversegmentation_suspected" not in r.abstention_reasons
    rows = fragmentation_gate_rows([e.to_dict() for e in r.evidence_ledger])
    by_id = {x["rule_id"]: x for x in rows}
    assert by_id["gate_oversegmentation_flag"]["measured_value"] is False
    assert by_id["gate_oversegmentation_flag"]["support_direction"] != "blocks"
    assert isinstance(by_id["gate_fragmentation_score"]["measured_value"], (int, float))
    assert by_id["gate_fragmentation_score"]["support_direction"] == "blocks"
    assert by_id["gate_fragmentation_score"].get("threshold_or_interval") is not None


def test_all_abstention_tokens_have_labels():
    from ionogram_morphology_lab.morphology_candidate.presentation import (
        ABSTENTION_LABELS,
        CANONICAL_ABSTENTION_TOKENS,
        abstention_label,
    )

    required = {
        "no_valid_ionospheric_trace",
        "missing_required_features",
        "incomplete_legacy_cache",
        "oversegmentation_suspected",
        "severe_fragmentation",
        "both_oversegmentation_and_fragmentation",
        "blocking_interference",
        "identity_mismatch",
        "incompatible_feature_version",
        "unrelated_horizontal_vertical_evidence",
        "weak_or_conflicting_evidence",
    }
    assert required <= set(ABSTENTION_LABELS)
    for tok in required:
        assert tok not in abstention_label(tok, "ru")
        assert tok not in abstention_label(tok, "en")
    assert required <= CANONICAL_ABSTENTION_TOKENS
