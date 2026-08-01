"""Natural-language preview of scientific rules (RU/EN)."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.features.registry import FEATURE_REGISTRY
from ionogram_morphology_lab.rule_builder.model import ScientificRule

_OP_EN = {
    "gt": "is greater than",
    "gte": "is at least",
    "lt": "is less than",
    "lte": "is at most",
    "eq": "equals",
    "ne": "does not equal",
    "between": "is between",
    "outside": "is outside",
    "present": "is present",
    "absent": "is absent",
    "persistent_n": "persists for at least N frames",
    "appears_n_of_m": "appears in at least N of M frames",
}
_OP_RU = {
    "gt": "больше",
    "gte": "не меньше",
    "lt": "меньше",
    "lte": "не больше",
    "eq": "равно",
    "ne": "не равно",
    "between": "находится между",
    "outside": "находится вне",
    "present": "присутствует",
    "absent": "отсутствует",
    "persistent_n": "сохраняется не менее N кадров",
    "appears_n_of_m": "встречается не менее чем в N из M кадров",
}


def _feature_label(name: str, lang: str) -> str:
    meta = FEATURE_REGISTRY.get(name, {})
    if lang == "ru":
        return meta.get("name_ru") or meta.get("interpretation") or name
    return meta.get("name_en") or meta.get("interpretation") or name


def _fmt_cond(cond: dict[str, Any], lang: str) -> str:
    feature = str(cond.get("feature", "?"))
    op = str(cond.get("operator", "gte"))
    value = cond.get("value")
    value2 = cond.get("value2")
    label = _feature_label(feature, lang)
    if lang == "ru":
        op_t = _OP_RU.get(op, op)
        if op == "between":
            return f"{label} {op_t} {value} и {value2}"
        if op in {"present", "absent", "persistent_n", "appears_n_of_m"}:
            extra = f" ({value})" if value is not None else ""
            return f"{label} {op_t}{extra}"
        return f"{label} {op_t} {value}"
    op_t = _OP_EN.get(op, op)
    if op == "between":
        return f"{label} {op_t} {value} and {value2}"
    if op in {"present", "absent", "persistent_n", "appears_n_of_m"}:
        extra = f" ({value})" if value is not None else ""
        return f"{label} {op_t}{extra}"
    return f"{label} {op_t} {value}"


def preview_rule(rule: ScientificRule, lang: str = "en") -> str:
    """Return a plain-language description of the rule."""
    conds = rule.conditions or []
    parts = [_fmt_cond(c, lang) for c in conds if isinstance(c, dict)]
    join = " и " if lang == "ru" else " and "
    body = join.join(parts) if parts else ("(условия не заданы)" if lang == "ru" else "(no conditions)")
    result = rule.proposed_result or next(iter(rule.outputs.values()), "indeterminate")
    excl = ""
    if rule.exclusions:
        if lang == "ru":
            excl = " Не активировать при: " + "; ".join(rule.exclusions) + "."
        else:
            excl = " Do not activate when: " + "; ".join(rule.exclusions) + "."
    abst = ""
    if rule.abstention_condition:
        if lang == "ru":
            abst = f" Воздерживаться, если: {rule.abstention_condition}."
        else:
            abst = f" Abstain when: {rule.abstention_condition}."
    alt = ""
    if rule.alternatives:
        if lang == "ru":
            alt = " Альтернативы: " + ", ".join(rule.alternatives) + "."
        else:
            alt = " Alternatives: " + ", ".join(rule.alternatives) + "."
    if lang == "ru":
        return (
            f"Когда {body}, предложить результат «{result}» "
            f"по оси «{rule.category}» (статус: {rule.status})."
            f"{excl}{abst}{alt}"
        )
    return (
        f"When {body}, propose «{result}» "
        f"on the «{rule.category}» axis (status: {rule.status})."
        f"{excl}{abst}{alt}"
    )


def preview_both(rule: ScientificRule) -> tuple[str, str]:
    return preview_rule(rule, "en"), preview_rule(rule, "ru")
