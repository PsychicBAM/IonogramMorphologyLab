"""Derive rule comparison-result tokens from ledger fields (presentation + engine)."""

from __future__ import annotations

from typing import Any, Mapping


def derive_comparison_result(
    *,
    validity: str,
    comparison: str,
    measured_value: Any,
    threshold_or_interval: Any,
    support_direction: str,
    comparison_result: str | None = None,
) -> str:
    """Return a stable comparison-result token separate from input validity."""
    if comparison_result:
        return str(comparison_result)
    cmp_s = str(comparison or "")
    validity = str(validity or "")
    if validity in {"missing", "insufficient", "absent"}:
        return "not_applicable"
    if validity == "invalid":
        return "condition_not_met"

    # Boolean gate: ==true
    if cmp_s in {"==true", "== true"} or (
        isinstance(threshold_or_interval, bool) and threshold_or_interval is True and "true" in cmp_s
    ):
        if measured_value is True:
            return "condition_met"
        return "condition_not_met"

    # Numeric threshold: >= / >
    if cmp_s.startswith(">=") or cmp_s.startswith(">"):
        try:
            thr = float(threshold_or_interval) if not isinstance(threshold_or_interval, dict) else None
            val = float(measured_value) if measured_value is not None else None
        except (TypeError, ValueError):
            thr = None
            val = None
        if thr is not None and val is not None:
            if val >= thr:
                return "threshold_exceeded"
            return "below_threshold"

    if "membership" in cmp_s or cmp_s == "in" or isinstance(threshold_or_interval, (list, tuple)):
        if support_direction in {"blocks", "opposes"} and validity == "invalid":
            return "membership_failed"
        if support_direction == "blocks":
            # e.g. quality not in allowed set recorded as valid measured + blocks
            return "membership_failed" if measured_value not in (threshold_or_interval or []) else "membership_passed"
        return "membership_passed"

    if support_direction == "blocks":
        return "condition_met"
    if support_direction in {"supports", "supports_frequency", "supports_range", "supports_both"}:
        return "condition_met"
    if support_direction == "opposes":
        return "condition_met"
    return "condition_not_met"


def comparison_result_from_entry(entry: Mapping[str, Any]) -> str:
    return derive_comparison_result(
        validity=str(entry.get("validity") or ""),
        comparison=str(entry.get("comparison") or ""),
        measured_value=entry.get("measured_value"),
        threshold_or_interval=entry.get("threshold_or_interval"),
        support_direction=str(entry.get("support_direction") or "neutral"),
        comparison_result=entry.get("comparison_result") or None,
    )
