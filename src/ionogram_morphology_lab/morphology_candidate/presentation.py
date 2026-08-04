"""Localized presentation helpers for morphology candidate UI (no raw Python dumps)."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ionogram_morphology_lab.morphology_candidate.labels import (
    candidate_label,
    disclaimer,
    strength_label,
)

# Canonical tokens that must never appear in normal RU/EN panel text.
CANONICAL_ABSTENTION_TOKENS = frozenset(
    {
        "no_valid_ionospheric_trace",
        "missing_required_features",
        "incomplete_legacy_cache",
        "incomplete_legacy_v2_cache",
        "oversegmentation_suspected",
        "severe_fragmentation",
        "both_oversegmentation_and_fragmentation",
        "blocking_interference",
        "identity_mismatch",
        "geometry_result_identity_mismatch",
        "incompatible_feature_version",
        "unrelated_horizontal_vertical_evidence",
        "unrelated_h_v_regions",
        "weak_or_conflicting_evidence",
        "weak_boundary_evidence",
        "weak_axis_evidence",
        "h_v_without_coexistence",
        "oversegmentation_or_severe_fragmentation",
        "geometry_or_quality_not_assessable",
        "temporal_contradiction",
        "incomplete_identity",
        "trace_pixel_fraction_below_minimum",
        "insufficient_accepted_support_above_floor",
        "high_interference_residual_uncertainty",
    }
)

ENUM_LABELS = {
    "assessable": {"ru": "Оценка возможна", "en": "Assessable"},
    "not_assessable": {"ru": "Оценка невозможна", "en": "Not assessable"},
    "indeterminate": {"ru": "Неопределённо", "en": "Indeterminate"},
    "none": {"ru": "Нет", "en": "None"},
    "low": {"ru": "Низкие", "en": "Low"},
    "weak": {"ru": "Слабая", "en": "Weak"},
    "moderate": {"ru": "Умеренная", "en": "Moderate"},
    "strong": {"ru": "Сильная", "en": "Strong"},
    "high": {"ru": "Высокие", "en": "High"},
    "blocking": {"ru": "Блокирующие", "en": "Blocking"},
    "unknown": {"ru": "Неизвестно", "en": "Unknown"},
    "unavailable": {"ru": "Недоступно", "en": "Unavailable"},
    "valid": {"ru": "Данные допустимы", "en": "Data valid"},
    "invalid": {"ru": "Данные недействительны", "en": "Data invalid"},
    "insufficient": {"ru": "Данных недостаточно", "en": "Insufficient data"},
    "not_applicable": {"ru": "Не применимо", "en": "Not applicable"},
    "missing": {"ru": "Отсутствует", "en": "Missing"},
    "absent": {"ru": "Отсутствует", "en": "Absent"},
    "categorical": {"ru": "категория", "en": "category"},
    "flag": {"ru": "флаг", "en": "flag"},
    "score": {"ru": "оценка", "en": "score"},
    "fraction": {"ru": "доля", "en": "fraction"},
    "version": {"ru": "версия", "en": "version"},
    "condition_met": {"ru": "условие выполнено", "en": "condition met"},
    "condition_not_met": {"ru": "условие не сработало", "en": "condition not met"},
    "threshold_exceeded": {"ru": "порог превышен", "en": "threshold exceeded"},
    "below_threshold": {"ru": "ниже порога", "en": "below threshold"},
    "membership_passed": {"ru": "входит в допустимый набор", "en": "membership passed"},
    "membership_failed": {"ru": "не входит в допустимый набор", "en": "membership failed"},
    "supports": {"ru": "Поддерживает", "en": "Supports"},
    "supports_frequency": {"ru": "Поддерживает частотное", "en": "Supports frequency"},
    "supports_range": {"ru": "Поддерживает высотное", "en": "Supports range"},
    "supports_both": {"ru": "Поддерживает оба", "en": "Supports both"},
    "blocks": {"ru": "Блокирует", "en": "Blocks"},
    "opposes": {"ru": "Противоречит", "en": "Opposes"},
    "neutral": {"ru": "Нейтрально", "en": "Neutral"},
    "true": {"ru": "да", "en": "true"},
    "false": {"ru": "нет", "en": "false"},
    "cached": {"ru": "из кэша", "en": "from cache"},
    "new": {"ru": "новый расчёт", "en": "newly evaluated"},
    "recomputed": {"ru": "пересчитан", "en": "recalculated"},
    "not_computed": {"ru": "не рассчитан", "en": "not calculated"},
    "not_calculated": {"ru": "не рассчитан", "en": "not calculated"},
    "v2_incomplete_legacy": {"ru": "нужен пересчёт V2", "en": "V2 recalculation required"},
    "v2_missing": {"ru": "нет V2", "en": "V2 missing"},
    "candidate_error": {"ru": "ошибка кандидата", "en": "candidate error"},
    "candidate_cached": {"ru": "кандидат из кэша", "en": "candidate from cache"},
    "candidate_new": {"ru": "кандидат новый", "en": "candidate newly evaluated"},
    "candidate_not_calculated": {"ru": "кандидат не рассчитан", "en": "candidate not calculated"},
}

RULE_LABELS = {
    "gate_quality_status": {"ru": "Проверка качества", "en": "Quality gate"},
    "gate_oversegmentation_flag": {"ru": "Проверка пересегментации", "en": "Oversegmentation gate"},
    "gate_fragmentation_score": {"ru": "Проверка фрагментации", "en": "Fragmentation gate"},
    "gate_feature_version": {"ru": "Проверка версии признаков", "en": "Feature-version gate"},
    "gate_trace_present": {"ru": "Проверка наличия следа", "en": "Trace-presence gate"},
    "gate_interference_blocking": {"ru": "Проверка блокирующих помех", "en": "Blocking-interference gate"},
    "gate_geometry_status": {"ru": "Проверка геометрии", "en": "Geometry gate"},
}

FEATURE_LABELS = {
    "v2_quality_status": {"ru": "Статус качества", "en": "Quality status"},
    "v2_oversegmentation_suspected": {"ru": "Подозрение на пересегментацию", "en": "Oversegmentation suspected"},
    "v2_fragmentation_score": {"ru": "Оценка фрагментации", "en": "Fragmentation score"},
    "feature_version": {"ru": "Версия признаков", "en": "Feature version"},
    "v2_trace_pixel_fraction": {"ru": "Доля пикселей следа", "en": "Trace pixel fraction"},
    "v2_interference_level": {"ru": "Уровень помех", "en": "Interference level"},
}

VALIDITY_LABELS = {
    "valid": {"ru": "Данные допустимы", "en": "Data valid"},
    "invalid": {"ru": "Данные недействительны", "en": "Data invalid"},
    "insufficient": {"ru": "Данных недостаточно", "en": "Insufficient data"},
    "not_applicable": {"ru": "Не применимо", "en": "Not applicable"},
    "missing": {"ru": "Отсутствует", "en": "Missing"},
    "absent": {"ru": "Отсутствует", "en": "Absent"},
}

ABSTENTION_LABELS = {
    "no_valid_ionospheric_trace": {
        "ru": "допустимый ионосферный след отсутствует",
        "en": "no usable ionospheric trace is available",
    },
    "oversegmentation_suspected": {
        "ru": "подозрение на пересегментацию",
        "en": "oversegmentation is suspected",
    },
    "severe_fragmentation": {
        "ru": "сильная фрагментация геометрии",
        "en": "severe geometry fragmentation",
    },
    "both_oversegmentation_and_fragmentation": {
        "ru": "пересегментация и сильная фрагментация",
        "en": "oversegmentation and severe fragmentation",
    },
    "oversegmentation_or_severe_fragmentation": {
        "ru": "пересегментация или сильная фрагментация",
        "en": "oversegmentation or severe fragmentation",
    },
    "blocking_interference": {
        "ru": "блокирующие помехи",
        "en": "blocking interference",
    },
    "missing_required_features": {
        "ru": "отсутствуют обязательные признаки",
        "en": "required features are missing",
    },
    "incomplete_legacy_cache": {
        "ru": "неполный устаревший кэш V2",
        "en": "incomplete legacy V2 cache",
    },
    "incomplete_legacy_v2_cache": {
        "ru": "неполный устаревший кэш V2",
        "en": "incomplete legacy V2 cache",
    },
    "geometry_or_quality_not_assessable": {
        "ru": "геометрия или качество не позволяют оценку",
        "en": "geometry or quality does not allow assessment",
    },
    "weak_boundary_evidence": {
        "ru": "слабые пограничные доказательства",
        "en": "weak or conflicting evidence",
    },
    "weak_or_conflicting_evidence": {
        "ru": "слабые или противоречивые доказательства",
        "en": "weak or conflicting evidence",
    },
    "unrelated_h_v_regions": {
        "ru": "H и V доказательства в несвязанных областях",
        "en": "horizontal and vertical evidence are in unrelated regions",
    },
    "unrelated_horizontal_vertical_evidence": {
        "ru": "H и V доказательства в несвязанных областях",
        "en": "horizontal and vertical evidence are in unrelated regions",
    },
    "h_v_without_coexistence": {
        "ru": "H и V без подтверждённого сосуществования",
        "en": "H and V without confirmed coexistence",
    },
    "weak_axis_evidence": {
        "ru": "слабая осевая поддержка",
        "en": "weak axis evidence",
    },
    "temporal_contradiction": {
        "ru": "противоречие соседних кадров",
        "en": "temporal contradiction",
    },
    "geometry_result_identity_mismatch": {
        "ru": "несовпадение идентичности результата V2",
        "en": "V2 result identity mismatch",
    },
    "identity_mismatch": {
        "ru": "несовпадение идентичности",
        "en": "identity mismatch",
    },
    "incompatible_feature_version": {
        "ru": "несовместимая версия признаков",
        "en": "incompatible feature version",
    },
    "incomplete_identity": {
        "ru": "неполная идентичность входа",
        "en": "incomplete input identity",
    },
    "trace_pixel_fraction_below_minimum": {
        "ru": "доля пикселей следа ниже минимума",
        "en": "trace pixel fraction below minimum",
    },
    "insufficient_accepted_support_above_floor": {
        "ru": "недостаточно поддержки следа выше пола",
        "en": "insufficient accepted support above floor",
    },
    "high_interference_residual_uncertainty": {
        "ru": "высокие помехи оставляют неопределённость",
        "en": "high interference leaves residual uncertainty",
    },
}


def enum_label(token: str | None, lang: str) -> str:
    if token is None or token == "":
        return "—"
    key = str(token)
    entry = ENUM_LABELS.get(key)
    if entry:
        return entry.get(lang, entry.get("en", key))
    return key


def abstention_label(reason: str, lang: str) -> str:
    if reason.startswith("missing:"):
        return (
            f"отсутствует признак ({reason.split(':', 1)[1]})"
            if lang == "ru"
            else f"missing feature ({reason.split(':', 1)[1]})"
        )
    entry = ABSTENTION_LABELS.get(reason)
    if entry:
        return entry.get(lang, entry["en"])
    # Never leak snake_case enums into UI
    return reason.replace("_", " ")


def format_abstention_sentence(reasons: list[str], lang: str) -> str:
    if not reasons:
        return "—"
    joined = "; ".join(abstention_label(r, lang) for r in reasons)
    if lang == "ru":
        return f"Оценка невозможна: {joined}."
    return f"Assessment is not possible because {joined}."


def localized_concise_explanation(result: Mapping[str, Any], lang: str) -> str:
    """Build a concise user-facing explanation without canonical enums or disclaimer."""
    cand = str(result.get("candidate") or "")
    strength = str(result.get("evidence_strength") or "none")
    reasons = list(result.get("abstention_reasons") or [])
    inter = (result.get("interference") or {}).get("level")
    if cand == "not_assessable":
        base = format_abstention_sentence(reasons, lang)
        extra = (
            " Геометрия могла быть приемлемой без классифицируемой морфологии рассеяния."
            if lang == "ru"
            else " Geometry may be acceptable without a classifiable spread morphology."
        )
        return (base + extra).strip()
    if cand == "indeterminate" or result.get("abstained"):
        why = "; ".join(abstention_label(r, lang) for r in reasons) if reasons else (
            "доказательства слабые или противоречивы" if lang == "ru" else "evidence is weak or conflicting"
        )
        if lang == "ru":
            return (
                f"{candidate_label(cand, 'ru')}, сила доказательств: {strength_label(strength, 'ru')}. "
                f"Причина: {why}. Помехи: {interference_label(inter, lang)}."
            )
        return (
            f"{candidate_label(cand, 'en')}, evidence strength: {strength_label(strength, 'en')}. "
            f"Reason: {why}. Interference: {interference_label(inter, lang)}."
        )
    if lang == "ru":
        return (
            f"{candidate_label(cand, 'ru')}, сила доказательств: {strength_label(strength, 'ru')}. "
            f"Помехи: {interference_label(inter, lang)}. Результат предварительный."
        )
    return (
        f"{candidate_label(cand, 'en')}, evidence strength: {strength_label(strength, 'en')}. "
        f"Interference: {interference_label(inter, lang)}. Result is provisional."
    )


def axis_support_label(supported: bool, strength: str, lang: str) -> str:
    if not supported:
        return "Не поддерживается" if lang == "ru" else "Not supported"
    s = strength_label(strength, lang)
    return f"Поддерживается ({s})" if lang == "ru" else f"Supported ({s})"


def coexistence_label(summary: Mapping[str, Any] | None, lang: str) -> str:
    summary = summary or {}
    if summary.get("coexistence_supported"):
        return "Подтверждена" if lang == "ru" else "Confirmed"
    if summary.get("unrelated_hv"):
        return (
            "Не подтверждена (несвязанные области)"
            if lang == "ru"
            else "Not confirmed (unrelated regions)"
        )
    return "Не подтверждена" if lang == "ru" else "Not confirmed"


def interference_label(level: str | None, lang: str) -> str:
    if level in {None, "", "unknown", "unavailable"}:
        return enum_label("unavailable", lang)
    mapping = {
        "none": {"ru": "Нет", "en": "None"},
        "low": {"ru": "Низкие", "en": "Low"},
        "moderate": {"ru": "Умеренные", "en": "Moderate"},
        "high": {"ru": "Высокие", "en": "High"},
        "blocking": {"ru": "Блокирующие", "en": "Blocking"},
    }
    e = mapping.get(str(level), {})
    return e.get(lang) or enum_label(str(level), lang)


def temporal_label(summary: Mapping[str, Any] | None, lang: str) -> str:
    summary = summary or {}
    if not summary.get("present"):
        return "Нет (одиночный кадр)" if lang == "ru" else "None (single frame)"
    if summary.get("isolated_candidate_flag"):
        return "Изолированный кандидат" if lang == "ru" else "Isolated candidate"
    n = int(summary.get("persistence_count") or 0)
    if n > 0:
        return (
            f"Есть (устойчивость: {n})"
            if lang == "ru"
            else f"Present (persistence: {n})"
        )
    return "Есть" if lang == "ru" else "Present"


def cached_return_status(lang: str, *, v2_cached: bool, candidate_cached: bool) -> str:
    if v2_cached and candidate_cached:
        if lang == "ru":
            return (
                "V2 загружен из кэша; кандидат загружен из кэша.\n"
                "Расчёт не выполнялся."
            )
        return (
            "V2 loaded from cache; candidate loaded from cache.\n"
            "No computation was performed."
        )
    if v2_cached and not candidate_cached:
        return (
            "V2 загружен из кэша; кандидат не рассчитан."
            if lang == "ru"
            else "V2 loaded from cache; candidate not calculated."
        )
    return ""


def format_panel_text(
    result: Mapping[str, Any] | None,
    *,
    lang: str,
    v2_status: str,
    candidate_status: str,
    compatibility_state: str | None = None,
    empty_hint: str = "",
) -> tuple[str, str]:
    """Return (status_line, body_text) with no raw dict/tuple dumps or canonical enums."""
    if compatibility_state == "incomplete_legacy_cache":
        from ionogram_morphology_lab.morphology_candidate.compatibility import legacy_incomplete_message

        status = (
            f"V2={enum_label(v2_status if v2_status != 'not_computed' else 'not_calculated', lang)}; "
            f"{enum_label('v2_incomplete_legacy', lang)}"
        )
        return status, legacy_incomplete_message(lang)

    v2_cached = v2_status in {"cached"}
    cand_cached = candidate_status in {"cached", "candidate_cached"}
    if v2_cached and cand_cached and result:
        status = cached_return_status(lang, v2_cached=True, candidate_cached=True)
    elif v2_status == "recomputed":
        status = (
            f"V2={enum_label('recomputed', lang)}; "
            f"{'кандидат' if lang == 'ru' else 'candidate'}="
            f"{enum_label(candidate_status if candidate_status != 'not_computed' else 'not_calculated', lang)}"
        )
    else:
        status = (
            f"V2={enum_label(v2_status if v2_status != 'not_computed' else 'not_calculated', lang)}; "
            f"{'кандидат' if lang == 'ru' else 'candidate'}="
            f"{enum_label(candidate_status if candidate_status != 'not_computed' else 'not_calculated', lang)}"
        )

    if not result:
        return status, empty_hint

    cand = str(result.get("candidate") or "")
    h = result.get("h_evidence") or {}
    v = result.get("v_evidence") or {}
    inter = result.get("interference") or {}
    reasons = list(result.get("abstention_reasons") or [])
    reason_txt = "; ".join(abstention_label(r, lang) for r in reasons) if reasons else "—"
    warn = list(result.get("warnings") or [])
    warn_txt = "; ".join(str(w).replace("_", " ") for w in warn) if warn else "—"

    lines = [
        f"{'Кандидат' if lang == 'ru' else 'Candidate'}:",
        candidate_label(cand, lang),
        f"{'Оценимость' if lang == 'ru' else 'Assessability'}:",
        enum_label(str(result.get("assessability") or ""), lang),
        f"{'Сила доказательств' if lang == 'ru' else 'Evidence strength'}:",
        strength_label(str(result.get("evidence_strength") or "none"), lang),
        f"{'Горизонтальная поддержка' if lang == 'ru' else 'Horizontal support'}:",
        axis_support_label(bool(h.get("supported")), str(h.get("strength") or "none"), lang),
        f"{'Вертикальная поддержка' if lang == 'ru' else 'Vertical support'}:",
        axis_support_label(bool(v.get("supported")), str(v.get("strength") or "none"), lang),
        f"{'Совместная H/V-поддержка' if lang == 'ru' else 'Joint H/V support'}:",
        coexistence_label(result.get("coexistence_summary"), lang),
        f"{'Помехи' if lang == 'ru' else 'Interference'}:",
        interference_label(inter.get("level"), lang),
        f"{'Временная поддержка' if lang == 'ru' else 'Temporal support'}:",
        temporal_label(result.get("temporal_summary"), lang),
        f"{'Причина воздержания' if lang == 'ru' else 'Abstention reason'}:",
        reason_txt,
        f"{'Предупреждения' if lang == 'ru' else 'Warnings'}:",
        warn_txt,
        f"{'Набор правил' if lang == 'ru' else 'Ruleset'}:",
        str(result.get("ruleset_version") or "—"),
        "",
        localized_concise_explanation(result, lang),
    ]
    body = "\n".join(lines).strip()
    disc = disclaimer(lang)
    body = body.replace(disc, "").strip()
    # Final guard: strip any leaked canonical tokens
    for tok in CANONICAL_ABSTENTION_TOKENS:
        if tok in body:
            body = body.replace(tok, abstention_label(tok, lang))
    return status, body


def rule_label(rule_id: str, lang: str) -> str:
    entry = RULE_LABELS.get(rule_id)
    if entry:
        return entry.get(lang, entry.get("en", rule_id))
    # Friendly fallback: gate_foo_bar → gate foo bar
    return rule_id.replace("_", " ")


def feature_label(feature_id: str, lang: str) -> str:
    entry = FEATURE_LABELS.get(feature_id)
    if entry:
        return entry.get(lang, entry.get("en", feature_id))
    return feature_id.replace("_", " ").removeprefix("v2 ")


def unit_label(unit: str, lang: str) -> str:
    return enum_label(unit, lang) if unit else "—"


def validity_label(token: str, lang: str) -> str:
    entry = VALIDITY_LABELS.get(token)
    if entry:
        return entry.get(lang, entry["en"])
    return enum_label(token, lang)


def comparison_result_label(token: str, lang: str) -> str:
    return enum_label(token, lang)


def _format_measured_value(val: Any, lang: str) -> str:
    if val is None:
        return "—"
    if isinstance(val, bool):
        return enum_label("true" if val else "false", lang)
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, dict):
        if "floor" in val and "stripe" in val:
            return f"floor={val.get('floor')}; stripe={val.get('stripe')}"
        return "—"
    if isinstance(val, (list, tuple)):
        parts = [_format_measured_value(x, lang) for x in val]
        return ", ".join(parts) if parts else "—"
    s = str(val)
    if s.lower() in {"true", "false"}:
        return enum_label(s.lower(), lang)
    # Categorical status tokens
    if s in ENUM_LABELS or s in VALIDITY_LABELS:
        return enum_label(s, lang) if s in ENUM_LABELS else validity_label(s, lang)
    if s.startswith("[") and "'" in s:
        # Python-style list string — never show raw
        return (
            "Статус входит в список допустимых"
            if lang == "ru"
            else "Status belongs to the accepted set"
        )
    return s.replace("_", " ")


def _format_condition(e: Mapping[str, Any], lang: str) -> str:
    thr = e.get("threshold_or_interval")
    cmp_s = str(e.get("comparison") or "")
    if "membership" in cmp_s or isinstance(thr, (list, tuple)):
        return (
            "Статус входит в список допустимых"
            if lang == "ru"
            else "Status belongs to the accepted set"
        )
    if isinstance(thr, bool):
        return (
            ("истина" if thr else "ложь")
            if lang == "ru"
            else ("true" if thr else "false")
        )
    if isinstance(thr, (int, float)):
        return str(thr)
    if isinstance(thr, dict):
        return (
            "Составное условие"
            if lang == "ru"
            else "Composite condition"
        )
    if thr is None:
        return "—"
    return _format_measured_value(thr, lang)


def format_ledger_rows(
    ledger: list[Mapping[str, Any]] | tuple,
    lang: str,
    *,
    show_technical_ids: bool = False,
) -> list[dict[str, str]]:
    from ionogram_morphology_lab.morphology_candidate.comparison_result import (
        comparison_result_from_entry,
    )

    rows = []
    for e in ledger:
        if not isinstance(e, Mapping):
            continue
        rule_id = str(e.get("rule_id") or "")
        feature_id = str(e.get("feature_id") or "")
        cmp_res = comparison_result_from_entry(e)
        expl = str(
            e.get("human_explanation_ru" if lang == "ru" else "human_explanation_en") or ""
        )
        for tok in CANONICAL_ABSTENTION_TOKENS:
            if tok in expl:
                expl = expl.replace(tok, abstention_label(tok, lang))
        rule_disp = rule_label(rule_id, lang)
        feat_disp = feature_label(feature_id, lang)
        if show_technical_ids:
            rule_disp = f"{rule_disp} ({rule_id})" if rule_id else rule_disp
            feat_disp = f"{feat_disp} ({feature_id})" if feature_id else feat_disp
        rows.append(
            {
                "rule": rule_disp,
                "feature": feat_disp,
                "value": _format_measured_value(e.get("measured_value"), lang),
                "unit": unit_label(str(e.get("unit") or ""), lang),
                "condition": _format_condition(e, lang),
                "data_validity": validity_label(str(e.get("validity") or ""), lang),
                "result": comparison_result_label(cmp_res, lang),
                "effect": enum_label(str(e.get("support_direction") or "neutral"), lang),
                "strength": strength_label(str(e.get("evidence_strength") or "none"), lang),
                "explanation": expl,
                "rule_id": rule_id,
                "feature_id": feature_id,
                "comparison_result": cmp_res,
            }
        )
    return rows


def ledger_headers(lang: str) -> list[str]:
    if lang == "ru":
        return [
            "Правило",
            "Признак",
            "Измеренное значение",
            "Единица",
            "Условие",
            "Данные",
            "Результат условия",
            "Влияние",
            "Сила",
            "Объяснение",
        ]
    return [
        "Rule",
        "Feature",
        "Measured value",
        "Unit",
        "Condition",
        "Data",
        "Condition result",
        "Effect",
        "Strength",
        "Explanation",
    ]


def evidence_identity_header(result: Mapping[str, Any], lang: str) -> str:
    sha = str(result.get("source_sha256") or "")[:12]
    frame = int(result.get("frame_index") or 0)
    time_s = str(result.get("interpreted_time") or "—")
    # Prefer HH:MM if ISO-like
    if "T" in time_s:
        try:
            time_s = time_s.split("T", 1)[1][:5]
        except Exception:
            pass
    if lang == "ru":
        return f"Источник: {sha or '—'} · Кадр: {frame} · Время: {time_s or '—'}"
    return f"Source: {sha or '—'} · Frame: {frame} · Time: {time_s or '—'}"


def evidence_stale_banner(frame_index: int, lang: str) -> str:
    if lang == "ru":
        return (
            f"Это окно относится к кадру {frame_index} и не следует за текущим кадром."
        )
    return f"This window belongs to frame {frame_index} and does not follow the current frame."


def fragmentation_gate_rows(ledger: list[Mapping[str, Any]] | tuple) -> list[dict[str, Any]]:
    """Extract the two fragmentation/oversegmentation gate rows for QA export."""
    wanted = {"gate_oversegmentation_flag", "gate_fragmentation_score"}
    return [dict(e) for e in ledger if isinstance(e, Mapping) and e.get("rule_id") in wanted]


def contains_raw_python_dump(text: str) -> bool:
    if "{'" in text or '{"' in text:
        return True
    if text.strip() in {"()", "None", "[]"}:
        return True
    if "'supported':" in text or '"supported":' in text:
        return True
    return False


def contains_canonical_abstention_enum(text: str) -> bool:
    """True if any canonical abstention token appears as a whole token in text."""
    for tok in CANONICAL_ABSTENTION_TOKENS:
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(tok)}(?![A-Za-z0-9_])", text):
            return True
    return False
