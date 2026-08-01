from __future__ import annotations

from typing import Any

OPS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "exists",
    "present",
    "absent",
    "between",
    "outside",
}


def _one(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    feature = condition.get("feature")
    op = condition.get("operator", "gte")
    # aliases
    aliases = {
        "greater than": "gt",
        "greater than or equal": "gte",
        "less than": "lt",
        "less than or equal": "lte",
        "equal": "eq",
        "not equal": "ne",
    }
    op = aliases.get(str(op), op)
    if op not in OPS:
        raise ValueError(f"Unsupported operator: {op}")
    present = feature in features
    actual = features.get(feature)
    expected = condition.get("value")
    if op in {"exists", "present"}:
        return present and actual is not None
    if op == "absent":
        return (not present) or actual is None
    if not present:
        return False
    if op == "between":
        lo, hi = expected if isinstance(expected, (list, tuple)) and len(expected) == 2 else (condition.get("min"), condition.get("max"))
        return lo is not None and hi is not None and lo <= actual <= hi
    if op == "outside":
        lo, hi = expected if isinstance(expected, (list, tuple)) and len(expected) == 2 else (condition.get("min"), condition.get("max"))
        return lo is not None and hi is not None and (actual < lo or actual > hi)
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    if op == "in":
        return actual in expected
    return actual not in expected


def evaluate_conditions(features: dict[str, Any], conditions: list[dict[str, Any]]) -> bool:
    """Evaluate AND conditions; each may contain an explicit any_of OR group."""
    return all(
        any(_one(features, c) for c in condition["any_of"])
        if "any_of" in condition
        else _one(features, condition)
        for condition in conditions
    )
