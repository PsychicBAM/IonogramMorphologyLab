"""Human-readable presenters — keep technical JSON out of default views."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.ui.display_values import display_status


MORPHOLOGY_LABEL = {
    "en": {
        "frequency": "Possible frequency F-spread",
        "frequency_spread": "Possible frequency F-spread",
        "range": "Possible range F-spread",
        "range_spread": "Possible range F-spread",
        "mixed": "Possible mixed F-spread",
        "mixed_spread": "Possible mixed F-spread",
        "spread_unspecified": "Diffuse structure visible; spread type undetermined",
        "clean": "No visible spread",
        "diffuse": "Diffuse structure visible; spread type undetermined",
        "diffuse_unspecified": "Diffuse structure visible; spread type undetermined",
        "none": "No visible spread",
        "no_visible_spread": "No visible spread",
        "clean_trace": "No visible spread",
        "morphology_none": "No visible spread",
        "indeterminate": "Insufficient data to determine morphology",
        "artifact": "Assessment limited by interference",
        "interference_dominated": "Assessment limited by interference",
        "low_signal": "Low signal",
        "multiple_branch": "Multiple branch",
        "possible_multiple_reflection": "Possible multiple reflection",
        "not_assessable": "Not assessable",
        "other": "Other morphology",
        "other_morphology": "Other morphology",
        "abstain": "Algorithm abstained",
    },
    "ru": {
        "frequency": "Возможно частотное F-рассеяние",
        "frequency_spread": "Возможно частотное F-рассеяние",
        "range": "Возможно высотное F-рассеяние",
        "range_spread": "Возможно высотное F-рассеяние",
        "mixed": "Возможно смешанное F-рассеяние",
        "mixed_spread": "Возможно смешанное F-рассеяние",
        "spread_unspecified": "Наблюдается диффузная структура, тип не определён",
        "clean": "Явное рассеяние не обнаружено",
        "diffuse": "Наблюдается диффузная структура, тип не определён",
        "diffuse_unspecified": "Наблюдается диффузная структура, тип не определён",
        "none": "Явное рассеяние не обнаружено",
        "no_visible_spread": "Явное рассеяние не обнаружено",
        "clean_trace": "Явное рассеяние не обнаружено",
        "morphology_none": "Явное рассеяние не обнаружено",
        "indeterminate": "Недостаточно данных для определения морфологии",
        "artifact": "Оценка ограничена помехами",
        "interference_dominated": "Оценка ограничена помехами",
        "low_signal": "Слабый сигнал",
        "multiple_branch": "Множественные ветви",
        "possible_multiple_reflection": "Возможное многократное отражение",
        "not_assessable": "Кадр невозможно надёжно оценить",
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
    if float(feats.get("frequency_evidence_passed", 0) or 0) >= 1.0:
        reasons.append(
            "независимое частотное уширение (локальная толщина)"
            if lang == "ru"
            else "independent frequency broadening (local thickness)"
        )
    if float(feats.get("range_evidence_passed", 0) or 0) >= 1.0:
        reasons.append(
            "независимое высотное уширение (локальная толщина)"
            if lang == "ru"
            else "independent range broadening (local thickness)"
        )
    if float(feats.get("colocated_spread_fraction", 0) or 0) >= 0.20:
        reasons.append(
            "со-локализация частотного и высотного уширения"
            if lang == "ru"
            else "co-located frequency and range broadening"
        )
    if feats.get("interference_dominance", 0) >= 0.55:
        reasons.append("доминирование помех" if lang == "ru" else "interference dominance")
    if record.get("possible_ox_confusion"):
        reasons.append("возможная O/X-неоднозначность" if lang == "ru" else "possible O/X ambiguity")

    auto = record.get("final_auto_status", "")
    if lang == "ru":
        if auto in ("abstain", "not_assessable", "uncertain"):
            status_txt = f"Статус автоматического решения: {auto}"
        elif record.get("confidence_score") is None:
            status_txt = f"Статус: {auto or 'proposed'} (численная уверенность не откалибрована)"
        else:
            status_txt = status_line(record, lang)
        lines = [
            f"Кандидатная морфология:\n{morph}",
            f"\nСтатус:\n{status_txt}",
            "\nОсновные основания:",
        ]
        lines += [f"- {r}" for r in (reasons or ["явное рассеяние не подтверждено признаками"])]
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

    if auto in ("abstain", "not_assessable", "uncertain"):
        status_txt = f"Automatic decision status: {auto}"
    elif record.get("confidence_score") is None:
        status_txt = f"Status: {auto or 'proposed'} (numerical confidence uncalibrated)"
    else:
        status_txt = status_line(record, lang)
    lines = [
        f"Candidate morphology:\n{morph}",
        f"\nStatus:\n{status_txt}",
        "\nMain evidence:",
    ]
    lines += [f"- {r}" for r in (reasons or ["no positive spread evidence gates passed"])]
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
    status = display_status(audit.get("status"), lang)
    warnings = ", ".join(audit.get("warnings") or []) or display_status("no" if lang == "ru" else "none", lang)
    if lang == "ru":
        return (
            f"Файл:\n{name}\n\n"
            f"Статус:\n{status}\n\n"
            f"Формат / адаптер:\n{audit.get('adapter')}\n\n"
            f"SHA-256:\n{(audit.get('sha256') or '')[:16]}…\n\n"
            f"Форма:\n{audit.get('shape')}\n\n"
            f"Доля конечных значений:\n{audit.get('finite_fraction')}\n\n"
            f"Предупреждения:\n{warnings}"
        )
    return (
        f"File:\n{name}\n\n"
        f"Status:\n{status}\n\n"
        f"Format / adapter:\n{audit.get('adapter')}\n\n"
        f"SHA-256:\n{(audit.get('sha256') or '')[:16]}…\n\n"
        f"Shape:\n{audit.get('shape')}\n\n"
        f"Finite fraction:\n{audit.get('finite_fraction')}\n\n"
        f"Warnings:\n{warnings}"
    )


def profile_card(profile: dict[str, Any], lang: str) -> str:
    verification_status = display_status(profile.get("profile_verification_status"), lang)
    if lang == "ru":
        return (
            f"Профиль:\n{profile.get('profile_name')}\n\n"
            f"Статус проверки:\n{verification_status}\n\n"
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
        f"Verification status:\n{verification_status}\n\n"
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
