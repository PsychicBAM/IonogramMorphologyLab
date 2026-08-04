"""Cancel/crash audit logging for packaged-EXE V2 worker (Phase 4B.2i)."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

_LOCK = threading.Lock()
_ACTIVE: "CancelCrashAudit | None" = None


def get_audit() -> "CancelCrashAudit | None":
    return _ACTIVE


def ensure_audit(*, enabled: bool | None = None) -> "CancelCrashAudit":
    global _ACTIVE
    if _ACTIVE is not None:
        return _ACTIVE
    env = os.environ.get("IML_CANCEL_CRASH_AUDIT", "").strip().lower()
    on = enabled if enabled is not None else env in ("1", "true", "yes", "on")
    # Always create a directory-backed audit in packaged EXE; lightweight otherwise.
    if not on and not getattr(sys, "frozen", False):
        # Still create for tests when explicitly requested via ensure_audit(enabled=True)
        pass
    root = ensure_dir(app_root() / "workspaces" / "_cancel_crash_audit")
    _ACTIVE = CancelCrashAudit(root)
    return _ACTIVE


class CancelCrashAudit:
    def __init__(self, root: Path):
        self.root = ensure_dir(root)
        self.session_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self._session = {
            "session_id": self.session_id,
            "pid": os.getpid(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "started_at": time.time(),
        }
        (self.root / "session.json").write_text(
            json.dumps(self._session, indent=2), encoding="utf-8"
        )
        for name in (
            "parent.log",
            "child.log",
            "qt_messages.log",
            "exceptions.log",
            "process_lifecycle.jsonl",
        ):
            (self.root / name).write_text("", encoding="utf-8")

    def _append(self, name: str, text: str) -> None:
        with _LOCK:
            with (self.root / name).open("a", encoding="utf-8") as fh:
                fh.write(text)
                if not text.endswith("\n"):
                    fh.write("\n")

    def parent(self, msg: str, **kwargs: Any) -> None:
        row = {"t": time.time(), "msg": msg, **kwargs}
        self._append("parent.log", json.dumps(row, default=str))

    def child(self, msg: str, **kwargs: Any) -> None:
        row = {"t": time.time(), "msg": msg, **kwargs}
        self._append("child.log", json.dumps(row, default=str))

    def lifecycle(self, event: str, **kwargs: Any) -> None:
        row = {
            "t": time.time(),
            "event": event,
            "tid": threading.get_ident(),
            "pid": os.getpid(),
            **kwargs,
        }
        self._append("process_lifecycle.jsonl", json.dumps(row, default=str))

    def exception(self, where: str, exc: BaseException | None = None) -> None:
        tb = ""
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        else:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
        self._append("exceptions.log", f"=== {where} t={time.time()} ===\n{tb}\n")

    def qt_message(self, mode: str, message: str) -> None:
        self._append("qt_messages.log", f"{time.time()} {mode}: {message}")


def install_exception_hooks() -> None:
    """Install process-wide hooks that never exit the app on worker errors."""
    audit = ensure_audit(enabled=True)
    try:
        import faulthandler

        fault_path = audit.root / "faulthandler.log"
        fh = open(fault_path, "a", encoding="utf-8")  # noqa: SIM115 — kept for process life
        faulthandler.enable(file=fh, all_threads=True)
    except Exception as exc:  # noqa: BLE001
        audit.exception("faulthandler_enable", exc)

    prev = sys.excepthook

    def _hook(exc_type, exc, tb) -> None:
        try:
            audit.exception("sys.excepthook", exc if isinstance(exc, BaseException) else None)
            audit.parent("uncaught_exception", type=getattr(exc_type, "__name__", str(exc_type)))
        except Exception:
            pass
        # Never SystemExit the GUI for worker-related noise
        if exc_type is SystemExit:
            prev(exc_type, exc, tb)
            return
        prev(exc_type, exc, tb)

    sys.excepthook = _hook

    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler

        def _qt_handler(mode, _ctx, message) -> None:
            try:
                name = {
                    QtMsgType.QtDebugMsg: "debug",
                    QtMsgType.QtInfoMsg: "info",
                    QtMsgType.QtWarningMsg: "warning",
                    QtMsgType.QtCriticalMsg: "critical",
                    QtMsgType.QtFatalMsg: "fatal",
                }.get(mode, str(mode))
                audit.qt_message(name, str(message))
            except Exception:
                pass

        qInstallMessageHandler(_qt_handler)
    except Exception as exc:  # noqa: BLE001
        audit.exception("qt_message_handler", exc)
