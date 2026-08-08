"""Small reusable workspace controls for readable data-heavy pages."""
from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QGroupBox, QMenu, QTableWidget, QWidget


class CollapsibleSection(QGroupBox):
    """A checkable group box which owns a body and optional collapsed summary."""

    def __init__(
        self,
        title: str = "",
        body: QWidget | None = None,
        collapsed_status: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)
        self._body = body or QWidget(self)
        self._collapsed_status = collapsed_status
        self._body.setVisible(False)
        self.toggled.connect(self._body.setVisible)

    @property
    def body(self) -> QWidget:
        return self._body

    @property
    def expanded(self) -> bool:
        return self.isChecked()

    @property
    def collapsed_status(self) -> str:
        return self._collapsed_status

    def set_collapsed_status(self, text: str) -> None:
        self._collapsed_status = text

    def set_expanded(self, expanded: bool) -> None:
        self.setChecked(bool(expanded))


class ColumnVisibilityController:
    """Attach a header menu to show named table columns without hiding essentials."""

    def __init__(
        self,
        table: QTableWidget,
        names: Iterable[str],
        essential: Iterable[int] = (),
    ) -> None:
        self.table = table
        self.names = list(names)
        self.essential = set(essential)
        self.table.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table.horizontalHeader().customContextMenuRequested.connect(self._show_menu)

    def _show_menu(self, pos) -> None:
        menu = QMenu(self.table)
        for index, name in enumerate(self.names):
            action = QAction(name, menu)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(index))
            action.setEnabled(index not in self.essential)
            action.toggled.connect(
                lambda visible, col=index: self.set_visible(col, visible)
            )
            menu.addAction(action)
        menu.addSeparator()
        reset = menu.addAction("Reset columns")
        reset.triggered.connect(self.reset)
        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    def set_names(self, names: Iterable[str]) -> None:
        """Update display names used by the column chooser (live i18n)."""
        self.names = list(names)

    def set_visible(self, column: int | str, visible: bool) -> None:
        """Show or hide a column by index or display name; essentials stay visible."""
        index = self.names.index(column) if isinstance(column, str) else column
        if index in self.essential:
            visible = True
        self.table.setColumnHidden(index, not visible)

    def reset(self) -> None:
        """Restore all columns, including any optional columns hidden by the user."""
        for column in range(self.table.columnCount()):
            self.table.setColumnHidden(column, False)
