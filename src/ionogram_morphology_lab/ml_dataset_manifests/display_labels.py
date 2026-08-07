"""Localized display labels for ML-B.1 UI (canonical codes stay in exports/Technical Details)."""

from __future__ import annotations

import re

from ionogram_morphology_lab.ml_dataset_readiness.contracts import CONTRACT_LABELS
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import GATE_LABELS

ROLE_LABELS = {
    "train": {"en": "Train", "ru": "Обучение"},
    "development": {"en": "Development", "ru": "Разработка"},
    "untouched_holdout": {"en": "Untouched holdout", "ru": "Незатронутый holdout"},
    "excluded": {"en": "Excluded", "ru": "Исключено"},
}

LIFECYCLE_LABELS = {
    "draft": {"en": "Draft", "ru": "Черновик"},
    "validated": {"en": "Validated", "ru": "Проверено"},
    "frozen": {"en": "Frozen", "ru": "Заморожен"},
    "archived": {"en": "Archived", "ru": "В архиве"},
}

POLICY_LABELS = {
    "sequence_blocked": {"en": "Sequence-blocked", "ru": "Блокировка по последовательности"},
    "related_frame_group_blocked": {
        "en": "Related-frame-group blocked",
        "ru": "Блокировка по группе связанных кадров",
    },
    "source_date_blocked": {"en": "Source-date blocked", "ru": "Блокировка по дате источника"},
    "acquisition_period_blocked": {
        "en": "Acquisition-period blocked",
        "ru": "Блокировка по периоду сбора",
    },
    "campaign_blocked": {"en": "Campaign blocked", "ru": "Блокировка по кампании"},
    "conservative_combined_leakage_graph": {
        "en": "Conservative combined leakage graph (default)",
        "ru": "Консервативный объединённый граф утечек (по умолчанию)",
    },
    "manual_atomic_group_assignment": {
        "en": "Manual atomic-group assignment",
        "ru": "Ручное назначение атомарных групп",
    },
}

BOOLEAN_FLAGS = {
    "authorizes_mlb_planning": {
        "en": "Authorizes ML-B planning only",
        "ru": "Разрешено только планирование ML-B",
    },
    "authorizes_training": {
        "en": "Authorizes training",
        "ru": "Разрешено обучение",
    },
    "authorizes_mlc": {
        "en": "Authorizes ML-C",
        "ru": "Разрешён ML-C",
    },
}

# Coverage / inventory field labels for normal UI (canonical keys stay in Technical Details).
COVERAGE_FIELD_LABELS = {
    "unique_items": {"en": "Items", "ru": "Элементов"},
    "atomic_groups": {"en": "Atomic groups", "ru": "Атомарных групп"},
    "sequences": {"en": "Sequences", "ru": "Последовательностей"},
    "acquisition_dates": {"en": "Acquisition dates", "ru": "Дат съёмки"},
    "sources": {"en": "Sources", "ru": "Источников"},
    "target_distribution": {"en": "Target class distribution", "ru": "Распределение целевых классов"},
    "target_classes": {"en": "Target classes", "ru": "Целевые классы"},
    "sequence": {"en": "Sequence", "ru": "Последовательность"},
    "acquisition_date": {"en": "Acquisition date", "ru": "Дата съёмки"},
    "source": {"en": "Source", "ru": "Источник"},
    "target_class": {"en": "Target class", "ru": "Целевой класс"},
}

CONTAMINATION_LABELS = {
    "development_exposed": {
        "en": "Development-exposed",
        "ru": "Использовано в разработке",
    },
    "untouched_candidate": {
        "en": "Untouched-holdout candidate",
        "ru": "Кандидат для нетронутого набора",
    },
}

# Raw keys that must not appear as labels in the normal Coverage tab.
COVERAGE_RAW_KEYS_FORBIDDEN_IN_UI = (
    "unique_items",
    "atomic_groups",
    "acquisition_dates",
    "target_distribution",
    "related_frame_groups",
    "untouched_candidate",
    "development_exposed",
)

# Stable blocker code → localized sentence. Persisted JSON keeps the raw code prefix.
BLOCKER_TEMPLATES = {
    "readiness_gate_not_F": {
        "en": (
            "Readiness Gate outcome is {outcome_label}. Draft split simulation is allowed; "
            "final manifest freeze is unavailable."
        ),
        "ru": (
            "Исход шлюза готовности — {outcome_label}. Разрешено только черновое моделирование "
            "разделения; финальная заморозка манифеста недоступна."
        ),
    },
    "no_untouched_eligible_groups": {
        "en": (
            "No independent untouched groups eligible for holdout. All available groups are "
            "development-exposed or otherwise ineligible. Randomly splitting adjacent frames "
            "is forbidden."
        ),
        "ru": (
            "Нет независимых нетронутых групп, пригодных для holdout. Все доступные группы уже "
            "использовались в разработке или иначе недопустимы. Случайное разделение соседних "
            "кадров запрещено."
        ),
    },
    "holdout_not_reserved": {
        "en": "Holdout is not reserved: assign at least one untouched_holdout group before freeze.",
        "ru": "Holdout не зарезервирован: перед заморозкой назначьте хотя бы одну группу untouched_holdout.",
    },
    "required_class_absent": {
        "en": "Required class absent from role {role}: {classes}.",
        "ru": "Обязательный класс отсутствует в роли {role}: {classes}.",
    },
    "prohibited_metric_payload": {
        "en": "Forbidden scientific performance metric or claim detected: {detail}.",
        "ru": "Обнаружена запрещённая научная метрика или заявление о качестве: {detail}.",
    },
    "validation_stale": {
        "en": "Manifest changed after the last validation. Run Validate again.",
        "ru": "Манифест изменён после последней проверки. Выполните проверку снова.",
    },
}


def role_label(role: str, lang: str = "en") -> str:
    return ROLE_LABELS.get(role, {}).get(lang, role)


def lifecycle_label(state: str, lang: str = "en") -> str:
    return LIFECYCLE_LABELS.get(state, {}).get(lang, state)


def policy_label(policy_id: str, lang: str = "en") -> str:
    return POLICY_LABELS.get(policy_id, {}).get(lang, policy_id)


def gate_outcome_label(outcome: str, lang: str = "en") -> str:
    if not outcome:
        return "—" if lang != "ru" else "—"
    entry = GATE_LABELS.get(outcome) or {}
    return entry.get(lang) or entry.get("en") or outcome


def gate_compact_label(outcome: str, lang: str = "en") -> str:
    """Short Gate letter for always-visible compact status (full text stays in context)."""
    if not outcome:
        return "—"
    letter = str(outcome).split("_", 1)[0].strip().upper()
    if len(letter) == 1 and letter.isalpha():
        # Owner compact line uses Latin "Gate F" in both languages.
        return f"Gate {letter}"
    return gate_outcome_label(outcome, lang)


def contract_label(contract_id: str, lang: str = "en") -> str:
    entry = CONTRACT_LABELS.get(contract_id) or {}
    return entry.get(lang) or entry.get("en") or contract_id


def contract_compact_label(contract_id: str, lang: str = "en") -> str:
    """Short task-contract phrase for compact status line."""
    if contract_id == "spread_f_morphology_classification":
        return "Spread-F morphology" if lang != "ru" else "Морфология Spread-F"
    return contract_label(contract_id, lang)


def flag_label(flag_key: str, lang: str = "en") -> str:
    entry = BOOLEAN_FLAGS.get(flag_key) or {}
    return entry.get(lang) or entry.get("en") or flag_key


def coverage_field_label(field_key: str, lang: str = "en") -> str:
    entry = COVERAGE_FIELD_LABELS.get(field_key) or {}
    return entry.get(lang) or entry.get("en") or field_key


def contamination_label(state: str, lang: str = "en") -> str:
    entry = CONTAMINATION_LABELS.get(state) or {}
    return entry.get(lang) or entry.get("en") or state


def short_source_id(value: str, *, head: int = 4, tail: int = 4) -> str:
    """Compact opaque identity for normal UI; full value stays in tooltip/Technical Details."""
    text = str(value or "").strip()
    if not text:
        return "—"
    if len(text) <= head + tail + 1:
        return text
    # Prefer the distinctive suffix of zero-padded SHA-256 digests (e.g. c211…1111).
    stripped = text.lstrip("0") or text
    if len(stripped) >= head + tail:
        return f"{stripped[:head]}…{stripped[-tail:]}"
    return f"{text[:head]}…{text[-tail:]}"


def format_blocker(raw: str, lang: str = "en") -> str:
    """Translate a persisted blocker string for normal UI. Keep raw codes for Technical Details."""
    text = str(raw or "").strip()
    if not text:
        return ""
    code = text.split(":", 1)[0].strip()
    # integrity: prefixed errors
    if code == "integrity":
        rest = text.split(":", 1)[1] if ":" in text else text
        prefix = "Integrity: " if lang != "ru" else "Целостность: "
        return prefix + format_blocker(rest, lang)

    if code == "readiness_gate_not_F":
        m = re.search(r"outcome=([^;\s]+)", text)
        outcome = m.group(1) if m else ""
        tmpl = BLOCKER_TEMPLATES["readiness_gate_not_F"][lang]
        return tmpl.format(outcome_label=gate_outcome_label(outcome, lang))

    if code == "no_untouched_eligible_groups":
        return BLOCKER_TEMPLATES["no_untouched_eligible_groups"][lang]

    if code == "holdout_not_reserved":
        return BLOCKER_TEMPLATES["holdout_not_reserved"][lang]

    if code == "required_class_absent":
        parts = text.split(":")
        role = parts[1] if len(parts) > 1 else ""
        classes = parts[2] if len(parts) > 2 else ""
        return BLOCKER_TEMPLATES["required_class_absent"][lang].format(
            role=role_label(role, lang) if role in ROLE_LABELS else role,
            classes=classes,
        )

    if code == "prohibited_metric_payload":
        detail = text.split(":", 1)[1] if ":" in text else text
        return BLOCKER_TEMPLATES["prohibited_metric_payload"][lang].format(detail=detail)

    if code == "validation_stale":
        return BLOCKER_TEMPLATES["validation_stale"][lang]

    # Fallback: replace known embedded codes with labels
    out = text
    for oid, labels in GATE_LABELS.items():
        if oid in out:
            out = out.replace(oid, labels.get(lang) or labels["en"])
    for cid, labels in CONTRACT_LABELS.items():
        if cid in out:
            out = out.replace(cid, labels.get(lang) or labels["en"])
    return out


def format_blockers(raw_list: list[str] | None, lang: str = "en") -> list[str]:
    return [format_blocker(b, lang) for b in (raw_list or [])]


# Known raw codes that must not appear in normal (non-technical) RU UI text.
RAW_UI_FORBIDDEN_FRAGMENTS = (
    "A_collect_more_expert_labels",
    "B_repair_label_contract_or_missing_data",
    "C_expand_class_source_date_sequence_coverage",
    "D_obtain_independent_expert_review",
    "E_untouched_holdout_not_currently_feasible",
    "F_ready_for_mlb_manifest_planning_only",
    "spread_f_morphology_classification",
    "assessability_quality_classification",
    "interference_classification",
    "ionogram_parameter_scaling",
    "readiness_gate_not_F",
    "no_untouched_eligible_groups",
    "Authorizes ML-B planning only",
    "Authorizes training",
)
