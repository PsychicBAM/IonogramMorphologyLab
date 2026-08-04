"""High-level candidate evaluation helpers (no MAT/V2 side effects)."""

from __future__ import annotations

from typing import Any, Mapping

from ionogram_morphology_lab.morphology_candidate.cache import (
    MorphologyCandidateCache,
    make_candidate_cache_key,
)
from ionogram_morphology_lab.morphology_candidate.compatibility import (
    INCOMPLETE_LEGACY_CACHE,
    classify_v2_for_candidate,
)
from ionogram_morphology_lab.morphology_candidate.engine import evaluate_morphology_candidate
from ionogram_morphology_lab.morphology_candidate.from_v2 import build_candidate_input_from_v2
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset, ruleset_hash
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION


def resolve_or_evaluate_candidate(
    ser: Mapping[str, Any],
    *,
    diagnostics_cache_id: str,
    cache: MorphologyCandidateCache,
    profile_id: str = "",
    signal_contract_id: str = "",
    temporal_context_signature: str = "",
    force: bool = False,
    interpreted_time: str = "",
) -> dict[str, Any]:
    """Load candidate cache or evaluate. Never opens MAT / never runs V2.

    Returns a status envelope:
      status: candidate_cached|candidate_new|v2_incomplete_legacy|candidate_error|...
      result: dict|None
      compatibility: dict
    """
    rs = load_ruleset()
    compat = classify_v2_for_candidate(ser, ruleset=rs)
    if not compat.get("can_evaluate"):
        return {
            "status": "v2_incomplete_legacy"
            if compat.get("state") == INCOMPLETE_LEGACY_CACHE
            else str(compat.get("state") or "candidate_error"),
            "result": None,
            "compatibility": compat,
            "evaluated": False,
            "cache_hit": False,
        }

    source_sha = str(ser.get("source_mat_sha256") or "")
    frame_index = int(ser.get("frame_index") or 0)
    key = make_candidate_cache_key(
        source_sha256=source_sha,
        frame_index=frame_index,
        profile_id=profile_id or str(ser.get("profile_id") or ""),
        signal_contract_id=signal_contract_id or str(ser.get("signal_contract_id") or ""),
        feature_version=str(ser.get("feature_version") or FEATURE_VERSION),
        diagnostics_cache_id=diagnostics_cache_id,
        ruleset_version=str(rs.get("ruleset_version")),
        ruleset_hash=ruleset_hash(rs),
        temporal_context_signature=temporal_context_signature,
    )
    if not force:
        lu = cache.lookup(key)
        if lu.hit and lu.result is not None:
            return {
                "status": "candidate_cached",
                "result": lu.result,
                "compatibility": compat,
                "evaluated": False,
                "cache_hit": True,
                "miss_reason": None,
                "key_digest": lu.key_digest,
            }
        # Surface schema incompatibility without evaluating
        if lu.miss_reason in {
            "incompatible_candidate_cache_schema",
            "incompatible_ledger_schema",
            "missing_required_ledger_entries",
        }:
            # Fall through to evaluate only when force=True; otherwise report miss
            pass

    try:
        inp = build_candidate_input_from_v2(
            ser,
            diagnostics_cache_id=diagnostics_cache_id,
            interpreted_time=interpreted_time,
            required_feature_ids=list(rs.get("required_feature_ids") or []),
        )
        cache.counters.candidate_engine_evaluation_count += 1
        result = evaluate_morphology_candidate(inp)
        payload = result.to_dict()
        cache.put(key, payload)
        return {
            "status": "candidate_new",
            "result": payload,
            "compatibility": compat,
            "evaluated": True,
            "cache_hit": False,
            "key_digest": key.digest(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "candidate_error",
            "result": None,
            "compatibility": compat,
            "evaluated": False,
            "cache_hit": False,
            "error": str(exc),
        }


def geometry_review_status_for_frame(
    project_root: str | None,
    *,
    source_sha256: str,
    frame_index: int,
) -> str:
    """Informational only — never gates candidate eligibility."""
    if not project_root:
        return "geometry_unreviewed"
    from pathlib import Path
    import json

    d = Path(project_root) / "feature_diagnostics" / "geometry_reviews"
    if not d.is_dir():
        return "geometry_unreviewed"
    for p in d.glob(f"review_f{int(frame_index):04d}_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(data.get("source_sha256") or "") == source_sha256:
            return "geometry_reviewed"
    return "geometry_unreviewed"
