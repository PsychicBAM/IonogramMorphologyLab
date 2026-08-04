"""Visible “What this analysis uses” panel — matches default v1.1.1 path."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

# Fixed factual statuses for the default automatic analysis path.
DEFAULT_PIPELINE_COMPONENTS = (
    ("data_audit", "Data audit", "Проверка данных", "Active", "Активно"),
    ("segmentation", "Trace / interference segmentation", "Сегментация трассы / помех", "Active", "Активно"),
    ("features", "Python feature extraction", "Извлечение признаков (Python)", "Active", "Активно"),
    ("rule_engine", "Python RuleEngine", "Правила (Python RuleEngine)", "Active", "Активно"),
    ("atlas_meta", "Reference metadata", "Метаданные эталонного атласа", "Active", "Активно"),
    ("atlas_images", "Reference atlas images", "Изображения эталонного атласа", "Unavailable", "Недоступно"),
    ("disagreement", "Disagreement flags", "Флаги разногласий", "Active", "Активно"),
    ("temporal", "Temporal context (multi-frame)", "Временной контекст (многокадровый)", "Optional", "Необязательно"),
    ("matlab", "MATLAB Studio methods", "Методы MATLAB Studio", "Disabled", "Отключено"),
    ("ml", "Development ML (Model Lab)", "Развивающие модели (Model Lab)", "Disabled", "Отключено"),
    ("ensemble", "Ensemble fusion", "Ансамблевое объединение", "Disabled", "Отключено"),
)


class AnalysisPipelinePanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("analysis_pipeline_panel")
        self._label = QLabel()
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.addWidget(self._label)

    def retranslate(self, lang: str = "en") -> None:
        ru = lang == "ru"
        self.setTitle("Что используется в этом анализе" if ru else "What this analysis uses")
        lines = []
        for _key, en, ru_name, en_st, ru_st in DEFAULT_PIPELINE_COMPONENTS:
            name = ru_name if ru else en
            status = ru_st if ru else en_st
            lines.append(f"• {name} — {status}")
        note = (
            "MATLAB, Model Lab и эталонные изображения не участвуют в результате, "
            "пока они не включены явно как этап конвейера."
            if ru
            else "MATLAB methods, Model Lab models, and atlas images do not participate "
            "in the result unless explicitly enabled as a pipeline stage."
        )
        self._label.setText("\n".join(lines) + "\n\n" + note)
