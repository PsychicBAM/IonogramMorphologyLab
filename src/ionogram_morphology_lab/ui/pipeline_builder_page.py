"""Pipeline Builder — stage cards; changes apply to future runs only."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


@dataclass
class StageSpec:
    key: str
    name_en: str
    name_ru: str
    purpose_en: str
    purpose_ru: str
    default: bool
    deps: list[str]
    status: str  # Active | Optional | Disabled | Unavailable | Misconfigured
    scientific_en: str
    scientific_ru: str
    effect_en: str
    effect_ru: str
    implementation: str = "built-in"
    available: bool = True


STAGES: list[StageSpec] = [
    StageSpec("import", "Import", "Импорт", "Register source MAT", "Регистрация исходного MAT", True, [], "Active",
              "No classification", "Без классификации", "Required for all analysis", "Нужен для любого анализа"),
    StageSpec("profile", "Profile", "Профиль", "Instrument axes and time mapping", "Оси прибора и время", True, ["import"], "Active",
              "Metadata", "Метаданные", "Shapes Viewer and features", "Определяет Просмотрщик и признаки"),
    StageSpec("cache", "Cache", "Кэш", "Derived frame cache", "Производный кэш кадров", True, ["profile"], "Active",
              "Engineering", "Инженерия", "Speeds Viewer/Batch", "Ускоряет Просмотрщик/Пакет"),
    StageSpec("trace", "Trace extraction", "Извлечение трассы", "Segment trace vs interference", "Сегментация трассы и помех", True, ["cache"], "Active",
              "Diagnostic", "Диагностика", "Feeds morphology rules", "Питает правила морфологии"),
    StageSpec("layer_e", "E-layer detector", "Детектор E", "E-region candidate", "Кандидат области E", True, ["trace"], "Optional",
              "Candidate", "Кандидат", "May propose E parameters", "Может предложить параметры E"),
    StageSpec("layer_es", "Es detector", "Детектор Es", "Es candidate", "Кандидат Es", True, ["trace"], "Optional",
              "Candidate", "Кандидат", "May propose Es parameters", "Может предложить параметры Es"),
    StageSpec("layer_f1", "F1 detector", "Детектор F1", "F1 candidate when separable", "Кандидат F1 при отделении", True, ["trace"], "Optional",
              "Candidate", "Кандидат", "Layer axis only", "Только ось слоя"),
    StageSpec("layer_f2", "F2 detector", "Детектор F2", "F2 candidate", "Кандидат F2", True, ["trace"], "Optional",
              "Candidate", "Кандидат", "Layer axis only", "Только ось слоя"),
    StageSpec("interference", "Interference detector", "Детектор помех", "Interference assessment", "Оценка помех", True, ["trace"], "Active",
              "Separate axis", "Отдельная ось", "Does not replace morphology", "Не заменяет морфологию"),
    StageSpec("spread_f", "Spread-F morphology", "Морфология Spread-F", "Python RuleEngine morphology", "Морфология Python RuleEngine", True, ["trace"], "Active",
              "Automatic candidate", "Автоматический кандидат", "Default analysis path", "Путь анализа по умолчанию"),
    StageSpec("ox_ambiguity", "O/X ambiguity detector", "Детектор неоднозначности O/X", "Flag possible O/X confusion", "Флаг возможной путаницы O/X", True, ["trace"], "Optional",
              "Ambiguity axis", "Ось неоднозначности", "Abstention support", "Поддержка воздержания"),
    StageSpec("parameters", "Parameter estimator", "Оценка параметров", "Image-estimated parameter candidates", "Кандидаты параметров по изображению", False, ["layer_e", "layer_es", "layer_f2"], "Optional",
              "Not confirmed scaling", "Не подтверждённый скейлинг", "Writes parameter candidates", "Пишет кандидатов параметров"),
    StageSpec("custom_rules", "User rule pack", "Пользовательский пакет правил", "Optional custom rules", "Опциональные правила", False, ["trace"], "Optional",
              "Needs validation", "Требует валидации", "Overrides only if saved pipeline selected", "Только если выбран сохранённый конвейер"),
    StageSpec("matlab", "MATLAB method", "Метод MATLAB", "Registered MATLAB plugin stage", "Этап зарегистрированного плагина MATLAB", False, ["cache"], "Disabled",
              "Not in default path", "Не в пути по умолчанию", "Future runs only when plugin enabled", "Только будущие запуски при включённом плагине",
              implementation="none", available=False),
    StageSpec("ml", "ML model", "ML-модель", "Development Model Lab model", "Модель Model Lab", False, ["trace"], "Disabled",
              "Not externally validated", "Не валидировано внешне", "Requires enabled trusted model", "Нужна включённая доверенная модель",
              implementation="none", available=False),
    StageSpec("temporal", "Temporal analyzer", "Временной анализатор", "Neighbor-frame context", "Контекст соседних кадров", False, ["cache"], "Optional",
              "Supplements single-frame", "Дополняет однокадровый вывод", "Requires ≥2 neighboring frames; does not replace single-frame morphology",
              "Нужно ≥2 соседних кадра; не заменяет однокадровую морфологию"),
    StageSpec("human_review", "Human review", "Человеческая проверка", "Owner/expert decisions", "Решения владельца/эксперта", True, [], "Active",
              "Separate from automatic", "Отдельно от автоматики", "Labels stay owner/expert", "Метки остаются owner/expert"),
    StageSpec("report", "Report", "Отчёт", "Export reproducible reports", "Экспорт воспроизводимых отчётов", True, ["human_review"], "Active",
              "Provenance export", "Экспорт происхождения", "Does not upgrade candidate status", "Не повышает статус кандидата"),
]


class PipelineBuilderPage(QWidget):
    def __init__(self, session, i18n, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.checks: dict[str, QCheckBox] = {}
        self.impl_boxes: dict[str, QComboBox] = {}
        self.cards: dict[str, QGroupBox] = {}
        self._saved: dict[str, bool] = {s.key: s.default for s in STAGES}
        self._dirty = False
        self._build()
        self._load_saved()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.title.setText("Конструктор конвейера" if ru else "Pipeline Builder")
        self.banner.setText(
            "Изменения конвейера применяются только к будущим запускам анализа. "
            "Существующие результаты не изменяются."
            if ru
            else "Pipeline changes apply only to future analysis runs. "
            "Existing results are not modified."
        )
        self.unsaved.setText(
            ("Есть несохранённые изменения" if self._dirty else "Все изменения сохранены")
            if ru
            else ("Unsaved changes" if self._dirty else "All changes saved")
        )
        for stage in STAGES:
            card = self.cards.get(stage.key)
            if not card:
                continue
            name = stage.name_ru if ru else stage.name_en
            purpose = stage.purpose_ru if ru else stage.purpose_en
            sci = stage.scientific_ru if ru else stage.scientific_en
            effect = stage.effect_ru if ru else stage.effect_en
            deps = ", ".join(stage.deps) or "—"
            status = stage.status
            if stage.key == "matlab":
                extra = (
                    f"\n{'Реализация' if ru else 'Implementation'}: {self.impl_boxes[stage.key].currentText()}\n"
                    f"{'Backend' if not ru else 'Исполнитель'}: MATLAB/Octave\n"
                    f"{'Входы' if ru else 'Expected inputs'}: frame, Amp_all\n"
                    f"{'Выходы' if ru else 'Expected outputs'}: registered features / candidates / files"
                )
            elif stage.key == "ml":
                extra = (
                    f"\n{'Модель' if ru else 'Model'}: {self.impl_boxes[stage.key].currentText()}\n"
                    f"{'Карточка модели / feature version / validation status shown when a model is selected.' if not ru else 'Карточка модели, версия признаков и статус валидации — при выборе модели.'}"
                )
            elif stage.key == "temporal":
                extra = (
                    "\n" + (
                        "Требуется ≥2 соседних кадра. Дополняет однокадровый результат, не заменяет его."
                        if ru
                        else "Requires ≥2 neighboring frames. Supplements single-frame output; does not replace it."
                    )
                )
            else:
                extra = ""
            card.setTitle(f"{name} — {status}")
            self.card_bodies[stage.key].setText(
                f"{'Назначение' if ru else 'Purpose'}: {purpose}\n"
                f"{'Статус' if ru else 'Status'}: {status}\n"
                f"{'Зависимости' if ru else 'Dependencies'}: {deps}\n"
                f"{'Научный статус' if ru else 'Scientific status'}: {sci}\n"
                f"{'Эффект на будущий анализ' if ru else 'Effect on future analysis'}: {effect}"
                + extra
            )
            self.checks[stage.key].setText("Включить этап" if ru else "Enable stage")
            if not stage.available:
                self.checks[stage.key].setEnabled(False)
                self.checks[stage.key].setToolTip(
                    "Этап недоступен и не может быть включён молча."
                    if ru
                    else "Unavailable stage cannot be enabled silently."
                )
        for button, key in self._buttons:
            labels = {
                "validate": ("Проверить", "Validate"),
                "save": ("Сохранить конвейер", "Save pipeline"),
                "save_as": ("Сохранить как новый", "Save as new pipeline"),
                "revert": ("Отменить изменения", "Revert changes"),
                "compare": ("Сравнить с сохранённым", "Compare with saved"),
                "defaults": ("Восстановить по умолчанию", "Restore defaults"),
            }
            button.setText(labels[key][0 if ru else 1])

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.title = QLabel()
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("padding:6px; border:1px solid #888;")
        self.unsaved = QLabel()
        root.addWidget(self.title)
        root.addWidget(self.banner)
        root.addWidget(self.unsaved)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host_lay = QVBoxLayout(host)
        self.card_bodies: dict[str, QLabel] = {}
        for stage in STAGES:
            card = QGroupBox()
            clay = QVBoxLayout(card)
            body = QLabel()
            body.setWordWrap(True)
            clay.addWidget(body)
            self.card_bodies[stage.key] = body
            cb = QCheckBox()
            cb.setChecked(stage.default and stage.available)
            if not stage.available:
                cb.setChecked(False)
                cb.setEnabled(False)
            cb.stateChanged.connect(self._mark_dirty)
            self.checks[stage.key] = cb
            clay.addWidget(cb)
            if stage.key in ("matlab", "ml"):
                combo = QComboBox()
                combo.addItem("none / unavailable")
                combo.setEnabled(False)
                self.impl_boxes[stage.key] = combo
                clay.addWidget(combo)
            cfg = QPushButton("Configure…" if self.i18n.language != "ru" else "Настроить…")
            cfg.setEnabled(stage.available)
            clay.addWidget(cfg)
            self.cards[stage.key] = card
            host_lay.addWidget(card)
        host_lay.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)
        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        root.addWidget(self.msg)
        row = QHBoxLayout()
        self._buttons = []
        for key, slot in [
            ("validate", self.validate),
            ("save", self.save),
            ("save_as", self.save_as),
            ("revert", self.revert),
            ("compare", self.compare_saved),
            ("defaults", self.reset),
        ]:
            b = QPushButton()
            b.clicked.connect(slot)
            self._buttons.append((b, key))
            row.addWidget(b)
        root.addLayout(row)
        self.retranslate()

    def _mark_dirty(self, *_args) -> None:
        self._dirty = True
        self.retranslate()

    def _current_cfg(self) -> dict[str, bool]:
        return {k: cb.isChecked() for k, cb in self.checks.items()}

    def _load_saved(self) -> None:
        path = app_root() / "config" / "pipeline_v11.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._saved = {s.key: bool(data.get(s.key, s.default)) for s in STAGES}
                for s in STAGES:
                    if s.key in self.checks and s.available:
                        self.checks[s.key].blockSignals(True)
                        self.checks[s.key].setChecked(self._saved[s.key])
                        self.checks[s.key].blockSignals(False)
                self._dirty = False
            except Exception:  # noqa: BLE001
                pass
        self.retranslate()

    def validate(self) -> bool:
        ru = self.i18n.language == "ru"
        enabled = {k for k, cb in self.checks.items() if cb.isChecked()}
        errors = []
        for stage in STAGES:
            if stage.key not in enabled:
                continue
            if not stage.available:
                errors.append(
                    f"{stage.name_en}: unavailable stage cannot be enabled"
                    if not ru
                    else f"{stage.name_ru}: недоступный этап нельзя включить"
                )
                continue
            for d in stage.deps:
                if d and d not in enabled:
                    errors.append(f"{stage.name_en} requires {d}" if not ru else f"{stage.name_ru} требует {d}")
        if errors:
            self.msg.setText(("Проверка не пройдена:\n" if ru else "Validation failed:\n") + "\n".join(errors))
            return False
        self.msg.setText("Зависимости конвейера в порядке." if ru else "Pipeline dependencies OK.")
        return True

    def save(self) -> None:
        if not self.validate():
            QMessageBox.warning(self, "Pipeline", self.msg.text())
            return
        cfg = self._current_cfg()
        path = ensure_dir(app_root() / "config") / "pipeline_v11.json"
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        self._saved = deepcopy(cfg)
        self._dirty = False
        if hasattr(self.session, "pipeline_config"):
            self.session.pipeline_config = cfg
        ru = self.i18n.language == "ru"
        QMessageBox.information(
            self,
            "Pipeline",
            (
                f"Сохранено: {path}\nПрименяется только к будущим запускам."
                if ru
                else f"Saved {path}\nApplies to future runs only."
            ),
        )
        self.retranslate()

    def save_as(self) -> None:
        if not self.validate():
            return
        cfg = self._current_cfg()
        path = ensure_dir(app_root() / "config" / "pipelines") / "pipeline_custom.json"
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Pipeline", str(path))

    def revert(self) -> None:
        for s in STAGES:
            if s.key in self.checks and s.available:
                self.checks[s.key].blockSignals(True)
                self.checks[s.key].setChecked(self._saved.get(s.key, s.default))
                self.checks[s.key].blockSignals(False)
        self._dirty = False
        self.retranslate()
        self.validate()

    def compare_saved(self) -> None:
        cur = self._current_cfg()
        diffs = [k for k in cur if cur[k] != self._saved.get(k)]
        ru = self.i18n.language == "ru"
        self.msg.setText(
            ("Изменения: " if ru else "Changed stages: ") + (", ".join(diffs) if diffs else ("нет" if ru else "none"))
        )

    def reset(self) -> None:
        for stage in STAGES:
            if stage.key in self.checks and stage.available:
                self.checks[stage.key].blockSignals(True)
                self.checks[stage.key].setChecked(stage.default)
                self.checks[stage.key].blockSignals(False)
        self._dirty = True
        self.retranslate()
        self.validate()
