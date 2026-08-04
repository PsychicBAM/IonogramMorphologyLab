"""Single active MAT source state — shared by Viewer, Batch, Diagnostics, MATLAB Studio.

Phase 4B.2k: warm UI reads a session-held ActiveSourceSnapshot. MAT open/stat/classify
happen only on import, activation, explicit refresh, or identity change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.ui.source_roles import SourceRole, localize_role_message
from ionogram_morphology_lab.ui.theme import refresh_themed_widget, resolve_theme_name, source_card_tokens


class SourceStatus(str, Enum):
    NO_PROJECT = "no_project"
    NO_MAT = "no_mat"
    INVENTORY_INACTIVE = "inventory_inactive"
    MISSING = "missing"
    NOT_LOADED = "not_loaded"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"


@dataclass
class ActiveSourceSnapshot:
    """Immutable-enough source-of-truth view for UI rendering (Phase 4B.2k)."""

    project_name: str = ""
    project_id: str = ""
    project_open: bool = False
    mat_path: Path | None = None
    mat_filename: str = ""
    source_size: int = 0
    source_mtime_ns: int = 0
    in_inventory: bool = False
    is_active: bool = False
    variable: str = "Amp_all"
    shape: str = ""
    dtype: str = ""
    frame_count: int = 1440
    profile_id: str = ""
    profile_version: str = ""
    signal_contract_id: str = "kfu_amp_all_v1"
    signal_contract_version: str = ""
    frame: int = 1
    interpreted_time: str = ""
    source_sha256: str = ""
    sha_status: str = "unknown"
    cache_status: str = "unknown"
    viewer_cache_state: str = "unknown"
    zarr_root: str = ""
    v2_cache_root: str = ""
    status: SourceStatus = SourceStatus.NO_PROJECT
    readiness: str = ""
    feature_version: str = FEATURE_VERSION
    reason_code: str = ""
    inventory_paths: list[str] = field(default_factory=list)
    role: str = ""
    can_activate: bool = False
    compatible_inactive: list[str] = field(default_factory=list)
    raw_frame_sha256: str = ""
    warnings: list[str] = field(default_factory=list)
    last_validation_identity: str = ""
    snapshot_generation: int = 0

    @property
    def ready(self) -> bool:
        return self.status == SourceStatus.READY and self.mat_path is not None


def _norm_path_key(path: Path | str | None) -> str:
    if path is None:
        return ""
    return os.path.normcase(os.path.normpath(str(path)))


def paths_equal(a: Path | str | None, b: Path | str | None) -> bool:
    """Compare paths without filesystem resolve/stat."""
    ka, kb = _norm_path_key(a), _norm_path_key(b)
    return bool(ka) and ka == kb


def _interpreted_time_for_frame(frame: int) -> str:
    try:
        from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute

        return format_hhmm(frame_to_minute(int(frame)))
    except Exception:
        f = max(1, int(frame))
        return f"{(f - 1) // 60:02d}:{(f - 1) % 60:02d}"


def _snap_matches_session(snap: ActiveSourceSnapshot, session: Any) -> bool:
    active = getattr(session, "active_mat", None)
    proj = getattr(session, "project", None)
    if bool(proj is not None) != bool(snap.project_open):
        return False
    if active is None:
        return snap.mat_path is None or not snap.is_active
    if snap.mat_path is None or not snap.is_active:
        return False
    if not paths_equal(snap.mat_path, active):
        return False
    pid = str(getattr(session, "profile_id", "") or "")
    if pid and snap.profile_id and snap.profile_id != pid:
        return False
    return True


def _with_volatile_ui_fields(snap: ActiveSourceSnapshot, session: Any) -> ActiveSourceSnapshot:
    frame = int(getattr(session, "current_frame", 1) or 1)
    if int(snap.frame) == frame and snap.interpreted_time:
        return snap
    return replace(snap, frame=frame, interpreted_time=_interpreted_time_for_frame(frame))


def invalidate_active_source_snapshot(session: Any) -> None:
    setattr(session, "_active_source_snap", None)


def resolve_active_source(session: Any, *, force_rebuild: bool = False) -> ActiveSourceSnapshot:
    """Return session ActiveSourceSnapshot. Warm UI must not force rebuild."""
    cached = getattr(session, "_active_source_snap", None)
    if not force_rebuild and isinstance(cached, ActiveSourceSnapshot):
        if _snap_matches_session(cached, session):
            out = _with_volatile_ui_fields(cached, session)
            if out is not cached:
                setattr(session, "_active_source_snap", out)
            return out
    return rebuild_active_source_snapshot(session)


def rebuild_active_source_snapshot(session: Any) -> ActiveSourceSnapshot:
    """Inspect source identity once and store on the session (may open/stat MAT)."""
    from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler, span_timer

    with span_timer("source.rebuild_snapshot"):
        snap = _build_snapshot_from_session(session)
        gen = int(getattr(session, "_snapshot_generation", 0) or 0) + 1
        setattr(session, "_snapshot_generation", gen)
        snap.snapshot_generation = gen
        setattr(session, "_active_source_snap", snap)
        prof = get_profiler()
        if prof is not None:
            prof.event(
                "active_source_snapshot_rebuilt",
                generation=gen,
                mat=snap.mat_filename,
                status=snap.status.value,
            )
        return snap


def _get_cached_classification(session: Any, path: Path | str):
    cache = getattr(session, "_source_classifications", None)
    if not isinstance(cache, dict):
        return None
    return cache.get(_norm_path_key(path))


def _remember_classification(session: Any, path: Path | str, cls: Any) -> None:
    cache = getattr(session, "_source_classifications", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(session, "_source_classifications", cache)
    cache[_norm_path_key(path)] = cls


def _classify_cached(session: Any, path: Path | str, profile: dict, *, try_frame: bool = False):
    from ionogram_morphology_lab.ui.source_roles import classify_mat_source
    from ionogram_morphology_lab.ui.source_service import bump_variable_inventory_scan

    cached = _get_cached_classification(session, path)
    if cached is not None and not try_frame:
        return cached
    bump_variable_inventory_scan()
    cls = classify_mat_source(path, profile, try_frame=try_frame)
    _remember_classification(session, path, cls)
    return cls


def _build_snapshot_from_session(session: Any) -> ActiveSourceSnapshot:
    snap = ActiveSourceSnapshot()
    proj = getattr(session, "project", None)
    snap.project_open = proj is not None
    snap.project_name = getattr(proj, "name", "") if proj else ""
    snap.project_id = str(getattr(proj, "project_id", "") or getattr(proj, "id", "") or "")
    snap.profile_id = str(
        getattr(session, "profile_id", "") or (getattr(proj, "profile_id", "") if proj else "")
    )
    profile = getattr(session, "profile", None) or {}
    snap.variable = str(profile.get("amplitude_variable_name") or "Amp_all")
    snap.profile_version = str(profile.get("profile_version") or profile.get("version") or "")
    h = int(profile.get("height_bins") or 256)
    w = int(profile.get("frequency_bins") or 400)
    snap.frame_count = int(profile.get("frames_per_file") or 1440)
    snap.frame = int(getattr(session, "current_frame", 1) or 1)
    snap.inventory_paths = [str(p) for p in (getattr(session, "selected_mats", None) or [])]
    if proj is not None and getattr(proj, "source_paths", None):
        for p in proj.source_paths:
            if p not in snap.inventory_paths:
                snap.inventory_paths.append(str(p))
    try:
        settings = getattr(session, "settings", None)
        if settings is not None and hasattr(settings, "cache_dir"):
            snap.v2_cache_root = str(settings.cache_dir())
    except Exception:
        pass

    active = getattr(session, "active_mat", None)
    active_key = _norm_path_key(active)

    try:
        for s in snap.inventory_paths:
            c = _classify_cached(session, s, profile, try_frame=False)
            if not c.can_activate:
                continue
            if active_key and _norm_path_key(c.path) == active_key:
                continue
            snap.compatible_inactive.append(str(c.path))
    except Exception:
        pass

    if active is not None:
        snap.mat_path = Path(active)
        snap.mat_filename = snap.mat_path.name
        snap.is_active = True
        snap.in_inventory = any(_norm_path_key(p) == active_key for p in snap.inventory_paths)
        try:
            st = snap.mat_path.stat()
            snap.source_size = int(st.st_size)
            snap.source_mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        except OSError:
            snap.status = SourceStatus.MISSING
            snap.reason_code = "mat_path_missing"
            snap.readiness = "missing"
            return snap
    elif snap.inventory_paths:
        snap.status = SourceStatus.INVENTORY_INACTIVE
        snap.reason_code = "mat_not_active"
        snap.readiness = "inventory_inactive"
        for s in snap.compatible_inactive or snap.inventory_paths:
            snap.mat_path = Path(s)
            snap.mat_filename = snap.mat_path.name
            snap.in_inventory = True
            snap.is_active = False
            break
        return snap

    if not snap.project_open:
        snap.status = SourceStatus.NO_PROJECT
        snap.reason_code = "project_not_open"
        snap.readiness = "no_project"
        return snap
    if snap.mat_path is None:
        snap.status = SourceStatus.NO_MAT
        snap.reason_code = "no_active_mat"
        snap.readiness = "no_mat"
        return snap
    if not snap.mat_path.is_file():
        snap.status = SourceStatus.MISSING
        snap.reason_code = "mat_path_missing"
        snap.readiness = "missing"
        return snap

    try:
        cls = _classify_cached(session, snap.mat_path, profile, try_frame=False)
        snap.role = cls.role.value
        snap.can_activate = cls.can_activate
        snap.shape = cls.shape or f"frame {h}×{w} (expected)"
        snap.dtype = cls.dtype or "pending"
        if cls.contract_id:
            snap.signal_contract_id = cls.contract_id
        if not cls.can_activate and cls.role != SourceRole.PRIMARY_IONOGRAM_SOURCE:
            snap.status = SourceStatus.INCOMPATIBLE
            snap.reason_code = cls.reason_code or "contract_incompatible"
            snap.readiness = "incompatible"
            return snap
    except Exception:
        pass

    store = getattr(session, "frame_store", None)
    try:
        store_ok = store is not None and paths_equal(getattr(store, "source_path", None), snap.mat_path)
        if store_ok:
            meta = getattr(store, "meta", None) or {}
            shape = meta.get("shape") or getattr(store, "shape", None)
            if shape is not None:
                snap.shape = "×".join(str(int(x)) for x in shape)
            snap.dtype = str(meta.get("dtype") or getattr(store, "dtype", "") or "")
            try:
                snap.frame_count = int(store.n_frames())
            except Exception:
                pass
            snap.cache_status = "ready"
            snap.viewer_cache_state = "ready"
            try:
                zroot = getattr(store, "zarr_root", None) or getattr(store, "cache_dir", None)
                snap.zarr_root = str(zroot) if zroot else ""
            except Exception:
                pass
            snap.status = SourceStatus.READY
            snap.readiness = "ready"
        else:
            if not snap.shape:
                snap.shape = f"frame {h}×{w} (expected)"
            snap.dtype = snap.dtype or "pending"
            snap.cache_status = "source_present"
            snap.viewer_cache_state = "source_present"
            snap.status = SourceStatus.READY
            snap.readiness = "source_present"
    except Exception:
        snap.status = SourceStatus.UNAVAILABLE
        snap.reason_code = "source_unavailable"
        snap.readiness = "unavailable"
        return snap

    snap.interpreted_time = _interpreted_time_for_frame(snap.frame)

    try:
        cached = ""
        if hasattr(session, "get_source_sha"):
            cached = session.get_source_sha(allow_compute=False) or ""
        if not cached and store is not None and getattr(store, "source_sha256", ""):
            cached = str(store.source_sha256)
        if cached:
            snap.source_sha256 = cached
            snap.sha_status = "ok"
            if hasattr(session, "remember_source_sha"):
                session.remember_source_sha(snap.mat_path, cached)
        else:
            snap.source_sha256 = ""
            snap.sha_status = "pending"
    except Exception:
        snap.sha_status = "unavailable"

    snap.last_validation_identity = (
        f"{snap.source_sha256[:16]}|{snap.source_size}|{snap.source_mtime_ns}|"
        f"{snap.profile_id}|{snap.signal_contract_id}|{snap.feature_version}"
    )
    snap.reason_code = ""
    return snap


def prerequisite_message(code: str, language: str) -> str:
    ru = language == "ru"
    messages = {
        "project_not_open": ("Проект не открыт." if ru else "No project is open."),
        "no_active_mat": (
            "В проекте не выбран активный MAT-файл."
            if ru
            else "No active MAT file is selected in the project."
        ),
        "mat_not_active": (
            "Файл присутствует в проекте, но не выбран как активный источник."
            if ru
            else "The file is present in the project but is not selected as the active source."
        ),
        "mat_path_missing": (
            "MAT-файл недоступен по сохранённому пути."
            if ru
            else "The MAT file is unavailable at the saved path."
        ),
        "variable_missing": (
            "В выбранном MAT-файле нет переменной Amp_all, необходимой для "
            "просмотра и диагностики ионограмм."
            if ru
            else "The selected MAT file does not contain variable Amp_all, which is "
            "required for ionogram viewing and diagnostics."
        ),
        "frame_not_loaded": ("Кадр ещё не загружен." if ru else "The frame is not loaded yet."),
        "profile_missing": (
            "Профиль прибора не выбран." if ru else "Instrument profile is not selected."
        ),
        "contract_incompatible": (
            "Контракт сигнала несовместим." if ru else "Signal contract is incompatible."
        ),
        "incompatible_source": localize_role_message("missing_amp_all", language),
        "generic_open_project_mat": (
            "Сначала откройте проект и выберите активный исходный MAT-файл."
            if ru
            else "Open a project and select an active source MAT file first."
        ),
        "identity_mismatch": (
            "Несовпадение кадра Viewer и диагностики. Старые маски очищены."
            if ru
            else "Viewer/Diagnostics frame identity mismatch. Stale masks cleared."
        ),
    }
    return messages.get(code, messages["generic_open_project_mat"])


def empty_state_copy(language: str) -> dict[str, str]:
    ru = language == "ru"
    if ru:
        return {
            "title": "Нет активного источника для диагностики признаков",
            "body": (
                "Для диагностики признаков требуется активный проект и исходный MAT-файл.\n"
                "1. Откройте или создайте проект.\n"
                "2. Импортируйте MAT-файл.\n"
                "3. Выберите его как активный источник.\n"
                "4. Вернитесь на эту страницу и запустите V2 в теневом режиме."
            ),
            "open_projects": "Открыть проекты",
            "open_import": "Открыть импорт данных",
            "choose_mat": "Выбрать другой MAT",
            "pick_from_project": localize_role_message("pick_from_project", "ru"),
            "refresh": "Обновить состояние",
        }
    return {
        "title": "No active source for Feature Diagnostics",
        "body": (
            "Feature Diagnostics requires an active project and source MAT file.\n"
            "1. Open or create a project.\n"
            "2. Import a MAT file.\n"
            "3. Select it as the active source.\n"
            "4. Return to this page and run V2 in shadow mode."
        ),
        "open_projects": "Open Projects",
        "open_import": "Open Import Data",
        "choose_mat": "Choose Another MAT",
        "pick_from_project": localize_role_message("pick_from_project", "en"),
        "refresh": "Refresh State",
    }


class ActiveSourceCard(QFrame):
    """Visible source card shared across Import / Viewer / Batch / Diagnostics / MATLAB."""

    action = Signal(str)

    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self._snap = ActiveSourceSnapshot()
        self._theme_pref = "system"
        self.setObjectName("ActiveSourceCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        self.title = QLabel()
        self.title.setStyleSheet("font-weight:700;")
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.no_active_hint = QLabel()
        self.no_active_hint.setWordWrap(True)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setVisible(False)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.toggle = QToolButton()
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self.details.setVisible)
        btn_row = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for key in (
            "choose_mat",
            "pick_from_project",
            "set_active",
            "detach",
            "open_import",
            "refresh",
            "open_folder",
            "remove_entry",
        ):
            b = QPushButton()
            b.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            self.buttons[key] = b
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        root.addWidget(self.title)
        root.addWidget(self.summary)
        root.addWidget(self.no_active_hint)
        root.addWidget(self.toggle)
        root.addWidget(self.details)
        root.addLayout(btn_row)
        self.apply_theme("system")
        self.retranslate()

    def apply_theme(self, preference: str | None = None) -> None:
        self._theme_pref = preference or self._theme_pref or "system"
        refresh_themed_widget(self, "ActiveSourceCard", self._theme_pref)

    def retranslate(self) -> None:
        ru = self.i18n.language == "ru"
        self.title.setText("Активный источник" if ru else "Active Source")
        self.toggle.setText("Технические сведения" if ru else "Technical details")
        labels = {
            "choose_mat": "Выбрать другой MAT" if ru else "Choose Another MAT",
            "pick_from_project": localize_role_message("pick_from_project", self.i18n.language),
            "set_active": "Активировать для анализа" if ru else "Activate for Analysis",
            "detach": "Отключить от анализа" if ru else "Deactivate for Analysis",
            "open_import": "Открыть страницу импорта" if ru else "Open Import Page",
            "refresh": "Обновить источник" if ru else "Refresh Source",
            "open_folder": "Открыть папку файла" if ru else "Open File Folder",
            "remove_entry": "Убрать из проекта" if ru else "Remove from Project",
        }
        for k, b in self.buttons.items():
            b.setText(labels[k])
            if k == "remove_entry":
                b.setToolTip(
                    "Запись исчезнет из проекта. Файл на компьютере удалён не будет."
                    if ru
                    else "The entry will disappear from the project. The file on disk will not be deleted."
                )
            if k == "detach":
                b.setToolTip(
                    "Отключает активный источник. Файл останется в проекте и на диске."
                    if ru
                    else "Deactivates the active source. The file remains in the project and on disk."
                )
        self.apply_snapshot(self._snap)

    def apply_snapshot(self, snap: ActiveSourceSnapshot) -> None:
        self._snap = snap
        ru = self.i18n.language == "ru"
        theme = resolve_theme_name(self._theme_pref)
        tokens = source_card_tokens(theme)
        status_map = {
            SourceStatus.NO_PROJECT: "нет проекта" if ru else "no project",
            SourceStatus.NO_MAT: "MAT не выбран" if ru else "no MAT selected",
            SourceStatus.INVENTORY_INACTIVE: "в проекте, не активен" if ru else "in project, not active",
            SourceStatus.MISSING: "файл недоступен" if ru else "file missing",
            SourceStatus.NOT_LOADED: "не загружен" if ru else "not loaded",
            SourceStatus.READY: "готов" if ru else "ready",
            SourceStatus.UNAVAILABLE: "недоступен" if ru else "unavailable",
            SourceStatus.INCOMPATIBLE: "несовместим" if ru else "incompatible",
        }
        status = status_map.get(snap.status, snap.status.value)
        if snap.is_active and snap.mat_filename:
            line1 = f"{snap.project_name or '—'} · {snap.mat_filename} · {status}"
        elif snap.status == SourceStatus.INVENTORY_INACTIVE:
            line1 = f"{snap.project_name or '—'} · {localize_role_message('no_active_selected', self.i18n.language)}"
        else:
            line1 = f"{snap.project_name or ('(нет проекта)' if ru else '(no project)')} · {status}"
        self.summary.setText(
            f"{line1}\n"
            f"{'Переменная' if ru else 'Variable'}: {snap.variable} | "
            f"{'Кадр' if ru else 'Frame'}: {snap.frame} | "
            f"{'Время' if ru else 'Time'}: {snap.interpreted_time or '—'} | "
            f"{'Профиль' if ru else 'Profile'}: {snap.profile_id or '—'}"
        )
        if snap.status == SourceStatus.INVENTORY_INACTIVE and snap.compatible_inactive:
            names = ", ".join(Path(p).name for p in snap.compatible_inactive[:5])
            self.no_active_hint.setText(
                (f"Совместимые файлы в проекте: {names}" if ru else f"Compatible files in project: {names}")
            )
            self.no_active_hint.setVisible(True)
            self.no_active_hint.setStyleSheet(f"color:{tokens['warn_fg']};")
        else:
            self.no_active_hint.clear()
            self.no_active_hint.setVisible(False)
        sha = (snap.source_sha256[:16] + "…") if snap.source_sha256 else "—"
        self.details.setText(
            f"path: {snap.mat_path or '—'}\n"
            f"shape: {snap.shape or '—'} | dtype: {snap.dtype or '—'}\n"
            f"signal_contract: {snap.signal_contract_id}\n"
            f"role: {snap.role or '—'}\n"
            f"source_sha256: {sha} ({snap.sha_status})\n"
            f"cache: {snap.cache_status} | feature_version: {snap.feature_version}"
        )
        has_compatible = bool(snap.compatible_inactive)
        self.buttons["set_active"].setVisible(
            (not snap.is_active) and has_compatible and snap.status == SourceStatus.INVENTORY_INACTIVE
        )
        self.buttons["pick_from_project"].setVisible(has_compatible and not snap.is_active)
        self.buttons["detach"].setEnabled(snap.is_active and snap.mat_path is not None)
        self.buttons["open_folder"].setEnabled(snap.mat_path is not None)
        self.buttons["remove_entry"].setEnabled(bool(snap.inventory_paths))


def open_file_folder(path: Path) -> None:
    folder = path if path.is_dir() else path.parent
    if not folder.exists():
        return
    try:
        os.startfile(str(folder))  # type: ignore[attr-defined]
    except Exception:
        pass


def confirm_imported_active(parent: QWidget, language: str, filename: str) -> None:
    ru = language == "ru"
    QMessageBox.information(
        parent,
        "IML",
        (
            f"Файл импортирован и выбран как активный источник.\n{filename}"
            if ru
            else f"File imported and selected as the active source.\n{filename}"
        ),
    )


def confirm_set_active(parent: QWidget, language: str, filename: str) -> None:
    prefix = localize_role_message("activated", language)
    QMessageBox.information(parent, "IML", f"{prefix}\n{filename}")


def confirm_switch_active(
    parent: QWidget, language: str, current_name: str, new_name: str
) -> bool:
    ru = language == "ru"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("IML")
    box.setText(
        "Сменить активный источник?\n\n"
        f"Текущий:\n{current_name}\n\n"
        f"Новый:\n{new_name}\n\n"
        "Текущие несохранённые диагностические данные будут очищены.\n"
        "Сохранённые результаты останутся в проекте."
        if ru
        else "Switch active source?\n\n"
        f"Current:\n{current_name}\n\n"
        f"New:\n{new_name}\n\n"
        "Unsaved diagnostic data will be cleared.\n"
        "Saved results will remain in the project."
    )
    switch_btn = box.addButton(
        "Сменить источник" if ru else "Switch Source",
        QMessageBox.ButtonRole.AcceptRole,
    )
    box.addButton("Отмена" if ru else "Cancel", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is switch_btn


def ask_set_active_for_inventory(parent: QWidget, language: str, filename: str) -> bool:
    ru = language == "ru"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("IML")
    box.setText(
        "Файл присутствует в проекте, но не выбран как активный источник."
        if ru
        else "The file is present in the project but is not selected as the active source."
    )
    box.setInformativeText(filename)
    set_btn = box.addButton(
        "Сделать активным" if ru else "Set as Active",
        QMessageBox.ButtonRole.AcceptRole,
    )
    box.addButton(QMessageBox.StandardButton.Cancel)
    box.exec()
    return box.clickedButton() is set_btn
