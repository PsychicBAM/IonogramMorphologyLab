"""Home operational dashboard with recommended workflow path."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.ui.intro_panel import IntroPanel
from ionogram_morphology_lab.ui.workflow import evaluate_workflow, next_action_text, next_recommended_step


STATUS_COLORS = {
    "completed": "#1b7f3a",
    "current": "#0b5fff",
    "incomplete": "#666666",
    "blocked": "#999999",
    "warning": "#b36b00",
    "optional": "#6a5acd",
}


class HomeDashboard(QWidget):
    navigate_to = Signal(str)  # nav key

    def __init__(self, session, i18n, settings, parent=None):
        super().__init__(parent)
        self.session = session
        self.i18n = i18n
        self.settings = settings
        self._step_buttons: list[QPushButton] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        self.intro = IntroPanel(
            "home",
            self.i18n,
            self.settings,
            purpose_en="Start here. Follow the recommended workflow instead of guessing the menu order.",
            purpose_ru="Начните здесь. Следуйте рекомендуемому порядку, не угадывая меню.",
            when_en="At first launch and whenever you return to a project.",
            when_ru="При первом запуске и при возврате к проекту.",
            action_en="Create/open a project, then press Continue recommended step.",
            action_ru="Создайте/откройте проект и нажмите «Продолжить рекомендуемый шаг».",
            after_en="The application opens the page required for the next incomplete step.",
            after_ru="Приложение откроет страницу следующего незавершённого шага.",
            risk_en="Skipping profile or cache steps can make frames unavailable.",
            risk_ru="Пропуск профиля или кэша может сделать кадры недоступными.",
            help_id="quick_start",
        )
        root.addWidget(self.intro)

        mode_row = QHBoxLayout()
        self.mode_label = QLabel()
        self.ux_mode = QComboBox()
        self.ux_mode.addItem("Guided", "guided")
        self.ux_mode.addItem("Research", "research")
        self.ux_mode.addItem("Expert", "expert")
        cur = self.settings.get("ux", "interface_mode", "guided")
        idx = max(0, self.ux_mode.findData(cur))
        self.ux_mode.setCurrentIndex(idx)
        self.ux_mode.currentIndexChanged.connect(self._save_ux_mode)
        self.mode_help = QLabel()
        self.mode_help.setWordWrap(True)
        mode_row.addWidget(self.mode_label)
        mode_row.addWidget(self.ux_mode)
        mode_row.addWidget(self.mode_help, 1)
        root.addLayout(mode_row)

        self.next_label = QLabel()
        self.next_label.setStyleSheet("font-size:15px; font-weight:600;")
        root.addWidget(self.next_label)

        actions = QGridLayout()
        self.btn_new = QPushButton()
        self.btn_open = QPushButton()
        self.btn_import = QPushButton()
        self.btn_continue = QPushButton()
        self.btn_viewer = QPushButton()
        self.btn_run = QPushButton()
        self.btn_matlab = QPushButton()
        self.btn_results = QPushButton()
        mapping = [
            (self.btn_new, "projects"),
            (self.btn_open, "projects"),
            (self.btn_import, "import"),
            (self.btn_continue, "__continue__"),
            (self.btn_viewer, "viewer"),
            (self.btn_run, "batch"),
            (self.btn_matlab, "matlab"),
            (self.btn_results, "results"),
        ]
        for i, (btn, key) in enumerate(mapping):
            btn.clicked.connect(lambda _=False, k=key: self._nav(k))
            actions.addWidget(btn, i // 4, i % 4)
        root.addLayout(actions)

        status = QGroupBox()
        self.status_box = status
        sl = QVBoxLayout(status)
        self.status_project = QLabel()
        self.status_data = QLabel()
        self.status_profile = QLabel()
        self.status_cache = QLabel()
        self.status_frame = QLabel()
        self.status_run = QLabel()
        for w in (
            self.status_project,
            self.status_data,
            self.status_profile,
            self.status_cache,
            self.status_frame,
            self.status_run,
        ):
            w.setWordWrap(True)
            sl.addWidget(w)
        root.addWidget(status)

        self.workflow_box = QGroupBox()
        self.workflow_layout = QVBoxLayout(self.workflow_box)
        root.addWidget(self.workflow_box, 1)
        self.disclaimer = QLabel()
        self.disclaimer.setWordWrap(True)
        self.disclaimer.setStyleSheet("color:#6b3a00;")
        root.addWidget(self.disclaimer)

    def _save_ux_mode(self) -> None:
        mode = self.ux_mode.currentData()
        self.settings.set("ux", "interface_mode", mode)
        self.settings.save()
        self.retranslate()

    def _nav(self, key: str) -> None:
        if key == "__continue__":
            step = next_recommended_step(self.session)
            self.navigate_to.emit(step.nav_key)
            return
        self.navigate_to.emit(key)

    def refresh(self) -> None:
        lang = self.i18n.language
        self.next_label.setText(next_action_text(self.session, lang))
        proj = self.session.project
        self.status_project.setText(
            ("Проект: " if lang == "ru" else "Project: ")
            + (proj.name if proj else ("нет" if lang == "ru" else "none"))
        )
        mat = self.session.active_mat
        self.status_data.setText(
            ("Данные: " if lang == "ru" else "Data: ")
            + (mat.name if mat else ("не импортированы" if lang == "ru" else "not imported"))
        )
        self.status_profile.setText(
            ("Профиль: " if lang == "ru" else "Profile: ") + str(self.session.profile_id)
        )
        cache = "—"
        try:
            if self.session.has_real_import():
                st = self.session.ensure_store().status()
                cache = "ready" if st.valid else (st.reason or "not ready")
        except Exception as exc:
            cache = str(exc)
        self.status_cache.setText(("Кэш: " if lang == "ru" else "Cache: ") + cache)
        self.status_frame.setText(
            ("Кадр: " if lang == "ru" else "Frame: ") + str(self.session.current_frame)
        )
        run = self.session.last_run_root
        self.status_run.setText(
            ("Последний запуск: " if lang == "ru" else "Last run: ")
            + (run.name if run else ("нет" if lang == "ru" else "none"))
        )

        while self.workflow_layout.count():
            item = self.workflow_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._step_buttons.clear()
        for step in evaluate_workflow(self.session):
            btn = QPushButton(f"[{step.status}] {step.title(lang)}")
            color = STATUS_COLORS.get(step.status, "#333")
            btn.setStyleSheet(f"text-align:left; color:{color}; padding:6px;")
            if step.status == "blocked":
                btn.setEnabled(False)
            btn.clicked.connect(lambda _=False, k=step.nav_key: self.navigate_to.emit(k))
            self.workflow_layout.addWidget(btn)
            self._step_buttons.append(btn)
        self.retranslate()

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.intro.retranslate()
        self.mode_label.setText("Режим интерфейса" if ru else "Interface complexity")
        self.mode_help.setText(
            "Guided / Research / Expert меняют только сложность интерфейса, не научные пороги. "
            "Режим анализа (Scientific Strict и др.) настраивается отдельно в Настройках."
            if ru
            else "Guided / Research / Expert change interface complexity only — not scientific thresholds. "
            "Analysis mode (Scientific Strict, etc.) is configured separately in Settings."
        )
        self.btn_new.setText("Новый проект" if ru else "New Project")
        self.btn_open.setText("Открыть проект" if ru else "Open Project")
        self.btn_import.setText("Импорт MAT" if ru else "Import MAT Data")
        self.btn_continue.setText("Продолжить рекомендуемый шаг" if ru else "Continue Recommended Step")
        self.btn_viewer.setText("Просмотр ионограмм" if ru else "Open Ionogram Viewer")
        self.btn_run.setText("Запуск анализа" if ru else "Run Analysis")
        self.btn_matlab.setText("MATLAB Studio" if ru else "Open MATLAB Studio")
        self.btn_results.setText("Результаты" if ru else "View Results")
        self.status_box.setTitle("Состояние" if ru else "Status")
        self.workflow_box.setTitle("Рекомендуемый порядок работы" if ru else "Recommended workflow")
        self.disclaimer.setText(
            "Результаты — кандидатная морфология. Приложение не подтверждает физический механизм только по изображению."
            if ru
            else "Results are candidate morphology. The application does not confirm physical mechanisms from images alone."
        )
        # refresh labels that depend on language
        self.next_label.setText(next_action_text(self.session, self.i18n.language))
