"""Virtualized Features inspector model (Phase 4C.1c) — no eager row widgets."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel

from ionogram_morphology_lab.features.v2.registry import load_feature_registry_v2
from ionogram_morphology_lab.ui.diagnostic_summary import FEATURE_GROUPS, group_for_feature, group_title


@lru_cache(maxsize=1)
def cached_feature_registry() -> dict[str, Any]:
    return load_feature_registry_v2()


@lru_cache(maxsize=512)
def cached_feature_entry(feature_id: str) -> tuple:
    """Return (name_ru, name_en, unit) from cached registry — no YAML re-parse per row."""
    reg = cached_feature_registry()
    feats = reg.get("features") or reg.get("feature_registry") or []
    entry: dict[str, Any] = {}
    if isinstance(feats, dict):
        entry = feats.get(feature_id) or {}
    else:
        for f in feats:
            if isinstance(f, dict) and (f.get("feature_id") or f.get("id")) == feature_id:
                entry = f
                break
    return (
        str(entry.get("name_ru") or feature_id),
        str(entry.get("name_en") or feature_id),
        str(entry.get("unit") or ""),
    )


class FeaturesTableModel(QAbstractTableModel):
    COLS = ("id", "name", "value", "status", "unit", "category")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []
        self._lang = "en"
        self._show_tech = False

    def set_language(self, lang: str) -> None:
        if lang == self._lang:
            return
        self._lang = lang
        if self._rows:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def set_show_technical_ids(self, show: bool) -> None:
        self._show_tech = bool(show)
        if self._rows:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def load_from_serializable(self, ser: dict[str, Any] | None) -> None:
        """Build lightweight row records only — no widgets, no explanations."""
        self.beginResetModel()
        self._rows = []
        if not ser:
            self.endResetModel()
            return
        feats = ser.get("features") or {}
        # Touch registry once
        _ = cached_feature_registry()
        for fid, feat in sorted(feats.items()):
            if not isinstance(feat, dict):
                feat = {}
            valid = bool(feat.get("valid", True))
            g = group_for_feature(fid, valid)
            name_ru, name_en, reg_unit = cached_feature_entry(fid)
            self._rows.append(
                {
                    "id": fid,
                    "name_ru": name_ru,
                    "name_en": name_en,
                    "value": feat.get("value"),
                    "valid": valid,
                    "unit": feat.get("unit") or reg_unit or "",
                    "category": g,
                }
            )
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def feature_id_at(self, row: int) -> str | None:
        if 0 <= row < len(self._rows):
            return str(self._rows[row]["id"])
        return None

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return 5  # name, value, status, unit, category (id optional via show_tech in name)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        ru = self._lang == "ru"
        headers = (
            ("Имя", "Name"),
            ("Значение", "Value"),
            ("Статус", "Status"),
            ("Единица", "Unit"),
            ("Категория", "Category"),
        )
        if 0 <= section < len(headers):
            return headers[section][0 if ru else 1]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return row["id"]
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        col = index.column()
        ru = self._lang == "ru"
        if col == 0:
            name = row["name_ru"] if ru else row["name_en"]
            if self._show_tech:
                return f"{name} ({row['id']})"
            return name
        if col == 1:
            v = row["value"]
            if isinstance(v, bool):
                return ("да" if v else "нет") if ru else ("true" if v else "false")
            if isinstance(v, (list, tuple, dict)):
                return "—"
            return "" if v is None else str(v)
        if col == 2:
            if row["valid"]:
                return "OK" if not ru else "OK"
            return "недействительно" if ru else "invalid"
        if col == 3:
            return str(row["unit"] or "")
        if col == 4:
            return group_title(row["category"], self._lang)
        return None


class FeaturesFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._category = "all"
        self._needle = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_category(self, category: str) -> None:
        self._category = category or "all"
        self.invalidateFilter()

    def set_search(self, text: str) -> None:
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if model is None or not hasattr(model, "_rows"):
            return True
        rows = model._rows  # noqa: SLF001
        if source_row >= len(rows):
            return False
        row = rows[source_row]
        if self._category not in {"", "all"} and row.get("category") != self._category:
            return False
        if self._needle:
            blob = " ".join(
                [
                    str(row.get("id") or ""),
                    str(row.get("name_ru") or ""),
                    str(row.get("name_en") or ""),
                ]
            ).lower()
            if self._needle not in blob:
                return False
        return True


def feature_group_filter_items(lang: str) -> list[tuple[str, str]]:
    """(data, label) including 'all'."""
    items = [("all", "Все" if lang == "ru" else "All")]
    for gkey, _ru, _en, _prefixes in FEATURE_GROUPS:
        items.append((gkey, group_title(gkey, lang)))
    return items
