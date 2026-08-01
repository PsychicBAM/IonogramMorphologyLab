"""Human-readable presenters — keep technical JSON out of default views."""

from __future__ import annotations

from typing import Any


MORPHOLOGY_LABEL = {
    "en": {
        "frequency": "Frequency spread",
        "frequency_spread": "Frequency spread",
        "range": "Range spread / virtual-height spread",
        "range_spread": "Range spread / virtual-height spread",
        "mixed": "Mixed spread",
        "mixed_spread": "Mixed spread",
        "spread_unspecified": "Unspecified spread / diffuse",
        "clean": "Clean / no confirmed spread feature",
        "diffuse": "Diffuse (unspecified)",
        "none": "No confirmed compatible feature",
        "indeterminate": "Indeterminate",
        "artifact": "Artifact / interference-dominated",
        "interference_dominated": "Interference-dominated",
        "low_signal": "Low signal",
        "multiple_branch": "Multiple branch",
        "possible_multiple_reflection": "Possible multiple reflection",
        "not_assessable": "Not assessable",
        "other": "Other morphology",
        "other_morphology": "Other morphology",
        "abstain": "Algorithm abstained",
    },
    "ru": {
        "frequency": "Частотное рассеяние",
        "frequency_spread": "Частотное рассеяние",
        "range": "Высотное рассеяние / рассеяние по виртуальной высоте",
        "range_spread": "Высотное рассеяние / рассеяние по виртуальной высоте",
        "mixed": "Смешанное рассеяние",
        "mixed_spread": "Смешанное рассеяние",
        "spread_unspecified": "Неуточнённое рассеяние / диффузность",
        "clean": "Чистая трасса / без подтверждённого рассеяния",
        "diffuse": "Диффузная (неуточнённая)",
        "none": "Убедительных признаков нет",
        "indeterminate": "Неопределённо",
        "artifact": "Артефакт / доминирующая помеха",
        "interference_dominated": "Доминирующая помеха",
        "low_signal": "Слабый сигнал",
        "multiple_branch": "Множественные ветви",
        "possible_multiple_reflection": "Возможное многократное отражение",
        "not_assessable": "Невозможно оценить",
        "other": "Другая морфология",
        "other_morphology": "Другая морфология",
        "abstain": "Алгоритм воздержался от решения",
    },
}


def morphology_label(token: str, lang: str) -> str:
    return MORPHOLOGY_LABEL.get(lang, MORPHOLOGY_LABEL["en"]).get(token, token)


def confidence_explanation(record: dict[str, Any], lang: str) -> str:
    score = record.get("confidence_score")
    status = record.get("final_auto_status") or record.get("confidence_calibration_status")
    if score is None:
        if lang == "ru":
            return (
                "Численная уверенность отсутствует: калибровка модели ещё не выполнена.\n"
                f"Статус автоматического решения: {status}."
            )
        return (
            "No numerical confidence is available because model calibration has "
            "not yet been performed.\n"
            f"Automatic decision status: {status}."
        )
    return f"{score} ({status})"


def explain_result(record: dict[str, Any], lang: str) -> str:
    morph = morphology_label(record.get("candidate_morphology", "abstain"), lang)
    conf = confidence_explanation(record, lang)
    alts = [record.get("top_alternative_1"), record.get("top_alternative_2")]
    alts = [morphology_label(a, lang) for a in alts if a]
    feats = record.get("measured_features") or {}
    reasons = []
    if feats.get("median_horizontal_width", 0) >= 5:
        reasons.append("горизонтальное уширение" if lang == "ru" else "horizontal broadening")
    if feats.get("median_vertical_width", 0) >= 8:
        reasons.append("вертикальное уширение" if lang == "ru" else "vertical broadening")
    if feats.get("interference_dominance", 0) >= 0.55:
        reasons.append("доминирование помех" if lang == "ru" else "interference dominance")
    if record.get("possible_ox_confusion"):
        reasons.append("возможная O/X-неоднозначность" if lang == "ru" else "possible O/X ambiguity")

    if lang == "ru":
        lines = [
            f"Кандидатная морфология:\n{morph}",
            f"\nСтатус:\nПредложено, но уверенность не откалибрована"
            if record.get("confidence_score") is None
            else f"\nСтатус:\n{status_line(record, lang)}",
            "\nОсновные основания:",
        ]
        lines += [f"- {r}" for r in (reasons or ["см. измеренные признаки"])]
        if alts:
            lines.append("\nАльтернативы:")
            for i, a in enumerate(alts, 1):
                lines.append(f"{i}. {a}")
        lines += [
            "\nОграничения:",
            "- пороги являются development-calibration;",
            "- O/X-компоненты не разделены;",
            "- абсолютная амплитудная калибровка отсутствует;",
            "- это не подтверждение физического механизма.",
            f"\n{conf}",
        ]
        return "\n".join(lines)

    lines = [
        f"Candidate morphology:\n{morph}",
        "\nStatus:\nProposed, but confidence is not calibrated"
        if record.get("confidence_score") is None
        else f"\nStatus:\n{status_line(record, lang)}",
        "\nMain evidence:",
    ]
    lines += [f"- {r}" for r in (reasons or ["see measured features"])]
    if alts:
        lines.append("\nAlternatives:")
        for i, a in enumerate(alts, 1):
            lines.append(f"{i}. {a}")
    lines += [
        "\nLimitations:",
        "- thresholds are development-calibration;",
        "- O/X components are not separated;",
        "- absolute amplitude calibration is absent;",
        "- this is not physical-mechanism confirmation.",
        f"\n{conf}",
    ]
    return "\n".join(lines)


def status_line(record: dict[str, Any], lang: str) -> str:
    s = record.get("final_auto_status", "")
    mapping = {
        "proposed": ("Предложено", "Proposed"),
        "uncertain": ("Неопределённо — нужна экспертная проверка", "Uncertain — expert review recommended"),
        "abstain": ("Алгоритм воздержался", "Algorithm abstained"),
        "not_assessable": ("Невозможно оценить", "Not assessable"),
        "out_of_domain": ("Вне верифицированной области", "Outside verified domain"),
    }
    ru, en = mapping.get(s, (s, s))
    return ru if lang == "ru" else en


def audit_card(audit: dict[str, Any], lang: str) -> str:
    path = audit.get("path", "")
    name = path.replace("\\", "/").split("/")[-1]
    if lang == "ru":
        return (
            f"Файл:\n{name}\n\n"
            f"Статус:\n{audit.get('status')}\n\n"
            f"Формат / адаптер:\n{audit.get('adapter')}\n\n"
            f"SHA-256:\n{(audit.get('sha256') or '')[:16]}…\n\n"
            f"Форма:\n{audit.get('shape')}\n\n"
            f"Доля конечных значений:\n{audit.get('finite_fraction')}\n\n"
            f"Предупреждения:\n{', '.join(audit.get('warnings') or []) or 'нет'}"
        )
    return (
        f"File:\n{name}\n\n"
        f"Status:\n{audit.get('status')}\n\n"
        f"Format / adapter:\n{audit.get('adapter')}\n\n"
        f"SHA-256:\n{(audit.get('sha256') or '')[:16]}…\n\n"
        f"Shape:\n{audit.get('shape')}\n\n"
        f"Finite fraction:\n{audit.get('finite_fraction')}\n\n"
        f"Warnings:\n{', '.join(audit.get('warnings') or []) or 'none'}"
    )


def profile_card(profile: dict[str, Any], lang: str) -> str:
    if lang == "ru":
        return (
            f"Профиль:\n{profile.get('profile_name')}\n\n"
            f"Статус проверки:\n{profile.get('profile_verification_status')}\n\n"
            f"Учреждение / прибор:\n{profile.get('institution')} / {profile.get('instrument')}\n\n"
            f"Станция:\n{profile.get('station_name')}\n\n"
            f"Координаты:\n{profile.get('latitude')}, {profile.get('longitude')}\n\n"
            f"Переменная:\n{profile.get('amplitude_variable_name')}\n\n"
            f"Ожидаемая форма:\n{profile.get('expected_amplitude_shape')}\n\n"
            f"Кадров / высоты / частоты:\n"
            f"{profile.get('frames_per_file')} / {profile.get('height_bins')} / {profile.get('frequency_bins')}\n\n"
            f"Частоты:\n{profile.get('frequency_start_mhz')}–{profile.get('frequency_end_mhz')} МГц\n\n"
            f"Ось высоты:\n{profile.get('range_axis_label_ru')}\n\n"
            f"Предупреждения:\n- " + "\n- ".join(profile.get("warnings") or [])
        )
    return (
        f"Profile:\n{profile.get('profile_name')}\n\n"
        f"Verification status:\n{profile.get('profile_verification_status')}\n\n"
        f"Institution / instrument:\n{profile.get('institution')} / {profile.get('instrument')}\n\n"
        f"Station:\n{profile.get('station_name')}\n\n"
        f"Coordinates:\n{profile.get('latitude')}, {profile.get('longitude')}\n\n"
        f"Variable:\n{profile.get('amplitude_variable_name')}\n\n"
        f"Expected shape:\n{profile.get('expected_amplitude_shape')}\n\n"
        f"Frames / height / frequency bins:\n"
        f"{profile.get('frames_per_file')} / {profile.get('height_bins')} / {profile.get('frequency_bins')}\n\n"
        f"Frequencies:\n{profile.get('frequency_start_mhz')}–{profile.get('frequency_end_mhz')} MHz\n\n"
        f"Height axis:\n{profile.get('range_axis_label_en')}\n\n"
        f"Warnings:\n- " + "\n- ".join(profile.get("warnings") or [])
    )
