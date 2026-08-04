"""Persistent warm Feature Pipeline V2 child process (Phase 4B.2i).

Uses ``subprocess.Popen`` (not QProcess) so Cancel from a worker thread cannot
destroy Qt objects or crash the UI. One warm process per session; Cancel kills
only the current job's child and schedules a background restart.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.ui.cancel_crash_audit import ensure_audit, get_audit
from ionogram_morphology_lab.ui.frame_diagnostic_context import next_request_generation_id
from ionogram_morphology_lab.ui.packaged_exe_profiler import get_profiler

WORKER_FLAG = "--iml-v2-worker"


class V2ProcessState(str, Enum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    STOPPED = "stopped"


def is_worker_argv(argv: list[str] | None = None) -> bool:
    argv = list(sys.argv if argv is None else argv)
    return WORKER_FLAG in argv


def run_worker_loop() -> int:
    """Child-process entry: JSON lines on stdin → JSON lines on stdout."""
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    # Child never imports Qt / never exits parent
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as exc:  # noqa: BLE001
            _emit({"ok": False, "error": f"bad_json:{exc}"})
            continue
        cmd = req.get("cmd")
        if cmd == "ping":
            _emit({"ok": True, "cmd": "pong", "feature_version": FEATURE_VERSION, "pid": os.getpid()})
            continue
        if cmd == "shutdown":
            _emit({"ok": True, "cmd": "bye"})
            return 0
        if cmd == "run_frame":
            _emit(_handle_run_frame(req))
            continue
        _emit({"ok": False, "error": f"unknown_cmd:{cmd}"})
    return 0


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, default=str) + "\n")
    sys.stdout.flush()


def _handle_run_frame(req: dict[str, Any]) -> dict[str, Any]:
    """Compute + cache; return compact summary only (no full feature dump / masks)."""
    t0 = time.perf_counter()
    try:
        from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2

        frame_path = Path(req["frame_npy"])
        raw = np.load(frame_path)
        t_load = time.perf_counter()
        v2 = run_feature_pipeline_v2(
            raw,
            signal_contract_id=str(req.get("signal_contract_id") or ""),
            profile_id=str(req.get("profile_id") or ""),
            frame_index=int(req["frame_index"]),
            source_mat_sha256=str(req.get("source_sha") or ""),
        )
        t_pipe = time.perf_counter()
        cache_root = Path(req["cache_root"])
        cache = V2FeatureCache(cache_root)
        key = make_cache_key(
            source_mat_sha256=str(req.get("source_sha") or ""),
            frame_index=int(req["frame_index"]),
            profile_id=str(req.get("profile_id") or ""),
            signal_contract_id=str(req.get("signal_contract_id") or ""),
            profile=req.get("profile") or {},
        )
        timings = {
            "frame_load_s": t_load - t0,
            "pipeline_s": t_pipe - t_load,
            "process": True,
        }
        cache.save(key, v2, timings=timings)
        t_save = time.perf_counter()
        timings["serialize_s"] = t_save - t_pipe
        timings["total_s"] = t_save - t0
        ser = v2.to_serializable()
        # Compact payload — UI loads summary/layers from cache lazily
        compact = {
            "quality_status": ser.get("quality_status"),
            "branch_count": len(ser.get("centerlines") or []),
            "oversegmentation_suspected": bool(ser.get("oversegmentation_suspected")),
            "feature_version": FEATURE_VERSION,
            "source_mat_sha256": key.source_mat_sha256,
            "frame_index": key.frame_index,
        }
        return {
            "ok": True,
            "cmd": "run_frame",
            "request_id": req.get("request_id"),
            "frame_index": int(req["frame_index"]),
            "key": key.to_dict(),
            "summary": compact,
            "available_layers": sorted((v2.masks or {}).keys()),
            "timings": timings,
            "feature_version": FEATURE_VERSION,
            "cache_dir": str(cache._dir(key)),
            "result_from_cache": True,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "cmd": "run_frame",
            "request_id": req.get("request_id"),
            "error": str(exc),
            "elapsed_s": time.perf_counter() - t0,
        }


def _worker_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, WORKER_FLAG]
    return [sys.executable, "-m", "ionogram_morphology_lab.app.main", WORKER_FLAG]


class PersistentV2Worker:
    """One warm subprocess per application session — thread-safe via a single lock."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._state = V2ProcessState.NOT_STARTED
        self._startup_s = 0.0
        self._last_error = ""
        self._start_count = 0
        self._job_count = 0
        self._reuse_count = 0
        self._bytes_sent = 0
        self._bytes_received = 0
        self._stdout_buf = b""
        self._active_request_id: str | None = None
        self._restart_pending = False
        ensure_audit(enabled=True)

    @property
    def state(self) -> V2ProcessState:
        return self._state

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def startup_s(self) -> float:
        return self._startup_s

    @property
    def start_count(self) -> int:
        return self._start_count

    @property
    def job_count(self) -> int:
        return self._job_count

    @property
    def reuse_count(self) -> int:
        return self._reuse_count

    def metrics(self) -> dict[str, Any]:
        return {
            "start_count": self._start_count,
            "job_count": self._job_count,
            "reuse_count": self._reuse_count,
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
            "state": self._state.value,
            "startup_s": self._startup_s,
        }

    def _set_state(self, state: V2ProcessState, **kwargs: Any) -> None:
        self._state = state
        audit = get_audit()
        if audit is not None:
            audit.lifecycle("state", state=state.value, **kwargs)
        prof = get_profiler()
        if prof is not None:
            prof.event("v2_worker_state", state=state.value, **kwargs)

    def ensure_started(self, *, timeout_s: float = 30.0) -> bool:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                if self._state in (
                    V2ProcessState.READY,
                    V2ProcessState.RUNNING,
                    V2ProcessState.COMPLETED,
                    V2ProcessState.CANCELLED,
                ):
                    if self._state != V2ProcessState.RUNNING:
                        self._set_state(V2ProcessState.READY)
                    return True
            return self._start_locked(timeout_s=timeout_s)

    def start_async(self) -> None:
        """Non-blocking warm start after UI idle — never blocks navigation."""

        def _run() -> None:
            try:
                self.ensure_started()
            except Exception as exc:  # noqa: BLE001
                audit = get_audit()
                if audit is not None:
                    audit.exception("start_async", exc)

        threading.Thread(target=_run, name="iml-v2-warm-start", daemon=True).start()

    def _start_locked(self, *, timeout_s: float) -> bool:
        self._set_state(V2ProcessState.STARTING)
        self._close_proc_locked(graceful=False)
        t0 = time.perf_counter()
        try:
            env = os.environ.copy()
            env["IML_V2_WORKER"] = "1"
            # Prevent nested GUI / onboarding in child
            env["IML_DISABLE_ONBOARDING"] = "1"
            env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._proc = subprocess.Popen(
                _worker_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
                creationflags=creationflags,
            )
            self._start_count += 1
            self._stdout_buf = b""
            audit = get_audit()
            if audit is not None:
                audit.lifecycle(
                    "spawn",
                    child_pid=self._proc.pid,
                    start_count=self._start_count,
                    cmd=_worker_command(),
                )
            resp = self._transact_locked({"cmd": "ping"}, timeout_ms=int(timeout_s * 1000))
            self._startup_s = time.perf_counter() - t0
            if not resp or not resp.get("ok"):
                self._last_error = f"ping_failed:{resp}"
                self._set_state(V2ProcessState.FAILED, error=self._last_error)
                self._close_proc_locked(graceful=False)
                return False
            self._set_state(V2ProcessState.READY, child_pid=self._proc.pid, startup_s=self._startup_s)
            return True
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"start_exc:{exc}"
            self._set_state(V2ProcessState.FAILED, error=self._last_error)
            audit = get_audit()
            if audit is not None:
                audit.exception("worker_start", exc)
            self._close_proc_locked(graceful=False)
            return False

    def _close_proc_locked(self, *, graceful: bool) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None and graceful and proc.stdin:
                try:
                    proc.stdin.write((json.dumps({"cmd": "shutdown"}) + "\n").encode("utf-8"))
                    proc.stdin.flush()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=1.5)
                except Exception:
                    pass
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=2.0)
                except Exception:
                    pass
        except Exception as exc:  # noqa: BLE001
            audit = get_audit()
            if audit is not None:
                audit.exception("close_proc", exc)
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except Exception:
                    pass

    def request_cancel_job(self, request_id: str | None = None) -> None:
        """Invalidate current job; kill child if it is running that job. Never exits UI."""
        with self._lock:
            audit = get_audit()
            if audit is not None:
                audit.parent(
                    "cancel_requested",
                    request_id=request_id,
                    active=self._active_request_id,
                    state=self._state.value,
                )
            self._set_state(V2ProcessState.CANCELLING, request_id=request_id)
            # Only kill if this request owns the running job (or unknown)
            if request_id is None or self._active_request_id in (None, request_id):
                self._close_proc_locked(graceful=False)
                self._active_request_id = None
                self._set_state(V2ProcessState.CANCELLED, request_id=request_id)
                self._restart_pending = True
            # Schedule warm restart off the UI thread
        self._schedule_restart()

    def _schedule_restart(self) -> None:
        def _restart() -> None:
            with self._lock:
                if not self._restart_pending:
                    return
                self._restart_pending = False
                if self._proc is not None and self._proc.poll() is None:
                    return
                self._set_state(V2ProcessState.RESTARTING)
            try:
                self.ensure_started()
            except Exception as exc:  # noqa: BLE001
                audit = get_audit()
                if audit is not None:
                    audit.exception("restart", exc)

        threading.Thread(target=_restart, name="iml-v2-restart", daemon=True).start()

    def shutdown(self) -> None:
        """Controlled application shutdown only — not for Cancel or page switch."""
        with self._lock:
            self._restart_pending = False
            self._set_state(V2ProcessState.STOPPED)
            self._close_proc_locked(graceful=True)

    def _transact_locked(self, req: dict[str, Any], *, timeout_ms: int) -> dict[str, Any] | None:
        proc = self._proc
        if proc is None or proc.poll() is not None or proc.stdin is None or proc.stdout is None:
            self._last_error = "process_not_running"
            return None
        payload = (json.dumps(req, default=str) + "\n").encode("utf-8")
        try:
            proc.stdin.write(payload)
            proc.stdin.flush()
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"write_failed:{exc}"
            self._set_state(V2ProcessState.CRASHED, error=self._last_error)
            return None
        deadline = time.perf_counter() + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            if proc.poll() is not None:
                err = b""
                try:
                    err = proc.stderr.read() if proc.stderr else b""
                except Exception:
                    pass
                self._last_error = f"process_exited:{err[:400]!r}"
                self._set_state(V2ProcessState.CRASHED, error=self._last_error)
                audit = get_audit()
                if audit is not None:
                    audit.child("exited", code=proc.returncode, stderr=err[:800].decode("utf-8", "replace"))
                return None
            # Non-blocking-ish read with short select/poll
            try:
                import select

                if sys.platform == "win32":
                    # Windows: peek via short sleep + read if available
                    time.sleep(0.02)
                    # Use buffered read with timeout via threading? Keep simple: read1 if any
                    try:
                        # msvcrt doesn't work on pipes well; use wait with communicate pattern
                        pass
                    except Exception:
                        pass
                    # Fallback: blocking read with overall deadline checked in loop via thread
                    line = self._readline_with_timeout(proc, max(0.05, deadline - time.perf_counter()))
                    if line is None:
                        continue
                    try:
                        return json.loads(line.decode("utf-8"))
                    except Exception as exc:  # noqa: BLE001
                        self._last_error = f"bad_response:{exc}"
                        return None
                else:
                    r, _, _ = select.select([proc.stdout], [], [], 0.05)
                    if not r:
                        continue
                    chunk = proc.stdout.read1(65536) if hasattr(proc.stdout, "read1") else proc.stdout.read(65536)
                    if not chunk:
                        continue
                    self._stdout_buf += chunk
                    if b"\n" in self._stdout_buf:
                        line, _, rest = self._stdout_buf.partition(b"\n")
                        self._stdout_buf = rest
                        return json.loads(line.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                self._last_error = f"read_failed:{exc}"
                return None
        self._last_error = "read_timeout"
        return None

    def _readline_with_timeout(self, proc: subprocess.Popen[bytes], timeout_s: float) -> bytes | None:
        """Read one stdout line with timeout (Windows-safe)."""
        if proc.stdout is None:
            return None
        result: list[bytes | None] = [None]
        done = threading.Event()

        def _reader() -> None:
            try:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                result[0] = line if line else None
            except Exception:
                result[0] = None
            finally:
                done.set()

        th = threading.Thread(target=_reader, name="iml-v2-readline", daemon=True)
        th.start()
        if not done.wait(timeout=max(0.01, timeout_s)):
            return None
        return result[0]

    def run_frame(
        self,
        *,
        frame: np.ndarray,
        frame_index: int,
        source_sha: str,
        profile_id: str,
        signal_contract_id: str,
        profile: dict[str, Any],
        cache_root: Path | str,
        request_id: str,
        timeout_ms: int = 180000,
    ) -> dict[str, Any]:
        tmp = Path(tempfile.mkdtemp(prefix="iml_v2_frame_"))
        npy = tmp / "frame.npy"
        try:
            np.save(npy, np.asarray(frame))
            with self._lock:
                already_warm = (
                    self._proc is not None
                    and self._proc.poll() is None
                    and self._start_count > 0
                )
                if not self.ensure_started():
                    return {"ok": False, "error": self._last_error or "worker_not_started"}
                if already_warm:
                    self._reuse_count += 1
                self._active_request_id = request_id
                self._set_state(V2ProcessState.RUNNING, request_id=request_id, frame_index=frame_index)
                t0 = time.perf_counter()
                req = {
                    "cmd": "run_frame",
                    "request_id": request_id,
                    "frame_npy": str(npy),
                    "frame_index": int(frame_index),
                    "source_sha": source_sha,
                    "profile_id": profile_id,
                    "signal_contract_id": signal_contract_id,
                    "profile": profile,
                    "cache_root": str(cache_root),
                }
                req_bytes = len(json.dumps(req).encode("utf-8"))
                try:
                    req_bytes += int(npy.stat().st_size)
                except Exception:
                    pass
                self._bytes_sent += req_bytes
                prof = get_profiler()
                if prof is not None:
                    prof.event(
                        "v2_worker_request_received",
                        request_id=request_id,
                        frame_index=frame_index,
                        bytes_sent=req_bytes,
                        reuse_count=self._reuse_count,
                    )
                t_compute = time.perf_counter()
                resp = self._transact_locked(req, timeout_ms=timeout_ms)
                compute_s = time.perf_counter() - t_compute
                ipc_s = time.perf_counter() - t0
                self._job_count += 1
                # If cancelled while waiting, treat as cancelled
                if self._state == V2ProcessState.CANCELLING or self._state == V2ProcessState.CANCELLED:
                    return {"ok": False, "error": "cancelled", "cancelled": True, "ipc_s": ipc_s}
                self._active_request_id = None
                if resp is None:
                    crashed = self._state == V2ProcessState.CRASHED
                    self._schedule_restart()
                    return {
                        "ok": False,
                        "error": self._last_error or "no_response",
                        "ipc_s": ipc_s,
                        "crashed": crashed,
                    }
                try:
                    self._bytes_received += len(json.dumps(resp).encode("utf-8"))
                except Exception:
                    pass
                if prof is not None:
                    prof.span(
                        "v2_worker_compute",
                        compute_s,
                        request_id=request_id,
                        frame_index=frame_index,
                        reuse_count=self._reuse_count,
                        bytes_sent=req_bytes,
                        bytes_received=self._bytes_received,
                    )
                    prof.event(
                        "v2_worker_result_send",
                        request_id=request_id,
                        ok=bool(resp.get("ok")),
                        reuse_count=self._reuse_count,
                    )
                self._set_state(V2ProcessState.COMPLETED if resp.get("ok") else V2ProcessState.FAILED)
                self._set_state(V2ProcessState.READY)
                resp["ipc_s"] = ipc_s
                resp["compute_s"] = compute_s
                resp["process_startup_s"] = self._startup_s
                resp["worker_start_count"] = self._start_count
                resp["worker_job_count"] = self._job_count
                resp["worker_reuse_count"] = self._reuse_count
                resp["bytes_sent"] = self._bytes_sent
                resp["bytes_received"] = self._bytes_received
                return resp
        finally:
            try:
                npy.unlink(missing_ok=True)
                tmp.rmdir()
            except Exception:
                pass


# Back-compat alias
V2ProcessPool = PersistentV2Worker

_POOL: PersistentV2Worker | None = None
_POOL_LOCK = threading.Lock()


def shared_pool() -> PersistentV2Worker:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = PersistentV2Worker()
        return _POOL


def worker_start_count() -> int:
    return shared_pool().start_count


class V2ProcessJobThread(QThread):
    """UI-side job runner: cache check locally; compute via persistent child process."""

    progress = Signal(dict)
    finished_ok = Signal(dict)
    failed = Signal(dict)
    cancelled = Signal(dict)

    def __init__(
        self,
        *,
        frames: list[int],
        profile: dict[str, Any],
        profile_id: str,
        signal_contract_id: str,
        cache: V2FeatureCache,
        raw_by_frame: dict[int, np.ndarray],
        source_sha: str,
        force_recompute: bool = False,
        request_generation_id: str | None = None,
        parent=None,
    ):
        # IMPORTANT: do not parent to a page widget — page nav must not destroy this thread.
        super().__init__(None)
        self.frames = [int(f) for f in frames]
        self.profile = profile
        self.profile_id = profile_id
        self.signal_contract_id = signal_contract_id
        self.cache = cache
        self.raw_by_frame = raw_by_frame
        self.source_sha = source_sha
        self.force_recompute = force_recompute
        self.request_generation_id = request_generation_id or next_request_generation_id()
        self._cancel = False
        self.job_state = "idle"
        self.terminal_state: str | None = None
        self._pool = shared_pool()
        self._signals_armed = True

    def request_cancel(self) -> None:
        self._cancel = True
        self.job_state = "cancelling"
        try:
            self._pool.request_cancel_job(self.request_generation_id)
        except Exception as exc:  # noqa: BLE001
            audit = get_audit()
            if audit is not None:
                audit.exception("job_request_cancel", exc)

    def disarm(self) -> None:
        """Ignore further signal emissions (UI discarded this generation)."""
        self._signals_armed = False
        self._cancel = True

    def _emit_safe(self, signal: Signal, payload: dict) -> None:
        if not self._signals_armed:
            return
        try:
            signal.emit(payload)
        except Exception as exc:  # noqa: BLE001
            audit = get_audit()
            if audit is not None:
                audit.exception("signal_emit", exc)

    def run(self) -> None:  # noqa: N802
        gen = self.request_generation_id
        t_all = time.perf_counter()
        results: list[dict[str, Any]] = []
        cache_hits = 0
        recomputed = 0
        failures = 0
        n = len(self.frames)
        audit = get_audit()
        if audit is not None:
            audit.parent("job_start", gen=gen, frames=self.frames, start_count=self._pool.start_count)
        try:
            for i, frame_index in enumerate(self.frames):
                if self._cancel:
                    self.terminal_state = "cancelled"
                    self._emit_safe(
                        self.cancelled,
                        {
                            "request_generation_id": gen,
                            "job_state": "cancelled",
                            "cache_hits": cache_hits,
                            "recomputed": recomputed,
                            "failures": failures,
                        },
                    )
                    return
                key = make_cache_key(
                    source_mat_sha256=self.source_sha,
                    frame_index=frame_index,
                    profile_id=self.profile_id,
                    signal_contract_id=self.signal_contract_id,
                    profile=self.profile,
                )
                pct = int(100 * i / max(1, n))
                self._emit_safe(
                    self.progress,
                    {
                        "request_generation_id": gen,
                        "job_state": "checking_cache",
                        "stage": "checking_cache",
                        "frame_index": frame_index,
                        "frame_i": i + 1,
                        "frame_n": n,
                        "percent": pct,
                    },
                )
                # Cache hit: never touch the worker process
                if not self.force_recompute:
                    hit = self.cache.load_summary(key)
                    if hit is not None:
                        cache_hits += 1
                        results.append(
                            {
                                "frame_index": frame_index,
                                "status": "cached",
                                "key": key.to_dict(),
                                "result": hit["result"],
                                "masks": {},
                                "available_layers": hit.get("available_layers") or [],
                                "timings": {
                                    "total_s": 0.0,
                                    "from_cache": True,
                                    "summary_only": True,
                                    "worker_used": False,
                                },
                                "request_generation_id": gen,
                                "source_sha256": self.source_sha,
                            }
                        )
                        continue

                raw = self.raw_by_frame.get(frame_index)
                if raw is None:
                    failures += 1
                    results.append(
                        {
                            "frame_index": frame_index,
                            "status": "failed",
                            "error": "raw_frame_missing_in_ui",
                            "request_generation_id": gen,
                            "source_sha256": self.source_sha,
                        }
                    )
                    continue

                self._emit_safe(
                    self.progress,
                    {
                        "request_generation_id": gen,
                        "job_state": "computing",
                        "stage": "computing",
                        "frame_index": frame_index,
                        "frame_i": i + 1,
                        "frame_n": n,
                        "percent": pct,
                    },
                )
                if self._cancel:
                    break
                starts_before = self._pool.start_count
                resp = self._pool.run_frame(
                    frame=raw,
                    frame_index=frame_index,
                    source_sha=self.source_sha,
                    profile_id=self.profile_id,
                    signal_contract_id=self.signal_contract_id,
                    profile=self.profile,
                    cache_root=getattr(self.cache, "cache_root", self.cache.root.parent),
                    request_id=gen,
                )
                if self._cancel or resp.get("cancelled"):
                    break
                if not resp.get("ok"):
                    err = str(resp.get("error") or "process_failed")
                    # Soft fallback only when worker never started
                    if "worker_not_started" in err or "failed_to_start" in err or "ping_failed" in err:
                        from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2

                        if self._cancel:
                            break
                        t2 = time.perf_counter()
                        v2 = run_feature_pipeline_v2(
                            raw,
                            signal_contract_id=self.signal_contract_id,
                            profile_id=self.profile_id,
                            frame_index=frame_index,
                            source_mat_sha256=self.source_sha,
                        )
                        timings = {"pipeline_s": time.perf_counter() - t2, "fallback_inprocess": True}
                        self.cache.save(key, v2, timings=timings)
                        recomputed += 1
                        results.append(
                            {
                                "frame_index": frame_index,
                                "status": "recomputed",
                                "key": key.to_dict(),
                                "result": v2.to_serializable(),
                                "masks": {},
                                "available_layers": sorted((v2.masks or {}).keys()),
                                "timings": timings,
                                "request_generation_id": gen,
                                "source_sha256": self.source_sha,
                                "process_fallback": True,
                            }
                        )
                        continue
                    failures += 1
                    results.append(
                        {
                            "frame_index": frame_index,
                            "status": "failed",
                            "error": err,
                            "request_generation_id": gen,
                            "source_sha256": self.source_sha,
                        }
                    )
                    continue
                # Load summary from cache (child saved it) — no full IPC result dump
                summary_hit = self.cache.load_summary(key)
                recomputed += 1
                results.append(
                    {
                        "frame_index": frame_index,
                        "status": "recomputed",
                        "key": resp.get("key") or key.to_dict(),
                        "result": (summary_hit or {}).get("result") or resp.get("summary") or {},
                        "masks": {},
                        "available_layers": resp.get("available_layers")
                        or (summary_hit or {}).get("available_layers")
                        or [],
                        "timings": {
                            **(resp.get("timings") or {}),
                            "ipc_s": resp.get("ipc_s"),
                            "process_startup_s": resp.get("process_startup_s"),
                            "worker_start_count": resp.get("worker_start_count"),
                            "starts_before": starts_before,
                            "starts_after": self._pool.start_count,
                        },
                        "request_generation_id": gen,
                        "source_sha256": self.source_sha,
                        "process": True,
                    }
                )

            if self._cancel:
                self.terminal_state = "cancelled"
                self._emit_safe(
                    self.cancelled,
                    {
                        "request_generation_id": gen,
                        "job_state": "cancelled",
                        "cache_hits": cache_hits,
                        "recomputed": recomputed,
                        "failures": failures,
                    },
                )
                return

            self.terminal_state = "completed"
            self._emit_safe(
                self.finished_ok,
                {
                    "request_generation_id": gen,
                    "job_state": "completed",
                    "source_sha": self.source_sha,
                    "feature_version": FEATURE_VERSION,
                    "results": results,
                    "cache_hits": cache_hits,
                    "recomputed": recomputed,
                    "failures": failures,
                    "elapsed_s": time.perf_counter() - t_all,
                    "process_isolated": True,
                    "worker_start_count": self._pool.start_count,
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.terminal_state = "failed"
            if audit is not None:
                audit.exception("job_run", exc)
            self._emit_safe(
                self.failed,
                {
                    "request_generation_id": gen,
                    "job_state": "failed",
                    "error": str(exc),
                },
            )
