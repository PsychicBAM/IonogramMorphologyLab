"""Built-in guided Rule Builder examples (templates — copy to draft only)."""

from __future__ import annotations

from copy import deepcopy

from ionogram_morphology_lab.rule_builder.model import ScientificRule

_EXAMPLE_NOTE_EN = (
    "Template for teaching and development. Not a universally validated scientific rule. "
    "Copy into a user draft before editing."
)
_EXAMPLE_NOTE_RU = (
    "Шаблон для обучения и разработки. Не является универсально валидированным научным правилом. "
    "Скопируйте в пользовательский черновик перед редактированием."
)


def builtin_examples() -> list[ScientificRule]:
    """Return immutable-style example rules (callers must deepcopy before edit)."""
    specs = [
        dict(
            rule_id="EX_FREQ_SPREAD",
            name_en="Frequency-spread candidate",
            name_ru="Кандидат частотного спреда",
            category="morphology",
            proposed_result="frequency_spread",
            conditions=[
                {"feature": "median_horizontal_width", "operator": "gte", "value": 0.70},
                {"feature": "temporal_persistence", "operator": "gte", "value": 0.60},
            ],
            exclusions=["vertical_interference_dominance >= 0.40"],
            threshold_origin="development_calibration",
        ),
        dict(
            rule_id="EX_RANGE_SPREAD",
            name_en="Range-spread candidate",
            name_ru="Кандидат высотного спреда",
            category="morphology",
            proposed_result="range_spread",
            conditions=[
                {"feature": "median_vertical_width", "operator": "gte", "value": 0.70},
                {"feature": "temporal_persistence", "operator": "gte", "value": 0.50},
            ],
            threshold_origin="development_calibration",
        ),
        dict(
            rule_id="EX_MIXED_SPREAD",
            name_en="Mixed-spread candidate",
            name_ru="Кандидат смешанного спреда",
            category="morphology",
            proposed_result="mixed_spread",
            conditions=[
                {"feature": "median_horizontal_width", "operator": "gte", "value": 0.55},
                {"feature": "median_vertical_width", "operator": "gte", "value": 0.55},
            ],
            threshold_origin="development_calibration",
        ),
        dict(
            rule_id="EX_ES",
            name_en="Es candidate",
            name_ru="Кандидат Es",
            category="layer",
            proposed_result="Es",
            conditions=[
                {"feature": "trace_pixel_fraction", "operator": "gte", "value": 0.08},
                {"feature": "continuity_score", "operator": "gte", "value": 0.40},
            ],
            threshold_origin="engineering_default",
        ),
        dict(
            rule_id="EX_OX",
            name_en="Possible O/X ambiguity",
            name_ru="Возможная неоднозначность O/X",
            category="ambiguity",
            proposed_result="possible_O_X",
            conditions=[
                {"feature": "possible_ox_compatibility", "operator": "gte", "value": 0.45},
                {"feature": "component_count", "operator": "gte", "value": 2},
            ],
            alternatives=["possible_O_X"],
            threshold_origin="development_calibration",
        ),
        dict(
            rule_id="EX_VERT_INTERF",
            name_en="Vertical-interference warning",
            name_ru="Предупреждение о вертикальной помехе",
            category="interference",
            proposed_result="vertical_interference",
            conditions=[
                {"feature": "interference_dominance", "operator": "gte", "value": 0.55},
            ],
            threshold_origin="engineering_default",
        ),
        dict(
            rule_id="EX_LOW_QUALITY",
            name_en="Low-quality abstention",
            name_ru="Воздержание при низком качестве",
            category="quality",
            proposed_result="poor_quality",
            conditions=[
                {"feature": "trace_pixel_fraction", "operator": "lt", "value": 0.05},
            ],
            abstention_condition="trace quality poor",
            threshold_origin="engineering_default",
        ),
        dict(
            rule_id="EX_CUSTOM_PARAM",
            name_en="Custom candidate parameter",
            name_ru="Пользовательский кандидатный параметр",
            category="parameter",
            proposed_result="candidate_parameter",
            conditions=[
                {"feature": "trace_frequency_coverage", "operator": "between", "value": 0.2, "value2": 0.95},
            ],
            threshold_origin="user_defined_experimental",
        ),
    ]
    out: list[ScientificRule] = []
    for s in specs:
        rule = ScientificRule(
            rule_id=s["rule_id"],
            name_en=s["name_en"],
            name_ru=s["name_ru"],
            category=s["category"],
            proposed_result=s["proposed_result"],
            conditions=list(s["conditions"]),
            outputs={s["category"]: s["proposed_result"]},
            status="draft",
            enabled=False,
            exclusions=list(s.get("exclusions", [])),
            alternatives=list(s.get("alternatives", [])),
            abstention_condition=str(s.get("abstention_condition", "")),
            threshold_origin=s.get("threshold_origin", "development_calibration"),
            limitations=[_EXAMPLE_NOTE_EN, _EXAMPLE_NOTE_RU],
            verification_status="unverified",
            implementation_status="disabled",
            version="1.1.1",
            tags=["builtin_example", "template"],
            metadata={"builtin_example": True, "editable_original": False},
        )
        out.append(rule)
    return out


def copy_example_to_draft(example: ScientificRule, new_id: str | None = None) -> ScientificRule:
    """Return a user-editable draft copy of a built-in example."""
    draft = deepcopy(example)
    draft.rule_id = new_id or f"USER_{example.rule_id}"
    draft.status = "draft"
    draft.enabled = True
    draft.implementation_status = "disabled"
    draft.verification_status = "unverified"
    draft.metadata = dict(draft.metadata or {})
    draft.metadata["copied_from_example"] = example.rule_id
    draft.metadata["builtin_example"] = False
    draft.metadata["editable_original"] = True
    draft.version = "1.1.1"
    return draft


TARGET_HELP = {
    "layer": {
        "en": "Propose a layer label (e.g. E, Es, F1, F2). Example: Es candidate from low-height trace.",
        "ru": "Предложить метку слоя (E, Es, F1, F2). Пример: кандидат Es по низковысотному следу.",
    },
    "morphology": {
        "en": "Propose morphology compatible with the image (e.g. frequency_spread). Not a physical mechanism.",
        "ru": "Предложить морфологию, совместимую с изображением (например frequency_spread). Не физический механизм.",
    },
    "ambiguity": {
        "en": "Flag unresolved alternatives such as possible O/X branching.",
        "ru": "Отметить неразрешённые альтернативы, например возможное ветвление O/X.",
    },
    "parameter": {
        "en": "Propose a candidate numerical parameter with explicit limitations.",
        "ru": "Предложить кандидатный числовой параметр с явными ограничениями.",
    },
    "interference": {
        "en": "Warn about interference patterns that may invalidate other proposals.",
        "ru": "Предупредить о помехах, которые могут обесценить другие предложения.",
    },
    "quality": {
        "en": "Mark poor quality or force abstention when evidence is insufficient.",
        "ru": "Отметить низкое качество или принудить к воздержанию при недостатке данных.",
    },
}

THRESHOLD_ORIGIN_HELP = {
    "source_defined": {
        "en": "Threshold taken directly from a cited source wording.",
        "ru": "Порог взят напрямую из цитируемого источника.",
    },
    "derived_from_verified_definition": {
        "en": "Derived from a verified definition without inventing a new physical claim.",
        "ru": "Выведен из проверенного определения без нового физического утверждения.",
    },
    "development_calibration": {
        "en": "Tuned on development data; not externally validated.",
        "ru": "Настроен на данных разработки; внешне не валидирован.",
    },
    "engineering_default": {
        "en": "Safe engineering default for tooling; scientific use needs review.",
        "ru": "Инженерный безопасный по умолчанию; для науки нужна проверка.",
    },
    "user_defined_experimental": {
        "en": "User experiment; must remain draft/development until tested.",
        "ru": "Эксперимент пользователя; остаётся черновиком до тестирования.",
    },
}

PROPOSED_RESULTS = [
    "F2",
    "F1",
    "E",
    "Es",
    "frequency_spread",
    "range_spread",
    "mixed_spread",
    "possible_O_X",
    "vertical_interference",
    "poor_quality",
    "indeterminate",
    "candidate_parameter",
]
