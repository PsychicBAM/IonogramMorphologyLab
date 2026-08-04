"""Scientific Rule Builder — no-code wizard with advanced code tab."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.features.registry import FEATURE_REGISTRY, list_features
from ionogram_morphology_lab.rule_builder.codegen import generate_matlab_function, generate_python_rule
from ionogram_morphology_lab.rule_builder.examples import (
    PROPOSED_RESULTS,
    TARGET_HELP,
    THRESHOLD_ORIGIN_HELP,
    builtin_examples,
    copy_example_to_draft,
)
from ionogram_morphology_lab.rule_builder.model import RULE_TARGETS, ScientificRule
from ionogram_morphology_lab.rule_builder.nl_preview import preview_both
from ionogram_morphology_lab.rule_builder.store import RuleStore
from ionogram_morphology_lab.ui.intro_panel import IntroPanel


class RuleBuilderPage(QWidget):
    """Nine-step visual wizard; programming is never required for ordinary rules."""

    def __init__(self, session, i18n, settings=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.settings = settings or getattr(session, "settings", None)
        self.store = RuleStore()
        self._step = 0
        self._conditions: list[dict] = []
        self._build()
        self.refresh()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self._localize_static_widgets(ru)
        self.banner.setText(
            "Для создания правила программирование не требуется."
            if ru
            else "No programming is required to create a rule."
        )
        self.note.setText(
            "Шаблоны примеров нельзя менять напрямую — только копию в черновик. "
            "Статусы правил различаются явно; Scientific Strict активирует только утверждённые."
            if ru
            else "Example templates cannot be edited directly — copy to a draft first. "
            "Rule statuses are explicit; Scientific Strict activates only approved statuses."
        )
        labels = [
            "1. Purpose",
            "2. Result",
            "3. Conditions",
            "4. Exclusions",
            "5. Source",
            "6. Threshold",
            "7. Preview",
            "8. Test",
            "9. Save",
        ]
        if ru:
            labels = [
                "1. Цель",
                "2. Результат",
                "3. Условия",
                "4. Исключения",
                "5. Источник",
                "6. Порог",
                "7. Предпросмотр",
                "8. Тест",
                "9. Сохранение",
            ]
        for i, lab in enumerate(labels):
            self.step_list.item(i).setText(lab)
        self.btn_prev.setText("Назад" if ru else "Back")
        self.btn_next.setText("Далее" if ru else "Next")
        self.btn_save.setText("Сохранить" if ru else "Save")
        self.examples_label.setText(self.i18n.t("rule.examples"))
        self.btn_copy_example.setText(self.i18n.t("rule.copy_example"))
        self.saved_label.setText(self.i18n.t("rule.saved"))
        self.btn_load_saved.setText(self.i18n.t("rule.load_saved"))
        self.btn_show_advanced.setText(self.i18n.t("rule.show_advanced"))
        self.tabs_adv.setTabText(0, self.i18n.t("rule.advanced"))
        if self.settings and hasattr(self, "intro"):
            self.intro.retranslate()
        self._update_target_help()
        self._update_threshold_help()
        self._refresh_preview()

    def _localize_static_widgets(self, ru: bool) -> None:
        """Translate instructional controls while leaving canonical tokens untouched."""
        translations = {
            "Copy example → draft": "Скопировать пример → черновик",
            "Load saved": "Загрузить сохранённое",
            "Examples:": "Примеры:",
            "Saved:": "Сохранённые:",
            "Advanced: generated Python / MATLAB / JSON only (optional).": "Дополнительно: только сгенерированные Python / MATLAB / JSON (необязательно).",
            "Show / hide Advanced tab": "Показать / скрыть вкладку «Дополнительно»",
            "Choose exactly one target axis:": "Выберите ровно одну целевую ось:",
            "Canonical proposed result:": "Канонический предлагаемый результат:",
            "Visual condition blocks (AND between rows; OR via nested group flag):": "Блоки визуальных условий (И между строками; ИЛИ — через флаг группы):",
            "OR group with previous": "Группа ИЛИ с предыдущим",
            "Add condition": "Добавить условие",
            "Clear conditions": "Очистить условия",
            "Do not activate when vertical interference dominates": "Не активировать при доминирующих вертикальных помехах",
            "Abstain when trace quality is poor": "Воздержаться при низком качестве трассы",
            "Add possible O/X as an alternative": "Добавить возможный O/X как альтернативу",
            "Disable for incompatible profiles": "Отключить для несовместимых профилей",
            "Additional exclusions:": "Дополнительные исключения:",
            "Alternatives:": "Альтернативы:",
            "Source Assistant — incomplete source may only be draft / imported_unverified / development.": "Помощник по источнику: неполный источник допускается только для черновика / непроверенного импорта / разработки.",
            "Rule ID": "ID правила",
            "Name EN": "Название EN",
            "Name RU": "Название RU",
            "Source ID": "ID источника",
            "Authors": "Авторы",
            "Year": "Год",
            "Title": "Название",
            "Type": "Тип",
            "Printed page": "Печатная страница",
            "PDF page": "Страница PDF",
            "Source wording": "Формулировка источника",
            "User paraphrase": "Перефразировка пользователя",
            "Applicability": "Применимость",
            "Assumptions": "Допущения",
            "Limitations": "Ограничения",
            "Rights note": "Примечание о правах",
            "Threshold origin:": "Источник порога:",
            "Natural-language preview (EN):": "Предпросмотр на естественном языке (EN):",
            "Natural-language preview (RU):": "Предпросмотр на естественном языке (RU):",
            "Refresh preview + generated code": "Обновить предпросмотр и сгенерированный код",
            "Run rule test (dry evaluation)": "Запустить проверку правила (без выполнения конвейера)",
            "Test scope:": "Область проверки:",
            "Save as:": "Сохранить как:",
        }
        for cls in (QLabel, QPushButton, QCheckBox):
            for widget in self.findChildren(cls):
                english = widget.property("iml_en_text") or widget.text()
                if english in translations:
                    widget.setProperty("iml_en_text", english)
                    widget.setText(translations[english] if ru else english)
        placeholders = {
            "Extra exclusion phrases, one per line": "Дополнительные фразы исключений, по одной на строку",
            "comma-separated alternatives": "альтернативы через запятую",
        }
        for cls in (QLineEdit, QPlainTextEdit):
            for widget in self.findChildren(cls):
                english = widget.property("iml_en_placeholder") or widget.placeholderText()
                if english in placeholders:
                    widget.setProperty("iml_en_placeholder", english)
                    widget.setPlaceholderText(placeholders[english] if ru else english)
        if hasattr(self, "tabs_adv"):
            self.tabs_adv.setTabText(0, "Дополнительно" if ru else "Advanced")

    def _build(self) -> None:
        root = QVBoxLayout(self)
        if self.settings is not None:
            self.intro = IntroPanel(
                "rules",
                self.i18n,
                self.settings,
                purpose_en="Create scientific rules with a visual wizard — no Python or MATLAB required.",
                purpose_ru="Создавайте научные правила визуальным мастером — без Python и MATLAB.",
                when_en="When you need a custom candidate proposal with documented conditions and source status.",
                when_ru="Когда нужен свой кандидатный вывод с документированными условиями и статусом источника.",
                action_en="Follow steps 1–9, then Save as Draft / Development / User tested / Project approved.",
                action_ru="Пройдите шаги 1–9 и сохраните как Черновик / Разработка / Протестировано / Утверждено.",
                after_en="A versioned rule is stored; code is generated only under the Advanced tab.",
                after_ru="Сохраняется версия правила; код появляется только на вкладке Advanced.",
                risk_en="Marking a rule source-verified without a real source is blocked.",
                risk_ru="Пометка source-verified без реального источника блокируется.",
                help_id="rules_nocode",
            )
            root.addWidget(self.intro)

        self.banner = QLabel()
        self.banner.setStyleSheet(
            "background:#e8f5e9; border:1px solid #2e7d32; color:#1b5e20; "
            "padding:10px; font-weight:700; font-size:14px;"
        )
        self.banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.banner)
        self.note = QLabel()
        self.note.setWordWrap(True)
        root.addWidget(self.note)

        top = QHBoxLayout()
        self.examples = QComboBox()
        for ex in builtin_examples():
            self.examples.addItem(f"{ex.rule_id}: {ex.name_en}", ex.rule_id)
        btn_ex = QPushButton()
        btn_ex.setObjectName("btn_copy_example")
        btn_ex.clicked.connect(self._copy_example)
        self.btn_copy_example = btn_ex
        self.saved_list = QComboBox()
        btn_load = QPushButton()
        btn_load.clicked.connect(self._load_saved)
        self.btn_load_saved = btn_load
        self.examples_label = QLabel()
        top.addWidget(self.examples_label)
        top.addWidget(self.examples, 1)
        top.addWidget(btn_ex)
        self.saved_label = QLabel()
        top.addWidget(self.saved_label)
        top.addWidget(self.saved_list, 1)
        top.addWidget(btn_load)
        root.addLayout(top)

        body = QHBoxLayout()
        self.step_list = QListWidget()
        for i in range(9):
            self.step_list.addItem(str(i + 1))
        self.step_list.currentRowChanged.connect(self._goto_step)
        self.step_list.setFixedWidth(180)
        body.addWidget(self.step_list)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._step_purpose())
        self.stack.addWidget(self._step_result())
        self.stack.addWidget(self._step_conditions())
        self.stack.addWidget(self._step_exclusions())
        self.stack.addWidget(self._step_source())
        self.stack.addWidget(self._step_threshold())
        self.stack.addWidget(self._step_preview())
        self.stack.addWidget(self._step_test())
        self.stack.addWidget(self._step_save())
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("Back")
        self.btn_next = QPushButton("Next")
        self.btn_save = QPushButton("Save")
        self.btn_prev.clicked.connect(lambda: self._goto_step(max(0, self._step - 1)))
        self.btn_next.clicked.connect(lambda: self._goto_step(min(8, self._step + 1)))
        self.btn_save.clicked.connect(self._save)
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        nav.addStretch(1)
        nav.addWidget(self.btn_save)
        root.addLayout(nav)

        self.tabs_adv = QTabWidget()
        self.gen_py = QPlainTextEdit()
        self.gen_py.setReadOnly(True)
        self.gen_m = QPlainTextEdit()
        self.gen_m.setReadOnly(True)
        self.machine = QPlainTextEdit()
        self.machine.setReadOnly(True)
        adv = QWidget()
        al = QVBoxLayout(adv)
        al.addWidget(QLabel("Advanced: generated Python / MATLAB / JSON only (optional)."))
        al.addWidget(self.gen_py, 1)
        al.addWidget(self.gen_m, 1)
        al.addWidget(self.machine, 1)
        self.tabs_adv.addTab(adv, "")
        # Collapse advanced for guided mode
        mode = "guided"
        if self.settings:
            mode = self.settings.get("ux", "interface_mode", "guided")
        self.tabs_adv.setVisible(mode == "expert")
        btn_adv = QPushButton()
        btn_adv.clicked.connect(lambda: self.tabs_adv.setVisible(not self.tabs_adv.isVisible()))
        self.btn_show_advanced = btn_adv
        root.addWidget(btn_adv)
        root.addWidget(self.tabs_adv)
        self.step_list.setCurrentRow(0)
        self.retranslate()

    def _wrap_label(self, text: str) -> QWidget:
        w = QWidget()
        QVBoxLayout(w).addWidget(QLabel(text))
        return w

    def _step_purpose(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Choose exactly one target axis:"))
        self.target = QComboBox()
        self.target.addItems(list(RULE_TARGETS))
        self.target.currentTextChanged.connect(self._update_target_help)
        self.target_help = QLabel()
        self.target_help.setWordWrap(True)
        lay.addWidget(self.target)
        lay.addWidget(self.target_help)
        self.rule_id = QLineEdit("USER_RULE_001")
        self.name_en = QLineEdit("New user rule")
        self.name_ru = QLineEdit("Новое пользовательское правило")
        form = QFormLayout()
        form.addRow("Rule ID", self.rule_id)
        form.addRow("Name EN", self.name_en)
        form.addRow("Name RU", self.name_ru)
        lay.addLayout(form)
        lay.addStretch(1)
        return w

    def _step_result(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Canonical proposed result:"))
        self.proposed = QComboBox()
        self.proposed.setEditable(True)
        self.proposed.addItems(PROPOSED_RESULTS)
        lay.addWidget(self.proposed)
        self.result_help = QLabel(
            "Examples: F2, Es, frequency_spread, range_spread, mixed_spread, "
            "possible_O_X, vertical_interference, poor_quality."
        )
        self.result_help.setWordWrap(True)
        lay.addWidget(self.result_help)
        lay.addStretch(1)
        return w

    def _step_conditions(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Visual condition blocks (AND between rows; OR via nested group flag):"))
        row = QHBoxLayout()
        self.feature = QComboBox()
        self.feature.addItems(list_features())
        self.feature.currentTextChanged.connect(self._update_feature_help)
        self.operator = QComboBox()
        self.operator.addItems(
            [
                "gt",
                "gte",
                "lt",
                "lte",
                "eq",
                "ne",
                "between",
                "present",
                "absent",
                "persistent_n",
                "appears_n_of_m",
            ]
        )
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(-1e6, 1e6)
        self.threshold.setDecimals(4)
        self.threshold.setValue(0.5)
        self.threshold2 = QDoubleSpinBox()
        self.threshold2.setRange(-1e6, 1e6)
        self.threshold2.setDecimals(4)
        self.or_group = QCheckBox("OR group with previous")
        add = QPushButton("Add condition")
        add.clicked.connect(self._add_condition)
        clear = QPushButton("Clear conditions")
        clear.clicked.connect(self._clear_conditions)
        for widget in (self.feature, self.operator, self.threshold, self.threshold2, self.or_group, add, clear):
            row.addWidget(widget)
        lay.addLayout(row)
        self.feature_help = QLabel()
        self.feature_help.setWordWrap(True)
        lay.addWidget(self.feature_help)
        self.cond_list = QListWidget()
        lay.addWidget(self.cond_list, 1)
        self._update_feature_help()
        return w

    def _step_exclusions(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.excl_interf = QCheckBox("Do not activate when vertical interference dominates")
        self.excl_poor = QCheckBox("Abstain when trace quality is poor")
        self.excl_ox = QCheckBox("Add possible O/X as an alternative")
        self.excl_profile = QCheckBox("Disable for incompatible profiles")
        self.exclusions_extra = QPlainTextEdit()
        self.exclusions_extra.setPlaceholderText("Extra exclusion phrases, one per line")
        self.alternatives = QLineEdit()
        self.alternatives.setPlaceholderText("comma-separated alternatives")
        for x in (self.excl_interf, self.excl_poor, self.excl_ox, self.excl_profile):
            lay.addWidget(x)
        lay.addWidget(QLabel("Additional exclusions:"))
        lay.addWidget(self.exclusions_extra)
        lay.addWidget(QLabel("Alternatives:"))
        lay.addWidget(self.alternatives)
        lay.addStretch(1)
        return w

    def _step_source(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Source Assistant — incomplete source may only be draft / imported_unverified / development."))
        form = QFormLayout()
        self.src_authors = QLineEdit()
        self.src_year = QLineEdit()
        self.src_title = QLineEdit()
        self.src_type = QComboBox()
        self.src_type.addItems(["article", "book", "manual", "other"])
        self.src_doi = QLineEdit()
        self.src_printed = QLineEdit()
        self.src_pdf = QLineEdit()
        self.src_wording = QPlainTextEdit()
        self.src_paraphrase = QPlainTextEdit()
        self.src_applicability = QLineEdit()
        self.src_assumptions = QPlainTextEdit()
        self.src_limitations = QPlainTextEdit()
        self.src_rights = QLineEdit()
        self.source_id = QLineEdit()
        for lab, widget in [
            ("Source ID", self.source_id),
            ("Authors", self.src_authors),
            ("Year", self.src_year),
            ("Title", self.src_title),
            ("Type", self.src_type),
            ("DOI / ISBN", self.src_doi),
            ("Printed page", self.src_printed),
            ("PDF page", self.src_pdf),
            ("Source wording", self.src_wording),
            ("User paraphrase", self.src_paraphrase),
            ("Applicability", self.src_applicability),
            ("Assumptions", self.src_assumptions),
            ("Limitations", self.src_limitations),
            ("Rights note", self.src_rights),
        ]:
            form.addRow(lab, widget)
        lay.addLayout(form)
        return w

    def _step_threshold(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.threshold_origin = QComboBox()
        self.threshold_origin.addItems(list(THRESHOLD_ORIGIN_HELP.keys()))
        self.threshold_origin.currentTextChanged.connect(self._update_threshold_help)
        self.threshold_help = QLabel()
        self.threshold_help.setWordWrap(True)
        self.score = QDoubleSpinBox()
        self.score.setRange(0, 1)
        self.score.setSingleStep(0.05)
        self.score.setValue(0.5)
        lay.addWidget(QLabel("Threshold origin:"))
        lay.addWidget(self.threshold_origin)
        lay.addWidget(self.threshold_help)
        form = QFormLayout()
        form.addRow("Score", self.score)
        lay.addLayout(form)
        lay.addStretch(1)
        return w

    def _step_preview(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.preview_en = QTextEdit()
        self.preview_en.setReadOnly(True)
        self.preview_ru = QTextEdit()
        self.preview_ru.setReadOnly(True)
        lay.addWidget(QLabel("Natural-language preview (EN):"))
        lay.addWidget(self.preview_en, 1)
        lay.addWidget(QLabel("Natural-language preview (RU):"))
        lay.addWidget(self.preview_ru, 1)
        btn = QPushButton("Refresh preview + generated code")
        btn.clicked.connect(self._refresh_preview)
        lay.addWidget(btn)
        return w

    def _step_test(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.test_scope = QComboBox()
        self.test_scope.addItems(["current_frame", "current_sequence", "selected_frames", "labeled_dev_set"])
        btn = QPushButton("Run rule test (dry evaluation)")
        btn.clicked.connect(self._run_test)
        self.test_out = QTextEdit()
        self.test_out.setReadOnly(True)
        lay.addWidget(QLabel("Test scope:"))
        lay.addWidget(self.test_scope)
        lay.addWidget(btn)
        lay.addWidget(self.test_out, 1)
        return w

    def _step_save(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.save_status = QComboBox()
        self.save_status.addItems(["draft", "development", "user_tested", "project_approved"])
        # map development → draft/imported style for model
        lay.addWidget(QLabel("Save as:"))
        lay.addWidget(self.save_status)
        self.save_help = QLabel(
            "Version history is created automatically. "
            "source_verified is never assigned silently — complete the Source Assistant first."
        )
        self.save_help.setWordWrap(True)
        lay.addWidget(self.save_help)
        lay.addStretch(1)
        return w

    def _update_target_help(self) -> None:
        ru = self.i18n.language == "ru"
        key = self.target.currentText()
        info = TARGET_HELP.get(key, {})
        self.target_help.setText(info.get("ru" if ru else "en", ""))

    def _update_threshold_help(self) -> None:
        ru = self.i18n.language == "ru"
        key = self.threshold_origin.currentText()
        info = THRESHOLD_ORIGIN_HELP.get(key, {})
        self.threshold_help.setText(info.get("ru" if ru else "en", ""))

    def _update_feature_help(self) -> None:
        name = self.feature.currentText()
        meta = FEATURE_REGISTRY.get(name, {})
        ru = self.i18n.language == "ru"
        text = (
            f"<b>{name}</b><br>"
            f"{'Пояснение' if ru else 'Meaning'}: {meta.get('interpretation', '')}<br>"
            f"{'Ед.' if ru else 'Unit'}: {meta.get('units', '')}<br>"
            f"{'Источник признака' if ru else 'Feature source'}: {meta.get('input', '')}<br>"
            f"{'Ограничения' if ru else 'Limitations'}: {meta.get('limitations', '')}<br>"
            f"{'Определение' if ru else 'Definition'}: {meta.get('definition', '')}"
        )
        self.feature_help.setText(text)

    def _add_condition(self) -> None:
        cond = {
            "feature": self.feature.currentText(),
            "operator": self.operator.currentText(),
            "value": float(self.threshold.value()),
            "join": "or" if self.or_group.isChecked() else "and",
        }
        if self.operator.currentText() == "between":
            cond["value2"] = float(self.threshold2.value())
        self._conditions.append(cond)
        self.cond_list.addItem(
            f"{cond['join'].upper()} {cond['feature']} {cond['operator']} {cond['value']}"
            + (f" .. {cond.get('value2')}" if "value2" in cond else "")
        )

    def _clear_conditions(self) -> None:
        self._conditions.clear()
        self.cond_list.clear()

    def _current_rule(self) -> ScientificRule:
        target = self.target.currentText()
        proposed = self.proposed.currentText().strip()
        exclusions: list[str] = []
        if self.excl_interf.isChecked():
            exclusions.append("vertical interference dominates")
        if self.excl_profile.isChecked():
            exclusions.append("incompatible instrument profile")
        extra = [x.strip() for x in self.exclusions_extra.toPlainText().splitlines() if x.strip()]
        exclusions.extend(extra)
        alts = [a.strip() for a in self.alternatives.text().split(",") if a.strip()]
        if self.excl_ox.isChecked() and "possible_O_X" not in alts:
            alts.append("possible_O_X")
        abst = "trace quality poor" if self.excl_poor.isChecked() else ""
        status_ui = self.save_status.currentText()
        status_map = {
            "draft": "draft",
            "development": "draft",
            "user_tested": "user_tested",
            "project_approved": "project_approved",
        }
        status = status_map.get(status_ui, "draft")
        # Incomplete source cannot be silently verified
        has_source = bool(self.source_id.text().strip() or self.src_title.text().strip())
        if status == "project_approved" and not has_source:
            status = "draft"
        meta = {
            "source_type": self.src_type.currentText(),
            "doi_isbn": self.src_doi.text().strip(),
            "paraphrase": self.src_paraphrase.toPlainText().strip(),
            "applicability": self.src_applicability.text().strip(),
            "save_as_ui": status_ui,
        }
        return ScientificRule(
            rule_id=self.rule_id.text().strip() or "USER_RULE",
            name_en=self.name_en.text().strip() or "User rule",
            name_ru=self.name_ru.text().strip() or "Пользовательское правило",
            category=target,
            conditions=list(self._conditions)
            or [
                {
                    "feature": self.feature.currentText(),
                    "operator": self.operator.currentText(),
                    "value": float(self.threshold.value()),
                }
            ],
            outputs={target: proposed} if proposed else {},
            proposed_result=proposed,
            status=status,
            enabled=status not in {"disabled", "rejected"},
            source_ids=[self.source_id.text().strip()] if self.source_id.text().strip() else [],
            source_pages=[p for p in [self.src_printed.text().strip(), self.src_pdf.text().strip()] if p],
            source_wording_en=self.src_wording.toPlainText().strip(),
            feature_names=[c.get("feature", "") for c in self._conditions] or [self.feature.currentText()],
            score=float(self.score.value()),
            threshold_origin=self.threshold_origin.currentText(),
            exclusions=exclusions,
            alternatives=alts,
            abstention_condition=abst,
            assumptions=[a.strip() for a in self.src_assumptions.toPlainText().splitlines() if a.strip()],
            limitations=[a.strip() for a in self.src_limitations.toPlainText().splitlines() if a.strip()],
            verification_status="unverified" if not has_source else "source_metadata_complete",
            implementation_status="active" if status in {"user_tested", "project_approved"} else "disabled",
            version="1.1.1",
            authors=self.src_authors.text().strip(),
            year=self.src_year.text().strip(),
            title=self.src_title.text().strip(),
            printed_page=self.src_printed.text().strip(),
            pdf_page=self.src_pdf.text().strip(),
            quotation=self.src_wording.toPlainText().strip(),
            rights_note=self.src_rights.text().strip(),
            applicable_domain=self.src_applicability.text().strip(),
            metadata=meta,
        )

    def _refresh_preview(self) -> None:
        rule = self._current_rule()
        en, ru = preview_both(rule)
        self.preview_en.setPlainText(en)
        self.preview_ru.setPlainText(ru)
        self.machine.setPlainText(json.dumps(rule.to_dict(), indent=2, ensure_ascii=False))
        try:
            self.gen_py.setPlainText(generate_python_rule(rule))
            self.gen_m.setPlainText(generate_matlab_function(rule))
        except Exception as exc:  # noqa: BLE001
            self.gen_py.setPlainText(str(exc))
            self.gen_m.setPlainText(str(exc))

    def _run_test(self) -> None:
        rule = self._current_rule()
        scope = self.test_scope.currentText()
        # Dry evaluation: report conditions structure + whether features exist
        lines = [
            f"Scope: {scope}",
            f"Rule: {rule.rule_id}",
            f"Proposed: {rule.proposed_result}",
            f"Status: {rule.status}",
            "",
            "Conditions:",
        ]
        for c in rule.conditions:
            feat = c.get("feature")
            known = feat in FEATURE_REGISTRY
            lines.append(
                f"  - {feat} {c.get('operator')} {c.get('value')} "
                f"[{'OK feature' if known else 'UNKNOWN feature'}]"
            )
        if rule.exclusions:
            lines.append("Exclusions: " + "; ".join(rule.exclusions))
        if rule.abstention_condition:
            lines.append("Abstention: " + rule.abstention_condition)
        if rule.alternatives:
            lines.append("Alternatives: " + ", ".join(rule.alternatives))
        # Optional: pull current frame features if available
        try:
            if self.session.has_real_import() and scope == "current_frame":
                lines.append("")
                lines.append(
                    f"Current frame index: {self.session.current_frame} "
                    "(full feature evaluation runs in Rule Testing Lab)."
                )
        except Exception:
            pass
        lines.append("")
        lines.append("Open Rule Testing Lab for labeled dataset sweeps.")
        self.test_out.setPlainText("\n".join(lines))
        self._refresh_preview()

    def _goto_step(self, row: int) -> None:
        if row < 0:
            return
        self._step = row
        self.stack.setCurrentIndex(row)
        self.step_list.setCurrentRow(row)
        if row == 6:
            self._refresh_preview()

    def _copy_example(self) -> None:
        rid = self.examples.currentData()
        for ex in builtin_examples():
            if ex.rule_id == rid:
                draft = copy_example_to_draft(ex)
                self._apply_rule(draft)
                QMessageBox.information(
                    self,
                    "Rule Builder",
                    "Example copied into an editable draft. Built-in originals stay unchanged.",
                )
                return

    def _apply_rule(self, r: ScientificRule) -> None:
        self.rule_id.setText(r.rule_id)
        self.name_en.setText(r.name_en)
        self.name_ru.setText(r.name_ru)
        if r.category in RULE_TARGETS:
            self.target.setCurrentText(r.category)
        idx = self.proposed.findText(r.proposed_result)
        if idx >= 0:
            self.proposed.setCurrentIndex(idx)
        else:
            self.proposed.setEditText(r.proposed_result)
        self._clear_conditions()
        for c in r.conditions:
            self._conditions.append(dict(c))
            self.cond_list.addItem(
                f"{c.get('join', 'and').upper()} {c.get('feature')} {c.get('operator')} {c.get('value')}"
            )
        self.excl_interf.setChecked(any("interference" in x.lower() for x in r.exclusions))
        self.excl_poor.setChecked(bool(r.abstention_condition))
        self.excl_ox.setChecked("possible_O_X" in (r.alternatives or []))
        self.alternatives.setText(",".join(r.alternatives))
        self.exclusions_extra.setPlainText("\n".join(r.exclusions))
        if r.source_ids:
            self.source_id.setText(r.source_ids[0])
        self.src_authors.setText(r.authors)
        self.src_year.setText(r.year)
        self.src_title.setText(r.title)
        self.src_wording.setPlainText(r.quotation or r.source_wording_en)
        self.src_limitations.setPlainText("\n".join(r.limitations))
        if r.threshold_origin in THRESHOLD_ORIGIN_HELP:
            self.threshold_origin.setCurrentText(r.threshold_origin)
        self.score.setValue(float(r.score or 0.5))
        self.save_status.setCurrentText("draft")
        self._refresh_preview()
        self._goto_step(0)

    def _load_saved(self) -> None:
        text = self.saved_list.currentText()
        if not text:
            return
        rid = text.split(" ")[0]
        for r in self.store.list_rules():
            if r.rule_id == rid:
                if r.metadata.get("builtin_example") and not r.metadata.get("editable_original", True):
                    QMessageBox.warning(self, "Rule Builder", "Built-in example originals are read-only.")
                    return
                self._apply_rule(r)
                return

    def _save(self) -> None:
        rule = self._current_rule()
        ui_status = self.save_status.currentText()
        has_source = bool(rule.source_ids or rule.title)
        if ui_status == "project_approved" and not has_source:
            QMessageBox.warning(
                self,
                "Rule Builder",
                "Project approved requires source metadata. Saved as draft instead of silently verifying.",
            )
            rule.status = "draft"
            self.save_status.setCurrentText("draft")
        if rule.status in {"source_verified", "project_approved", "externally_reviewed"} and not rule.source_ids:
            QMessageBox.warning(self, "Rule Builder", "Verified statuses require a source ID.")
            return
        if not rule.name_en.strip() or not rule.rule_id.strip():
            QMessageBox.warning(self, "Rule Builder", "Rule ID and name are required.")
            return
        # Duplicate ID warning for conflicting content is handled by versioning in store
        path = self.store.save_rule(rule, comment=f"wizard save ({ui_status})")
        self._refresh_preview()
        self.refresh()
        QMessageBox.information(self, "Rule Builder", f"Saved versioned rule:\n{path}")

    def refresh(self) -> None:
        self.saved_list.clear()
        for r in self.store.list_rules():
            self.saved_list.addItem(f"{r.rule_id} [{r.status}] {r.name_en}")
