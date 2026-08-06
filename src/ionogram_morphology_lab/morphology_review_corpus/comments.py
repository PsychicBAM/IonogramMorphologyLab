"""Structured comment builder, generation, presets (Phase 4C.2b)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_review_corpus.constants import (
    COMMENT_RECORD_SCHEMA_VERSION,
    COMMENT_TEMPLATE_VERSION,
    CORPORA_DIRNAME,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

COMMENT_TYPES = frozenset(
    {
        "observation",
        "decision_rationale",
        "assessment_limitation",
        "uncertainty_note",
        "technical_display_note",
        "free_comment",
        "post_reveal_comparison_note",
        "adjudication_note",
    }
)

# A. Trace visibility
TRACE_CODES = (
    "primary_f_trace_clear",
    "primary_f_trace_partial",
    "trace_fragmented",
    "multiple_traces_visible",
    "secondary_trace_visible",
    "trace_poorly_visible",
    "no_visible_trace",
    "other_trace_observation",
)
# B. Morphological observations (aligned with existing human morphology where possible)
MORPH_OBS_CODES = (
    "frequency_broadening_visible",
    "range_broadening_visible",
    "mixed_characteristics_visible",
    "weak_spread_characteristics",
    "uncertain_spread_characteristics",
    "no_supported_visible_spread_characteristics",
    "other_morphology_observation",
)
# C. Interference / artifacts — reuse vertical_interference etc. where equivalent
INTERF_OBS_CODES = (
    "vertical_interference",
    "horizontal_banding",
    "localized_artifact",
    "low_signal_to_noise",
    "clipping_or_saturation",
    "missing_data",
    "possible_data_corruption",
    "interference_partly_obscures_trace",
    "interference_does_not_prevent_review",
    "other_interference",
)
# D. Assessment limitations — reuse assessability codes where equivalent
LIMIT_CODES = (
    "fully_assessable",
    "partially_assessable",
    "only_part_of_trace_assessable",
    "interference_limits_assessment",
    "display_limits_assessment",
    "not_reliably_assessable",
    "other_assessability_reason",
)

ALL_STRUCTURED_CODES = frozenset(
    TRACE_CODES + MORPH_OBS_CODES + INTERF_OBS_CODES + LIMIT_CODES
)

_PHRASES: dict[str, dict[str, str]] = {
    "primary_f_trace_clear": {
        "en": "The primary F-trace is clear.",
        "ru": "Основной F-след виден чётко.",
    },
    "primary_f_trace_partial": {
        "en": "The primary F-trace is only partially visible.",
        "ru": "Основной F-след виден частично.",
    },
    "trace_fragmented": {
        "en": "The trace appears fragmented.",
        "ru": "След выглядит фрагментированным.",
    },
    "multiple_traces_visible": {
        "en": "Multiple traces are visible.",
        "ru": "Видно несколько следов.",
    },
    "secondary_trace_visible": {
        "en": "A secondary trace is visible.",
        "ru": "Виден вторичный след.",
    },
    "trace_poorly_visible": {
        "en": "The trace is poorly visible.",
        "ru": "След плохо различим.",
    },
    "no_visible_trace": {
        "en": "No clear trace is visible.",
        "ru": "Чёткий след не виден.",
    },
    "other_trace_observation": {
        "en": "Additional trace observations apply.",
        "ru": "Есть дополнительные наблюдения по следу.",
    },
    "frequency_broadening_visible": {
        "en": "Frequency-broadening characteristics are visible.",
        "ru": "Наблюдаются признаки частотного расширения.",
    },
    "range_broadening_visible": {
        "en": "Range-broadening characteristics are visible.",
        "ru": "Наблюдаются признаки высотного расширения.",
    },
    "mixed_characteristics_visible": {
        "en": "Mixed spread characteristics are visible.",
        "ru": "Наблюдаются смешанные признаки расплывания.",
    },
    "weak_spread_characteristics": {
        "en": "Spread characteristics are weak.",
        "ru": "Признаки расплывания слабые.",
    },
    "uncertain_spread_characteristics": {
        "en": "Spread characteristics are uncertain.",
        "ru": "Признаки расплывания неопределённы.",
    },
    "no_supported_visible_spread_characteristics": {
        "en": "No supported visible spread characteristics are present.",
        "ru": "Подтверждённых видимых признаков расплывания нет.",
    },
    "other_morphology_observation": {
        "en": "Additional morphology observations apply.",
        "ru": "Есть дополнительные морфологические наблюдения.",
    },
    "vertical_interference": {
        "en": "Vertical interference is present.",
        "ru": "Присутствуют вертикальные помехи.",
    },
    "horizontal_banding": {
        "en": "Horizontal banding is present.",
        "ru": "Присутствует горизонтальная полосатость.",
    },
    "localized_artifact": {
        "en": "A localized artifact is present.",
        "ru": "Присутствует локальный артефакт.",
    },
    "low_signal_to_noise": {
        "en": "Signal-to-noise is low.",
        "ru": "Низкое отношение сигнал/шум.",
    },
    "clipping_or_saturation": {
        "en": "Clipping or saturation is present.",
        "ru": "Присутствует клиппинг или насыщение.",
    },
    "missing_data": {
        "en": "Data are missing in the frame.",
        "ru": "В кадре отсутствуют данные.",
    },
    "possible_data_corruption": {
        "en": "Possible data corruption is present.",
        "ru": "Возможно повреждение данных.",
    },
    "interference_partly_obscures_trace": {
        "en": "Interference partly obscures the trace.",
        "ru": "Помехи частично закрывают след.",
    },
    "interference_does_not_prevent_review": {
        "en": "Interference does not prevent review.",
        "ru": "Помехи не препятствуют оценке.",
    },
    "other_interference": {
        "en": "Additional interference notes apply.",
        "ru": "Есть дополнительные замечания по помехам.",
    },
    "fully_assessable": {
        "en": "The frame is fully assessable.",
        "ru": "Кадр полностью оцениваем.",
    },
    "partially_assessable": {
        "en": "The frame is assessable with limitations.",
        "ru": "Кадр оцениваем с ограничениями.",
    },
    "only_part_of_trace_assessable": {
        "en": "Only part of the trace is assessable.",
        "ru": "Оценивается только часть следа.",
    },
    "interference_limits_assessment": {
        "en": "Interference limits the assessment.",
        "ru": "Помехи ограничивают оценку.",
    },
    "display_limits_assessment": {
        "en": "Display limits the assessment.",
        "ru": "Отображение ограничивает оценку.",
    },
    "not_reliably_assessable": {
        "en": "The frame is not reliably assessable.",
        "ru": "Кадр нельзя надёжно оценить.",
    },
    "other_assessability_reason": {
        "en": "Additional assessability notes apply.",
        "ru": "Есть дополнительные замечания по оценимости.",
    },
}

PRESET_DEFS: dict[str, dict[str, Any]] = {
    "clear_assessable_trace": {
        "codes": ["primary_f_trace_clear", "fully_assessable"],
        "label_en": "Clear assessable trace",
        "label_ru": "Чёткий оцениваемый след",
    },
    "partial_trace_vertical_interference": {
        "codes": [
            "primary_f_trace_partial",
            "vertical_interference",
            "interference_partly_obscures_trace",
            "partially_assessable",
        ],
        "label_en": "Partial trace with vertical interference",
        "label_ru": "Частичный след с вертикальными помехами",
    },
    "weak_frequency_spread": {
        "codes": [
            "primary_f_trace_partial",
            "frequency_broadening_visible",
            "weak_spread_characteristics",
            "partially_assessable",
        ],
        "label_en": "Weak frequency-spread characteristics",
        "label_ru": "Слабые признаки частотного расплывания",
    },
    "weak_range_spread": {
        "codes": [
            "primary_f_trace_partial",
            "range_broadening_visible",
            "weak_spread_characteristics",
            "partially_assessable",
        ],
        "label_en": "Weak range-spread characteristics",
        "label_ru": "Слабые признаки высотного расплывания",
    },
    "mixed_uncertain": {
        "codes": [
            "mixed_characteristics_visible",
            "uncertain_spread_characteristics",
            "partially_assessable",
        ],
        "label_en": "Mixed but uncertain characteristics",
        "label_ru": "Смешанные, но неопределённые признаки",
    },
    "no_supported_visible_spread": {
        "codes": [
            "primary_f_trace_clear",
            "no_supported_visible_spread_characteristics",
            "fully_assessable",
        ],
        "label_en": "No supported visible spread",
        "label_ru": "Нет подтверждённого видимого расплывания",
    },
    "not_assessable_interference": {
        "codes": [
            "trace_poorly_visible",
            "vertical_interference",
            "interference_limits_assessment",
            "not_reliably_assessable",
        ],
        "label_en": "Not assessable because of interference",
        "label_ru": "Не оцениваем из‑за помех",
    },
    "not_assessable_missing_data": {
        "codes": ["no_visible_trace", "missing_data", "not_reliably_assessable"],
        "label_en": "Not assessable because of missing data",
        "label_ru": "Не оцениваем из‑за отсутствия данных",
    },
}


def structured_code_label(code: str, lang: str = "en") -> str:
    row = _PHRASES.get(code)
    if not row:
        return code
    return row["ru" if lang == "ru" else "en"]


def generate_comment_text(codes: list[str], lang: str = "en") -> str:
    """Deterministic localized prose from structured observation codes."""
    phrases = []
    for code in codes:
        if code not in ALL_STRUCTURED_CODES:
            continue
        phrases.append(structured_code_label(code, lang))
    return " ".join(phrases).strip()


@dataclass
class CommentRecord:
    comment_id: str
    comment_type: str
    cohort_id: str
    item_id: str
    reviewer_id: str
    structured_codes: list[str] = field(default_factory=list)
    generated_text: str = ""
    final_text: str = ""
    expert_own_description: str = ""
    review_id: str = ""
    template_version: str = COMMENT_TEMPLATE_VERSION
    ui_language: str = "en"
    schema_version: int = COMMENT_RECORD_SCHEMA_VERSION
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    record_hash: str = ""
    supersedes_comment_id: str = ""
    build_identity: str = "ML-A.1a.2"

    def __post_init__(self) -> None:
        if self.comment_type not in COMMENT_TYPES:
            raise ValueError(f"Invalid comment_type: {self.comment_type!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "CommentRecord":
        payload = self.to_dict()
        payload.pop("record_hash", None)
        return CommentRecord(**{**payload, "record_hash": deterministic_hash(payload)})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommentRecord":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def create(
        cls,
        *,
        comment_type: str,
        cohort_id: str,
        item_id: str,
        reviewer_id: str,
        structured_codes: list[str] | None = None,
        generated_text: str = "",
        final_text: str = "",
        expert_own_description: str = "",
        review_id: str = "",
        ui_language: str = "en",
        supersedes_comment_id: str = "",
    ) -> "CommentRecord":
        codes = list(structured_codes or [])
        gen = generated_text or generate_comment_text(codes, ui_language)
        final = final_text if final_text is not None and final_text != "" else gen
        return cls(
            comment_id=str(uuid4()),
            comment_type=comment_type,
            cohort_id=cohort_id,
            item_id=item_id,
            reviewer_id=reviewer_id,
            structured_codes=codes,
            generated_text=gen,
            final_text=final,
            expert_own_description=expert_own_description,
            review_id=review_id,
            ui_language=ui_language,
            supersedes_comment_id=supersedes_comment_id,
        ).with_hash()


def project_presets_path(project_root: Path | str) -> Path:
    return Path(project_root) / CORPORA_DIRNAME / "_comment_presets.json"


def load_project_presets(project_root: Path | str) -> dict[str, dict[str, Any]]:
    p = project_presets_path(project_root)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_project_preset(
    project_root: Path | str, preset_id: str, codes: list[str], label: str
) -> None:
    """Project-local custom presets — not stored in Git."""
    data = load_project_presets(project_root)
    data[preset_id] = {"codes": list(codes), "label": label}
    path = project_presets_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_preset(preset_id: str, lang: str = "en") -> dict[str, Any]:
    """Return structured codes + generated text. Never selects morphology."""
    row = PRESET_DEFS.get(preset_id)
    if not row:
        return {"codes": [], "generated_text": "", "morphology": None}
    codes = list(row["codes"])
    return {
        "codes": codes,
        "generated_text": generate_comment_text(codes, lang),
        "morphology": None,
        "label": row["label_ru" if lang == "ru" else "label_en"],
    }
