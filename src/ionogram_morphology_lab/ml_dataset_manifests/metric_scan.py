"""Token-aware forbidden scientific-metric detection for ML-B manifests.

Rejects real performance metric keys/claims. Does NOT flag opaque IDs/hashes
that merely contain metric substrings (e.g. hex ``f1`` inside atomic_group_id).
"""

from __future__ import annotations

import re
from typing import Any

# Keys that must never appear as model-performance fields.
FORBIDDEN_METRIC_KEYS = frozenset(
    {
        "accuracy",
        "accuracy_score",
        "f1",
        "f1_score",
        "precision",
        "recall",
        "sensitivity",
        "specificity",
        "auc",
        "roc_auc",
        "validated_performance",
        "ground_truth",
        "confusion_matrix",
        "error_matrix",
        "accuracy_matrix",
        "inter_rater_kappa",
    }
)

# Opaque identity / hash fields — values are never scanned for metric claims.
_OPAQUE_KEY_EXACT = frozenset(
    {
        "atomic_group_id",
        "group_id",
        "item_id",
        "item_identity_key",
        "identity_key",
        "source_sha256",
        "source_inventory_id",
        "manifest_set_id",
        "manifest_set_hash",
        "manifest_hash",
        "inventory_hash",
        "train_manifest_hash",
        "development_manifest_hash",
        "holdout_public_manifest_hash",
        "holdout_reference_labels_hash",
        "excluded_manifest_hash",
        "holdout_lock_hash",
        "lock_hash",
        "validated_content_hash",
        "public_manifest_hash",
        "reference_labels_hash",
        "result_hash",
        "ledger_hash",
        "ruleset_hash",
        "audit_id",
        "gate_id",
        "cohort_id",
        "project_id",
        "campaign_id",
        "sequence_id",
        "related_frame_group",
        "locked_first_review_id",
        "independent_second_review_id",
        "arbitration_id",
        "parent_manifest_set_id",
        "source_readiness_audit_id",
        "source_readiness_manifest_hash",
        "diagnostics_cache_id",
        "source_display_name",
        "filename",
        "path",
    }
)

_OPAQUE_KEY_SUFFIXES = (
    "_hash",
    "_sha256",
    "_sha1",
    "_uuid",
    "_id",
)

# Human-readable fields where performance claim phrases are meaningful.
_CLAIM_BEARING_KEYS = frozenset(
    {
        "claim",
        "claims",
        "note",
        "note_en",
        "note_ru",
        "description",
        "limitation",
        "limitations",
        "rationale",
        "analyst_rationale",
        "exclusion_reason",
        "revision_reason",
        "comment",
        "summary",
        "title",
        "message",
        "error",
        "errors",
        "warning",
        "warnings",
        "freeze_blockers",
        "required_next_actions",
    }
)

_CLAIM_PATTERNS = [
    re.compile(
        r"\b(?:model\s+)?(?:accuracy|precision|recall|sensitivity|specificity|"
        r"f1(?:[_\s-]?score)?|auc|roc[_\s-]?auc)\b\s*[=:]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:accuracy|f1(?:[_\s-]?score)?|roc[_\s-]?auc)\b\s+(?:is|=)\s+[0-9]",
        re.IGNORECASE,
    ),
]


def normalize_metric_key(key: str) -> str:
    return str(key or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_opaque_identity_key(key: str) -> bool:
    nk = normalize_metric_key(key)
    if not nk:
        return False
    if nk in _OPAQUE_KEY_EXACT:
        return True
    if nk in FORBIDDEN_METRIC_KEYS:
        return False
    return any(nk.endswith(suf) for suf in _OPAQUE_KEY_SUFFIXES)


def is_claim_bearing_key(key: str) -> bool:
    nk = normalize_metric_key(key)
    return nk in _CLAIM_BEARING_KEYS or nk.endswith("_claim") or nk.endswith("_note")


def string_has_performance_claim(text: str) -> bool:
    s = str(text or "")
    if not s.strip():
        return False
    return any(p.search(s) for p in _CLAIM_PATTERNS)


def scan_prohibited_metrics(payload: Any, *, path: str = "$") -> list[str]:
    """Return blocker codes for forbidden metric keys/claims in structured data."""
    hits: list[str] = []
    seen: set[str] = set()

    def _add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            hits.append(code)

    def _walk(node: Any, cur: str, parent_key: str = "") -> None:
        if isinstance(node, dict):
            for raw_key, value in node.items():
                key = str(raw_key)
                nk = normalize_metric_key(key)
                child_path = f"{cur}.{key}"
                if nk in FORBIDDEN_METRIC_KEYS:
                    _add(f"prohibited_metric_payload:{nk}")
                    # Still skip descending into opaque-looking values under metric keys
                    continue
                if is_opaque_identity_key(key):
                    continue
                if isinstance(value, str) and is_claim_bearing_key(key):
                    if string_has_performance_claim(value):
                        _add(f"prohibited_metric_payload:claim:{nk or 'text'}")
                    continue
                _walk(value, child_path, parent_key=key)
            return
        if isinstance(node, list):
            for i, value in enumerate(node):
                _walk(value, f"{cur}[{i}]", parent_key=parent_key)
            return
        if isinstance(node, str) and is_claim_bearing_key(parent_key):
            if string_has_performance_claim(node):
                _add("prohibited_metric_payload:claim:text")

    _walk(payload, path)
    return hits
