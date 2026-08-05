"""Procedural UI blinding helpers (not cryptographic protection)."""

from __future__ import annotations

from typing import Any

# Columns / keys that must stay hidden during blind review
CANDIDATE_UI_KEYS = frozenset(
    {
        "candidate_class",
        "candidate_state",
        "candidate_strength",
        "ordinal_strength",
        "evidence_ledger",
        "candidate_thresholds",
        "candidate_status",
        "candidate_result_hash",
        "ruleset_hash",
        "agreement",
        "agreement_status",
        "provisional_morphology",
        "candidate_summary",
        "evidence_ledger_hash",
    }
)

BLINDING_DISCLAIMER_EN = (
    "Blind mode hides the morphology candidate procedurally in the UI. "
    "This is not cryptographic protection."
)
BLINDING_DISCLAIMER_RU = (
    "Слепой режим процедурно скрывает кандидата морфологии в интерфейсе. "
    "Это не криптографическая защита."
)


def strip_candidate_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy without candidate-derived fields for blind presentation/export."""
    out = {}
    for k, v in payload.items():
        if k in CANDIDATE_UI_KEYS or k.startswith("candidate_"):
            continue
        if isinstance(v, dict):
            out[k] = strip_candidate_fields(v)
        else:
            out[k] = v
    return out


def queue_columns(*, blind: bool) -> list[str]:
    base = [
        "manifest_position",
        "source_display_name",
        "frame_time",
        "item_status",
        "availability",
        "first_review",
        "second_review",
        "adjudication",
        "reveal_comparison",
    ]
    if not blind:
        base.extend(["candidate_state", "agreement_status"])
    return base


def may_show_candidate(*, blind_locked: bool) -> bool:
    return bool(blind_locked)
