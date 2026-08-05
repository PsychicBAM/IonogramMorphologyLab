"""Controlled vocabulary for human morphology review (no candidate suffixes)."""

from __future__ import annotations

from typing import Any

HUMAN_MORPHOLOGY_CODES = frozenset(
    {
        "frequency_spread",
        "range_spread",
        "mixed_spread",
        "no_supported_visible_spread",
        "indeterminate",
        "not_assessable",
    }
)

ASSESSABILITY_CODES = frozenset(
    {
        "assessable",
        "partially_assessable",
        "not_assessable",
    }
)

INTERFERENCE_CODES = frozenset(
    {
        "none_supported",
        "vertical_interference",
        "interference_or_artifact",
        "possible_corruption",
        "other",
        "uncertain",
    }
)

AMBIGUITY_CODES = frozenset({"low", "moderate", "high", "not_applicable"})
CONFIDENCE_CODES = frozenset({"low", "moderate", "high"})

COMPARISON_STATUSES = frozenset(
    {
        "exact_agreement",
        "morphology_disagreement",
        "assessability_disagreement",
        "candidate_abstained",
        "human_abstained",
        "both_abstained",
        "not_comparable",
    }
)

PARTITION_CODES = frozenset({"pilot_review", "future_holdout", "excluded"})

_LABELS: dict[str, dict[str, str]] = {
    "frequency_spread": {"en": "Frequency spread", "ru": "Частотное расплывание"},
    "range_spread": {"en": "Range spread", "ru": "Высотное расплывание"},
    "mixed_spread": {"en": "Mixed spread", "ru": "Смешанное расплывание"},
    "no_supported_visible_spread": {
        "en": "No supported visible spread",
        "ru": "Нет подтверждённого видимого расплывания",
    },
    "indeterminate": {"en": "Indeterminate", "ru": "Неопределённо"},
    "not_assessable": {"en": "Not assessable", "ru": "Не поддаётся оценке"},
    "assessable": {"en": "Assessable", "ru": "Оценимо"},
    "partially_assessable": {"en": "Partially assessable", "ru": "Частично оценимо"},
    "none_supported": {"en": "None supported", "ru": "Помехи не подтверждены"},
    "vertical_interference": {"en": "Vertical interference", "ru": "Вертикальные помехи"},
    "interference_or_artifact": {
        "en": "Interference or artifact",
        "ru": "Помеха или артефакт",
    },
    "possible_corruption": {"en": "Possible corruption", "ru": "Возможное повреждение"},
    "other": {"en": "Other", "ru": "Другое"},
    "uncertain": {"en": "Uncertain", "ru": "Неясно"},
    "low": {"en": "Low", "ru": "Низкая"},
    "moderate": {"en": "Moderate", "ru": "Средняя"},
    "high": {"en": "High", "ru": "Высокая"},
    "not_applicable": {"en": "Not applicable", "ru": "Не применимо"},
    # Candidate states (display as candidate wording — not ground truth)
    "frequency_spread_candidate": {
        "en": "Frequency spread (candidate)",
        "ru": "Частотное расплывание (кандидат)",
    },
    "range_spread_candidate": {
        "en": "Range spread (candidate)",
        "ru": "Высотное расплывание (кандидат)",
    },
    "mixed_spread_candidate": {
        "en": "Mixed spread (candidate)",
        "ru": "Смешанное расплывание (кандидат)",
    },
    "no_supported_visible_spread_candidate": {
        "en": "No supported visible spread (candidate)",
        "ru": "Нет подтверждённого видимого расплывания (кандидат)",
    },
    "indeterminate_candidate": {
        "en": "Indeterminate (candidate)",
        "ru": "Неопределённо (кандидат)",
    },
    "not_assessable_candidate": {
        "en": "Not assessable (candidate)",
        "ru": "Не поддаётся оценке (кандидат)",
    },
    # Comparison / agreement statuses
    "exact_agreement": {"en": "Agreement", "ru": "Совпадение"},
    "morphology_disagreement": {
        "en": "Morphology disagreement",
        "ru": "Морфологическое расхождение",
    },
    "assessability_disagreement": {
        "en": "Assessability disagreement",
        "ru": "Расхождение по оцениваемости",
    },
    "candidate_abstained": {"en": "Candidate abstained", "ru": "Кандидат воздержался"},
    "human_abstained": {"en": "Expert abstained", "ru": "Эксперт воздержался"},
    "both_abstained": {"en": "Both abstained", "ru": "Оба воздержались"},
    "not_comparable": {"en": "Comparison not possible", "ru": "Сравнение невозможно"},
}


def display_label(code: str, lang: str = "en") -> str:
    """Localized label for morphology, candidate, strength, or comparison codes."""
    if not code:
        return "—"
    row = _LABELS.get(code)
    if row:
        return row["ru" if lang == "ru" else "en"]
    # Fallback: try morphology_label path for human codes only
    try:
        return morphology_label(code, lang)
    except ValueError:
        return code


def morphology_label(code: str, lang: str = "en") -> str:
    row = _LABELS.get(code)
    if not row:
        raise ValueError(f"Unknown morphology/axis code: {code!r}")
    return row.get(lang if lang in ("en", "ru") else "en", row["en"])


def validate_human_morphology(code: str) -> str:
    if code not in HUMAN_MORPHOLOGY_CODES:
        raise ValueError(f"Invalid human morphology code: {code!r}")
    return code


def rationale_required(
    *,
    morphology: str,
    interference_flags: list[str] | None = None,
    is_revision: bool = False,
    is_post_reveal_revision: bool = False,
    override_revealed_candidate: bool = False,
) -> bool:
    if morphology in ("indeterminate", "not_assessable"):
        return True
    if interference_flags and "other" in interference_flags:
        return True
    if is_revision or is_post_reveal_revision or override_revealed_candidate:
        return True
    return False


def map_candidate_state_to_human(candidate_state: str) -> str | None:
    """Map engine candidate codes to human morphology codes for comparison only."""
    if candidate_state in HUMAN_MORPHOLOGY_CODES:
        return candidate_state
    mapping = {
        "frequency_spread_candidate": "frequency_spread",
        "range_spread_candidate": "range_spread",
        "mixed_spread_candidate": "mixed_spread",
        "no_supported_visible_spread_candidate": "no_supported_visible_spread",
        "indeterminate_candidate": "indeterminate",
        "not_assessable_candidate": "not_assessable",
        # Engine also emits some abstention codes without _candidate suffix
        "no_supported_visible_spread": "no_supported_visible_spread",
        "indeterminate": "indeterminate",
        "not_assessable": "not_assessable",
    }
    return mapping.get(candidate_state)


def comparison_status(
    *,
    human_morphology: str,
    human_assessability: str,
    candidate_state: str | None,
    candidate_assessability: str | None = None,
    candidate_available: bool | None = None,
) -> str:
    """Agreement status after an explicit candidate reveal.

    Do not call this for pre-reveal UI — use ``comparison_pending_reveal``.
    """
    if candidate_available is False or (
        candidate_available is None and candidate_state is None
    ):
        if human_morphology == "not_assessable":
            return "not_comparable"
        if human_morphology == "indeterminate":
            return "human_abstained"
        return "candidate_unavailable"

    cand_human = map_candidate_state_to_human(candidate_state or "")
    human_indet = human_morphology == "indeterminate"
    human_na = human_morphology == "not_assessable"
    cand_indet = cand_human in ("indeterminate",) or candidate_state in (
        "indeterminate_candidate",
        "indeterminate",
    )
    cand_na = cand_human in ("not_assessable",) or candidate_state in (
        "not_assessable_candidate",
        "not_assessable",
    )

    if human_na:
        return "not_comparable"
    if human_indet and (cand_indet or cand_na or not cand_human):
        return "both_abstained" if (cand_indet or cand_na) else "human_abstained"
    if human_indet:
        return "human_abstained"
    if cand_indet or cand_na or not cand_human:
        return "candidate_abstained" if (cand_indet or cand_na) else "candidate_unavailable"
    if cand_human == human_morphology:
        if (
            candidate_assessability
            and human_assessability
            and candidate_assessability != human_assessability
        ):
            return "assessability_disagreement"
        return "exact_agreement"
    return "morphology_disagreement"


def comparison_status_display(status: str, lang: str = "en") -> str:
    """Localized explanation for a saved comparison agreement_status."""
    ru = lang == "ru"
    table = {
        "exact_agreement": (
            "Точное совпадение морфологии" if ru else "Exact morphology agreement"
        ),
        "morphology_disagreement": (
            "Морфологическое расхождение" if ru else "Morphology disagreement"
        ),
        "human_abstained": (
            "Эксперт воздержался от выбора определённого класса."
            if ru
            else "Expert abstained from selecting a definite class."
        ),
        "candidate_abstained": (
            "Кандидат воздержался / неопределён."
            if ru
            else "Candidate abstained / indeterminate."
        ),
        "both_abstained": (
            "И эксперт, и кандидат воздержались."
            if ru
            else "Both expert and candidate abstained."
        ),
        "not_comparable": (
            "Сравнение невозможно: кадр признан неоцениваемым экспертом."
            if ru
            else "Not comparable: frame marked not assessable by the expert."
        ),
        "candidate_unavailable": (
            "Снимок кандидата недоступен или несовместим."
            if ru
            else "Candidate snapshot unavailable or incompatible."
        ),
        "assessability_disagreement": (
            "Расхождение по оценимости" if ru else "Assessability disagreement"
        ),
        "comparison_pending_reveal": (
            "Кандидат ещё не показан. Сравнение не выполнено."
            if ru
            else "Candidate not yet revealed. Comparison not performed."
        ),
    }
    return table.get(status, status)


def label_explanations(lang: str = "en") -> dict[str, str]:
    if lang == "ru":
        return {
            "no_supported_visible_spread": (
                "Нет подтверждённого видимого расплывания на оцениваемом изображении; "
                "это не доказательство отсутствия физического явления."
            ),
            "indeterminate": "Рецензент не может надёжно выбрать класс.",
            "not_assessable": "Кадр нельзя адекватно оценить.",
            "confidence": "Уверенность рецензента — самоотчёт, не вероятность и не научная истина.",
            "blinding": (
                "Слепая оценка скрывает кандидата процедурно в UI; "
                "это не криптографическая защита."
            ),
        }
    return {
        "no_supported_visible_spread": (
            "No supported visible spread in the assessable image; "
            "not proof that the physical phenomenon was absent."
        ),
        "indeterminate": "The reviewer cannot choose reliably.",
        "not_assessable": "The frame cannot be evaluated adequately.",
        "confidence": "Reviewer confidence is a self-report, not a probability or scientific truth.",
        "blinding": (
            "Blind mode hides the candidate procedurally in the UI; "
            "this is not cryptographic protection."
        ),
    }


def assert_no_prohibited_metrics(payload: dict[str, Any]) -> None:
    from ionogram_morphology_lab.morphology_review_corpus.constants import PROHIBITED_METRICS

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = str(k).lower()
                if key in PROHIBITED_METRICS:
                    raise ValueError(f"Prohibited metric field at {path}.{k}")
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")

    _walk(payload)
