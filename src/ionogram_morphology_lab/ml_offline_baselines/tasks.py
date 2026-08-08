"""Task-contract and target-label helpers."""
from __future__ import annotations

from typing import Any

from .constants import SUPPORTED_TASK


def _value(item: Any, key: str, default: Any = "") -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def task_supported(task_contract: str) -> bool:
    return task_contract == SUPPORTED_TASK


def task_support_reason(task_contract: str, lang: str = "en") -> str:
    if task_supported(task_contract):
        return ""
    if lang.lower().startswith("ru"):
        return f"ML-C.1 поддерживает только контракт задачи {SUPPORTED_TASK!r}."
    return f"ML-C.1 supports only the {SUPPORTED_TASK!r} task contract."


def target_label_from_item(item: Any) -> str:
    """Use frozen expert target_label, with morphology only as legacy fallback."""
    label = _value(item, "target_label", "")
    if label:
        return str(label)
    return str(_value(item, "morphology", ""))
