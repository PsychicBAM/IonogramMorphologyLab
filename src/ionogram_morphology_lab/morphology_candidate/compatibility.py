"""V2 cache compatibility classification for morphology candidates (Phase 4C.1a)."""

from __future__ import annotations

from typing import Any, Mapping

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.morphology_candidate.rules import load_ruleset

COMPATIBLE_COMPLETE = "compatible_complete"
COMPATIBLE_WITH_EXPLICIT_INVALID = "compatible_with_explicit_invalid_features"
INCOMPATIBLE_FEATURE_VERSION = "incompatible_feature_version"
INCOMPLETE_LEGACY_CACHE = "incomplete_legacy_cache"
CORRUPT_CACHE = "corrupt_cache"
IDENTITY_MISMATCH = "identity_mismatch"

COMPATIBILITY_STATES = frozenset(
    {
        COMPATIBLE_COMPLETE,
        COMPATIBLE_WITH_EXPLICIT_INVALID,
        INCOMPATIBLE_FEATURE_VERSION,
        INCOMPLETE_LEGACY_CACHE,
        CORRUPT_CACHE,
        IDENTITY_MISMATCH,
    }
)

LEGACY_INCOMPLETE_MSG = {
    "ru": (
        "Кэш V2 не содержит признаки, необходимые для предварительного "
        "кандидата морфологии. Пересчитайте V2 для этого кадра."
    ),
    "en": (
        "The cached V2 result does not contain the features required by the "
        "provisional morphology candidate. Recalculate V2 for this frame."
    ),
}


def required_feature_ids(ruleset: dict[str, Any] | None = None) -> list[str]:
    rs = ruleset if ruleset is not None else load_ruleset()
    return list(rs.get("required_feature_ids") or [])


def classify_v2_for_candidate(
    ser: Mapping[str, Any] | None,
    *,
    expected_feature_version: str = FEATURE_VERSION,
    expected_source_sha: str | None = None,
    expected_frame_index: int | None = None,
    ruleset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify whether a V2 serializable result can feed the candidate engine."""
    if ser is None or not isinstance(ser, Mapping):
        return {
            "state": CORRUPT_CACHE,
            "missing_feature_ids": [],
            "explicit_invalid_ids": [],
            "message_key": "corrupt_cache",
            "can_evaluate": False,
        }

    fv = str(ser.get("feature_version") or "")
    if fv and fv != expected_feature_version:
        return {
            "state": INCOMPATIBLE_FEATURE_VERSION,
            "missing_feature_ids": [],
            "explicit_invalid_ids": [],
            "message_key": "incompatible_feature_version",
            "can_evaluate": False,
            "feature_version": fv,
        }

    if expected_source_sha and ser.get("source_mat_sha256") and ser.get("source_mat_sha256") != expected_source_sha:
        return {
            "state": IDENTITY_MISMATCH,
            "missing_feature_ids": [],
            "explicit_invalid_ids": [],
            "message_key": "identity_mismatch",
            "can_evaluate": False,
        }

    if expected_frame_index is not None and ser.get("frame_index") is not None:
        if int(ser.get("frame_index")) != int(expected_frame_index):
            return {
                "state": IDENTITY_MISMATCH,
                "missing_feature_ids": [],
                "explicit_invalid_ids": [],
                "message_key": "identity_mismatch",
                "can_evaluate": False,
            }

    features = ser.get("features")
    if not isinstance(features, Mapping):
        return {
            "state": CORRUPT_CACHE,
            "missing_feature_ids": [],
            "explicit_invalid_ids": [],
            "message_key": "corrupt_cache",
            "can_evaluate": False,
        }

    required = required_feature_ids(ruleset)
    missing: list[str] = []
    explicit_invalid: list[str] = []
    for fid in required:
        raw = features.get(fid)
        if raw is None:
            missing.append(fid)
            continue
        if not isinstance(raw, Mapping):
            missing.append(fid)
            continue
        # Present with explicit invalid / not_applicable semantics → OK for evaluation
        valid = bool(raw.get("valid", True))
        value = raw.get("value")
        reason = str(raw.get("reason_invalid") or "")
        meta = raw.get("metadata") or {}
        not_applicable = (
            str(meta.get("status") or "").lower() in {"not_applicable", "n_a"}
            or "not_applicable" in reason.lower()
            or reason.lower() in {"trace_not_found", "no_trace", "not_applicable"}
        )
        if not valid and value is None and not not_applicable and not reason:
            # Ambiguous null without reason — treat as legacy omission if key barely present
            if "feature_id" not in raw and "unit" not in raw:
                missing.append(fid)
            else:
                explicit_invalid.append(fid)
        elif not valid:
            explicit_invalid.append(fid)

    if missing:
        return {
            "state": INCOMPLETE_LEGACY_CACHE,
            "missing_feature_ids": missing,
            "explicit_invalid_ids": explicit_invalid,
            "message_key": "incomplete_legacy_cache",
            "can_evaluate": False,
        }

    if explicit_invalid:
        return {
            "state": COMPATIBLE_WITH_EXPLICIT_INVALID,
            "missing_feature_ids": [],
            "explicit_invalid_ids": explicit_invalid,
            "message_key": "compatible_with_explicit_invalid_features",
            "can_evaluate": True,
        }

    return {
        "state": COMPATIBLE_COMPLETE,
        "missing_feature_ids": [],
        "explicit_invalid_ids": [],
        "message_key": "compatible_complete",
        "can_evaluate": True,
    }


def legacy_incomplete_message(lang: str) -> str:
    return LEGACY_INCOMPLETE_MSG.get(lang, LEGACY_INCOMPLETE_MSG["en"])
