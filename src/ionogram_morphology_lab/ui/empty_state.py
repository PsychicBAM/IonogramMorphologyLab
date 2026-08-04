"""Guided empty states for pages without data."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyStatePanel(QWidget):
    """Why empty / prerequisite / action — avoids unexplained blank areas."""

    action_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-weight:700; font-size:14px;")
        self.why = QLabel()
        self.why.setWordWrap(True)
        self.prereq = QLabel()
        self.prereq.setWordWrap(True)
        self.after = QLabel()
        self.after.setWordWrap(True)
        self.action_btn = QPushButton()
        self.action_btn.clicked.connect(self._emit)
        self._nav_key = ""
        lay.addWidget(self.title)
        lay.addWidget(self.why)
        lay.addWidget(self.prereq)
        lay.addWidget(self.after)
        lay.addWidget(self.action_btn)
        lay.addStretch(1)

    def _emit(self) -> None:
        if self._nav_key:
            self.action_requested.emit(self._nav_key)

    def configure(
        self,
        *,
        title: str,
        why: str,
        prereq: str,
        after: str,
        action: str,
        nav_key: str,
    ) -> None:
        self.title.setText(title)
        self.why.setText(why)
        self.prereq.setText(prereq)
        self.after.setText(after)
        self.action_btn.setText(action)
        self._nav_key = nav_key
        self.action_btn.setVisible(bool(nav_key and action))
