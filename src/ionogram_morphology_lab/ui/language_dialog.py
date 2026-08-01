"""Polished first-launch language page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
)


class LanguageDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ionogram Morphology Lab")
        self.setMinimumSize(520, 320)
        self._language = "en"
        layout = QVBoxLayout(self)
        title = QLabel("Ionogram Morphology Lab\nЛаборатория морфологии ионограмм")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        desc = QLabel(
            "Standalone scientific application for ionogram morphology analysis,\n"
            "reference comparison, MATLAB Studio, and development model tools.\n\n"
            "Автономное научное приложение для морфологического анализа ионограмм,\n"
            "сопоставления с эталонами, MATLAB Studio и лаборатории моделей."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(desc)
        choose = QLabel("Choose interface language / Выберите язык интерфейса")
        choose.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(choose)
        row = QHBoxLayout()
        btn_ru = QPushButton("Русский")
        btn_en = QPushButton("English")
        btn_ru.setMinimumHeight(44)
        btn_en.setMinimumHeight(44)
        btn_ru.clicked.connect(self._choose_ru)
        btn_en.clicked.connect(self._choose_en)
        row.addWidget(btn_ru)
        row.addWidget(btn_en)
        layout.addLayout(row)
        note = QLabel("Language can be changed later in Settings → General.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

    def _choose_ru(self) -> None:
        self._language = "ru"
        self.accept()

    def _choose_en(self) -> None:
        self._language = "en"
        self.accept()

    @classmethod
    def ask_language(cls, force: bool = False) -> str | None:
        """Return language or None if first-launch already done and not forced."""
        from ionogram_morphology_lab.app.settings_store import SettingsStore

        settings = SettingsStore()
        if settings.get("general", "first_launch_done", False) and not force:
            return settings.get("general", "language", "en")
        dlg = cls()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            settings.set("general", "language", dlg._language)
            settings.set("general", "first_launch_done", True)
            settings.save()
            return dlg._language
        settings.set("general", "first_launch_done", True)
        settings.save()
        return settings.get("general", "language", "en")
