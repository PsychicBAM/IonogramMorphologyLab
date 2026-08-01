"""Uncertainty display helpers (uncalibrated in IML-1)."""

from __future__ import annotations


def confidence_label(status: str, language: str = "en") -> str:
    mapping_en = {
        "proposed": "Proposed (uncalibrated)",
        "uncertain": "Uncertain — expert review recommended",
        "abstain": "Algorithm abstained",
        "not_assessable": "Not assessable",
        "out_of_domain": "Outside verified reference domain",
    }
    mapping_ru = {
        "proposed": "Предложено (без калибровки уверенности)",
        "uncertain": "Неопределённо — рекомендована экспертная проверка",
        "abstain": "Алгоритм воздержался от решения",
        "not_assessable": "Невозможно оценить",
        "out_of_domain": "Вне верифицированной области эталонов",
    }
    m = mapping_ru if language == "ru" else mapping_en
    return m.get(status, status)
