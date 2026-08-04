"""Opt-in packaged-EXE session profiler (Phase 4B.2j).

Enable with ``IML_PACKAGED_PERF=1`` or Settings ``performance.packaged_exe_profiler``.
"""

from __future__ import annotations

import builtins
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ionogram_morphology_lab.utils.paths import ensure_dir

_LOCK = threading.Lock()
_ACTIVE: "PackagedExeProfiler | None" = None
_SPAN_STACK: threading.local = threading.local()
_ORIG_OPEN = builtins.open
_IO_INSTALLED = False


def profiler_enabled(settings=None) -> bool:
    env = os.environ.get("IML_PACKAGED_PERF", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if settings is not None:
        try:
            return bool(settings.get("performance", "packaged_exe_profiler", False))
        except Exception:
            return False
    return False


def get_profiler() -> "PackagedExeProfiler | None":
    return _ACTIVE


def _span_stack() -> list[str]:
    stack = getattr(_SPAN_STACK, "stack", None)
    if stack is None:
        stack = []
        _SPAN_STACK.stack = stack
    return stack


def start_profiler(out_dir: Path | str, *, identity: dict[str, Any] | None = None) -> "PackagedExeProfiler":
    global _ACTIVE
    prof = PackagedExeProfiler(Path(out_dir), identity=identity or {})
    with _LOCK:
        _ACTIVE = prof
    prof.install_file_io_hooks()
    return prof


def stop_profiler() -> None:
    global _ACTIVE
    with _LOCK:
        prof = _ACTIVE
        _ACTIVE = None
    if prof is not None:
        prof.uninstall_file_io_hooks()
        prof.close()


def _classify_path(path: str) -> str:
    s = path.replace("/", "\\").lower()
    if "pytest-of-" in s or "\\pytest-" in s or "test_cache_" in s:
        return "test"
    if "ionogrammorphologylab\\cache" in s or "workspaces\\_cache" in s or "v2_features" in s:
        return "cache"
    if s.endswith(".mat"):
        return "source_mat"
    if s.endswith(".npy") or s.endswith(".zarr") or "data.zarr" in s:
        return "array"
    return "other"


@dataclass
class PackagedExeProfiler:
    out_dir: Path
    identity: dict[str, Any] = field(default_factory=dict)
    _t0: float = field(default_factory=time.perf_counter)
    _hb_last: float = field(default_factory=time.perf_counter)
    _hb_delays: list[float] = field(default_factory=list)
    _counters: dict[str, int] = field(default_factory=dict)
    _closed: bool = False
    file_io_tracer_active: bool = False
    intercepted_operation_count: int = 0
    uninstrumented_backend_warning: str = ""

    def __post_init__(self) -> None:
        self.out_dir = ensure_dir(self.out_dir)
        manifest = {
            "started_at": time.time(),
            "identity": self.identity,
            "pid": os.getpid(),
            "file_io_tracer_active": False,
        }
        (self.out_dir / "session_manifest.json").write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8"
        )
        for name in ("timeline.jsonl", "file_io.jsonl", "ui_heartbeat.jsonl"):
            (self.out_dir / name).write_text("", encoding="utf-8")

    def install_file_io_hooks(self) -> None:
        global _IO_INSTALLED
        if _IO_INSTALLED:
            self.file_io_tracer_active = True
            return
        prof = self
        import os as _os

        self._orig_stat = getattr(_os, "stat", None)
        self._orig_scandir = getattr(_os, "scandir", None)

        def _open_hook(file, mode="r", *args, **kwargs):
            t0 = time.perf_counter()
            fh = _ORIG_OPEN(file, mode, *args, **kwargs)
            path = str(file)
            # Avoid recursion when writing profiler logs
            try:
                if str(prof.out_dir) in path.replace("/", "\\"):
                    return fh
            except Exception:
                pass
            # Open ≠ read: record file_size separately; actual_bytes_read unknown at open.
            file_size = 0
            try:
                if hasattr(fh, "seek"):
                    pos = fh.tell()
                    fh.seek(0, 2)
                    file_size = int(fh.tell())
                    fh.seek(pos)
            except Exception:
                file_size = 0
            prof.intercepted_operation_count += 1
            prof.file_io(
                "open",
                path,
                bytes_read=0,
                actual_bytes_read=0,
                file_size=file_size,
                bytes_unknown=True,
                mode=str(mode),
                duration_s=time.perf_counter() - t0,
                category=_classify_path(path),
                caller="builtins.open",
            )
            return fh

        def _stat_hook(path, *args, **kwargs):
            t0 = time.perf_counter()
            result = self._orig_stat(path, *args, **kwargs)  # type: ignore[misc]
            try:
                p = str(path)
                if str(prof.out_dir) not in p.replace("/", "\\"):
                    prof.intercepted_operation_count += 1
                    prof.file_io(
                        "stat",
                        p,
                        duration_s=time.perf_counter() - t0,
                        category=_classify_path(p),
                        caller="os.stat",
                    )
            except Exception:
                pass
            return result

        def _scandir_hook(path="."):
            t0 = time.perf_counter()
            result = self._orig_scandir(path)  # type: ignore[misc]
            try:
                p = str(path)
                if str(prof.out_dir) not in p.replace("/", "\\"):
                    prof.intercepted_operation_count += 1
                    prof.file_io(
                        "scandir",
                        p,
                        duration_s=time.perf_counter() - t0,
                        category=_classify_path(p),
                        caller="os.scandir",
                    )
            except Exception:
                pass
            return result

        builtins.open = _open_hook  # type: ignore[assignment]
        if self._orig_stat is not None:
            _os.stat = _stat_hook  # type: ignore[assignment]
        if self._orig_scandir is not None:
            _os.scandir = _scandir_hook  # type: ignore[assignment]
        self.uninstrumented_backend_warning = (
            "numpy/zarr native I/O may bypass Python open(); prefer Path.open / builtins.open paths"
        )
        _IO_INSTALLED = True
        self.file_io_tracer_active = True
        # Refresh manifest flag
        try:
            with _ORIG_OPEN(self.out_dir / "session_manifest.json", encoding="utf-8") as fh:
                man = json.loads(fh.read())
            man["file_io_tracer_active"] = True
            man["uninstrumented_backend_warning"] = self.uninstrumented_backend_warning
            with _ORIG_OPEN(self.out_dir / "session_manifest.json", "w", encoding="utf-8") as fh:
                fh.write(json.dumps(man, indent=2, default=str))
        except Exception:
            pass

    def uninstall_file_io_hooks(self) -> None:
        global _IO_INSTALLED
        import os as _os

        if _IO_INSTALLED:
            builtins.open = _ORIG_OPEN  # type: ignore[assignment]
            if getattr(self, "_orig_stat", None) is not None:
                _os.stat = self._orig_stat  # type: ignore[assignment]
            if getattr(self, "_orig_scandir", None) is not None:
                _os.scandir = self._orig_scandir  # type: ignore[assignment]
            _IO_INSTALLED = False
        self.file_io_tracer_active = False

    def _append(self, name: str, row: dict[str, Any]) -> None:
        if self._closed:
            return
        parents = list(_span_stack())
        row = {
            "t_wall": time.time(),
            "t_rel_s": time.perf_counter() - self._t0,
            "tid": threading.get_ident(),
            "pid": os.getpid(),
            "parent": parents[-1] if parents else None,
            "parents": parents,
            **row,
        }
        path = self.out_dir / name
        # Use original open to avoid recursive file_io logging
        with _LOCK:
            with _ORIG_OPEN(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")

    def event(self, name: str, **kwargs: Any) -> None:
        self._append("timeline.jsonl", {"event": name, **kwargs})

    def span(self, name: str, duration_s: float, **kwargs: Any) -> None:
        self._append(
            "timeline.jsonl",
            {"event": name, "duration_s": float(duration_s), **kwargs},
        )

    def file_io(self, op: str, path: str | Path, *, bytes_read: int = 0, **kwargs: Any) -> None:
        row = {
            "op": op,
            "path": str(path),
            # Legacy field kept; for open() this is 0 (not file size).
            "bytes_read": int(bytes_read),
            "actual_bytes_read": int(kwargs.pop("actual_bytes_read", bytes_read) or 0),
            "file_size": int(kwargs.pop("file_size", 0) or 0),
            "bytes_unknown": bool(kwargs.pop("bytes_unknown", bytes_read == 0 and op == "open")),
            **kwargs,
        }
        self._append("file_io.jsonl", row)
        self.bump("file_io_ops")
        if op == "open":
            self.bump("open_count")
        elif op in ("read", "readinto"):
            self.bump("read_call_count")

    def bump(self, key: str, n: int = 1) -> None:
        with _LOCK:
            self._counters[key] = int(self._counters.get(key, 0)) + int(n)

    def counters(self) -> dict[str, int]:
        with _LOCK:
            out = dict(self._counters)
        out["intercepted_operation_count"] = self.intercepted_operation_count
        out["file_io_tracer_active"] = 1 if self.file_io_tracer_active else 0
        return out

    def heartbeat_tick(self) -> None:
        now = time.perf_counter()
        delay = now - self._hb_last
        self._hb_last = now
        self._hb_delays.append(delay)
        if len(self._hb_delays) > 5000:
            self._hb_delays = self._hb_delays[-2500:]
        self._append("ui_heartbeat.jsonl", {"delay_s": delay})

    def timed(self, name: str, **kwargs: Any):
        return span_timer(name, **kwargs)

    def write_summary(self) -> Path:
        delays = sorted(self._hb_delays) or [0.0]
        p95 = delays[int(0.95 * (len(delays) - 1))]
        spans: list[dict[str, Any]] = []
        timeline = self.out_dir / "timeline.jsonl"
        if timeline.is_file():
            for line in timeline.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if "duration_s" in row:
                    spans.append(row)
        spans_sorted = sorted(spans, key=lambda r: float(r.get("duration_s") or 0), reverse=True)
        over_100ms = [s for s in spans_sorted if float(s.get("duration_s") or 0) >= 0.1]
        fio_lines = 0
        fio_path = self.out_dir / "file_io.jsonl"
        if fio_path.is_file():
            fio_lines = sum(1 for line in fio_path.read_text(encoding="utf-8").splitlines() if line.strip())
        summary = {
            "identity": self.identity,
            "counters": self.counters(),
            "profiler_health": {
                "file_io_tracer_active": self.file_io_tracer_active,
                "intercepted_operation_count": self.intercepted_operation_count,
                "file_io_records": fio_lines,
                "uninstrumented_backend_warning": self.uninstrumented_backend_warning,
                "file_io_status": (
                    "FAIL"
                    if fio_lines == 0 and self.file_io_tracer_active
                    else ("OK" if fio_lines > 0 else "INACTIVE")
                ),
            },
            "ui_heartbeat": {
                "samples": len(delays),
                "p50_s": delays[len(delays) // 2],
                "p95_s": p95,
                "max_s": delays[-1],
            },
            "top20_spans": spans_sorted[:20],
            "spans_over_100ms": over_100ms,
            "elapsed_s": time.perf_counter() - self._t0,
        }
        path = self.out_dir / "summary.md"
        lines = [
            "# Packaged EXE performance session",
            "",
            f"- elapsed_s: {summary['elapsed_s']:.3f}",
            f"- heartbeat p50/p95/max: "
            f"{summary['ui_heartbeat']['p50_s']:.4f} / "
            f"{summary['ui_heartbeat']['p95_s']:.4f} / "
            f"{summary['ui_heartbeat']['max_s']:.4f}",
            f"- file_io_status: {summary['profiler_health']['file_io_status']} "
            f"(records={fio_lines}, intercepted={self.intercepted_operation_count})",
            "",
            "## Top 20 longest operations",
        ]
        for s in summary["top20_spans"]:
            parent = s.get("parent")
            lines.append(
                f"- {s.get('event')}: {float(s.get('duration_s') or 0):.4f}s"
                + (f" (parent={parent})" if parent else "")
            )
        lines.append("")
        lines.append("## Operations ≥ 100 ms")
        for s in over_100ms:
            lines.append(f"- {s.get('event')}: {float(s.get('duration_s') or 0):.4f}s")
        lines.append("")
        lines.append("## Counters")
        for k, v in sorted(summary["counters"].items()):
            lines.append(f"- {k}: {v}")
        lines.extend(["", "## Identity", "```", json.dumps(self.identity, indent=2), "```", ""])
        with _ORIG_OPEN(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        with _ORIG_OPEN(self.out_dir / "summary.json", "w", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, indent=2, default=str))
        return path

    def close(self) -> None:
        if self._closed:
            return
        self.write_summary()
        self._closed = True


class span_timer:
    """Nested profiler span (pushes parent stack)."""

    def __init__(self, name: str, **kwargs: Any):
        self.name = name
        self.kwargs = kwargs
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        _span_stack().append(self.name)
        return self

    def __exit__(self, *_exc):
        stack = _span_stack()
        if stack and stack[-1] == self.name:
            stack.pop()
        elif self.name in stack:
            stack.remove(self.name)
        prof = get_profiler()
        if prof is not None:
            prof.span(self.name, time.perf_counter() - self._t0, **self.kwargs)


@contextmanager
def profiled(name: str, **kwargs: Any):
    with span_timer(name, **kwargs):
        yield
