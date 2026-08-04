"""Central MATLAB/Octave job manager — owns workers for their full lifetime."""

from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QProcess, QThread, QTimer, Signal, QProcessEnvironment

from ionogram_morphology_lab.matlab_studio.backends import select_backend
from ionogram_morphology_lab.matlab_studio.runner import (
    MatlabRunRequest,
    MatlabRunResult,
    _load_outputs,
    _make_runner_script,
    _write_inputs,
    run_matlab_job,
)
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir

_LOG = logging.getLogger(__name__)

VALID_STATUSES = (
    "queued",
    "starting",
    "running",
    "cancelling",
    "completed",
    "failed",
    "timed_out",
    "cancelled",
)

# Ordered shutdown wait before escalate terminate → kill (ms)
DEFAULT_SHUTDOWN_WAIT_MS = 5000
DEFAULT_TERMINATE_WAIT_MS = 3000


@dataclass
class MatlabJob:
    job_id: str
    script_id: str
    source_path: str
    sha256: str
    trust_status: str
    backend: str
    process_state: str = "idle"
    start_time: str = ""
    timeout_s: int = 120
    stdout: str = ""
    stderr: str = ""
    output_directory: str = ""
    requested_inputs: str = ""
    cancellation_requested: bool = False
    status: str = "queued"
    error_message: str = ""
    error_identifier: str = ""
    stack: str = ""
    elapsed_s: float = 0.0
    exit_code: int | None = None
    source_mats_unchanged: bool = True
    source_mat_paths: list[str] = field(default_factory=list)
    source_hashes: dict[str, str] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    active_frame: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_active(self) -> bool:
        return self.status in ("queued", "starting", "running", "cancelling")


class _EngineWorker(QThread):
    """Owned engine worker — parent must be MatlabJobManager."""

    finished_payload = Signal(str, dict)
    failed_payload = Signal(str, str)

    def __init__(self, job_id: str, req: MatlabRunRequest, cancel_flag: Callable[[], bool], parent: QObject):
        super().__init__(parent)
        self.job_id = job_id
        self.req = req
        self._cancel_flag = cancel_flag

    def run(self) -> None:
        try:
            res = run_matlab_job(self.req, cancel_flag=self._cancel_flag)
            self.finished_payload.emit(self.job_id, res.to_dict())
        except Exception as exc:  # noqa: BLE001
            self.failed_payload.emit(self.job_id, f"{exc}\n{traceback.format_exc()}")


class MatlabJobManager(QObject):
    """Singleton-style manager: one instance per MainWindow."""

    job_updated = Signal(object)  # MatlabJob
    job_finished = Signal(object)  # MatlabJob

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._jobs: dict[str, MatlabJob] = {}
        self._processes: dict[str, QProcess] = {}
        self._engine_workers: dict[str, _EngineWorker] = {}
        self._timeout_timers: dict[str, QTimer] = {}
        self._started_at: dict[str, datetime] = {}

    def jobs(self) -> list[MatlabJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> MatlabJob | None:
        return self._jobs.get(job_id)

    def active_jobs(self) -> list[MatlabJob]:
        return [j for j in self._jobs.values() if j.is_active]

    def has_active_jobs(self) -> bool:
        return bool(self.active_jobs())

    def submit(
        self,
        req: MatlabRunRequest,
        *,
        script_id: str = "",
        trust_status: str = "unconfirmed",
        requested_inputs: str = "",
        active_frame: int | None = None,
    ) -> MatlabJob:
        if self.has_active_jobs():
            # Do not overwrite a running worker reference.
            raise RuntimeError("matlab_job_already_running")

        backend = select_backend(req.backend, req.matlab_executable, req.octave_executable)
        script_path = Path(req.script_path).resolve()
        work = Path(req.work_dir).resolve() if req.work_dir else ensure_dir(
            Path.cwd() / "workspaces" / "_matlab_runs" / (script_id or "job")
        )
        ensure_dir(work)
        source_hashes = {p: sha256_file(p) for p in req.source_mat_paths if Path(p).is_file()}
        job_id = uuid.uuid4().hex
        job = MatlabJob(
            job_id=job_id,
            script_id=script_id or script_path.stem,
            source_path=str(script_path),
            sha256=sha256_file(script_path) if script_path.is_file() else "",
            trust_status=trust_status,
            backend=backend.backend_id,
            status="queued",
            timeout_s=int(req.timeout_s),
            output_directory=str(work),
            requested_inputs=requested_inputs,
            source_mat_paths=list(req.source_mat_paths),
            source_hashes=source_hashes,
            active_frame=active_frame,
        )
        self._jobs[job_id] = job
        self._emit(job)

        if backend.backend_id == "none" or not backend.available:
            job.status = "failed"
            job.error_message = (
                backend.status
                if backend.backend_id != "none"
                else (
                    "No MATLAB/Octave execution backend is available. "
                    "Editing and packaging still work; execution is disabled."
                )
            )
            job.process_state = "idle"
            job.result = MatlabRunResult(
                status="no_backend",
                backend=backend.backend_id,
                elapsed_s=0.0,
                error_message=job.error_message,
                work_dir=str(work),
            ).to_dict()
            self._emit(job)
            self.job_finished.emit(job)
            return job

        job.status = "starting"
        job.start_time = datetime.now(timezone.utc).isoformat()
        self._started_at[job_id] = datetime.now(timezone.utc)
        self._emit(job)

        # Prepare workspace (same artifacts as run_matlab_job).
        _write_inputs(work, req.inputs, req.parameters)
        runner = _make_runner_script(work, script_path, req.entrypoint)

        if backend.backend_id == "matlab_engine":
            self._start_engine(job, req)
        elif backend.backend_id in ("external_matlab", "octave"):
            exe = backend.path or (
                req.matlab_executable if backend.backend_id == "external_matlab" else req.octave_executable
            )
            self._start_process(job, exe, work, matlab=(backend.backend_id == "external_matlab"))
        else:
            job.status = "failed"
            job.error_message = f"unsupported backend: {backend.backend_id}"
            self._emit(job)
            self.job_finished.emit(job)
        return job

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job or not job.is_active:
            return
        job.cancellation_requested = True
        job.status = "cancelling"
        job.process_state = "cancelling"
        self._emit(job)
        proc = self._processes.get(job_id)
        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
            proc.terminate()
            QTimer.singleShot(DEFAULT_TERMINATE_WAIT_MS, lambda: self._kill_if_needed(job_id))
        worker = self._engine_workers.get(job_id)
        if worker is not None and worker.isRunning():
            # Engine path polls cancel_flag inside run_matlab_job when supported;
            # request interruption as best-effort.
            worker.requestInterruption()

    def shutdown_all(self, wait_ms: int = DEFAULT_SHUTDOWN_WAIT_MS) -> None:
        """Ordered shutdown for application close."""
        for job in list(self.active_jobs()):
            self.cancel(job.job_id)
        deadline = datetime.now(timezone.utc).timestamp() + (wait_ms / 1000.0)
        # Pump wait via process waitForFinished where possible
        for job_id, proc in list(self._processes.items()):
            remaining = max(0, int((deadline - datetime.now(timezone.utc).timestamp()) * 1000))
            if proc.state() != QProcess.ProcessState.NotRunning:
                proc.waitForFinished(remaining)
                if proc.state() != QProcess.ProcessState.NotRunning:
                    proc.kill()
                    proc.waitForFinished(1000)
        for job_id, worker in list(self._engine_workers.items()):
            remaining = max(0, int((deadline - datetime.now(timezone.utc).timestamp()) * 1000))
            if worker.isRunning():
                worker.wait(remaining)
        self._release_finished_workers()

    def _start_process(self, job: MatlabJob, exe: str, work: Path, *, matlab: bool) -> None:
        if not exe or not Path(exe).exists():
            # Allow bare command names on PATH
            if not exe:
                job.status = "failed"
                job.error_message = "MATLAB/Octave executable path is empty."
                self._emit(job)
                self.job_finished.emit(job)
                return
        work_abs = Path(work).resolve()
        work_posix = work_abs.as_posix().replace("'", "''")
        if matlab:
            args = ["-batch", f"cd('{work_posix}'); iml_batch_entry();"]
        else:
            args = ["--quiet", "--eval", f"cd('{work_posix}'); iml_batch_entry();"]

        proc = QProcess(self)  # parent = manager
        proc.setProgram(exe)
        proc.setArguments(args)
        proc.setWorkingDirectory(str(work_abs))
        env = QProcessEnvironment.systemEnvironment()
        # Restricted: do not expand arbitrary shell; keep minimal inherited env.
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)

        job_id = job.job_id
        self._processes[job_id] = proc

        proc.readyReadStandardOutput.connect(lambda jid=job_id: self._read_stdout(jid))
        proc.readyReadStandardError.connect(lambda jid=job_id: self._read_stderr(jid))
        proc.started.connect(lambda jid=job_id: self._on_process_started(jid))
        proc.finished.connect(
            lambda code, status, jid=job_id: self._on_process_finished(jid, int(code), status)
        )
        proc.errorOccurred.connect(lambda err, jid=job_id: self._on_process_error(jid, err))

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda jid=job_id: self._on_timeout(jid))
        self._timeout_timers[job_id] = timer
        timer.start(max(1, job.timeout_s) * 1000)

        job.status = "running"
        job.process_state = "starting"
        self._emit(job)
        proc.start()
        # QProcess.start(program, args) already set via setProgram/setArguments

    def _start_engine(self, job: MatlabJob, req: MatlabRunRequest) -> None:
        job_id = job.job_id

        def cancel_flag() -> bool:
            j = self._jobs.get(job_id)
            return bool(j and j.cancellation_requested)

        worker = _EngineWorker(job_id, req, cancel_flag, parent=self)
        self._engine_workers[job_id] = worker
        worker.finished_payload.connect(self._on_engine_finished)
        worker.failed_payload.connect(self._on_engine_failed)
        job.status = "running"
        job.process_state = "running"
        self._emit(job)
        worker.start()

    def _on_process_started(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.process_state = "running"
        self._emit(job)

    def _read_stdout(self, job_id: str) -> None:
        proc = self._processes.get(job_id)
        job = self._jobs.get(job_id)
        if not proc or not job:
            return
        chunk = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        job.stdout += chunk
        self._emit(job)

    def _read_stderr(self, job_id: str) -> None:
        proc = self._processes.get(job_id)
        job = self._jobs.get(job_id)
        if not proc or not job:
            return
        chunk = bytes(proc.readAllStandardError()).decode("utf-8", errors="replace")
        job.stderr += chunk
        self._emit(job)

    def _on_timeout(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        proc = self._processes.get(job_id)
        if not job or not job.is_active:
            return
        job.status = "cancelling"
        job.error_message = f"Execution exceeded timeout ({job.timeout_s}s)"
        self._emit(job)
        if proc and proc.state() != QProcess.ProcessState.NotRunning:
            proc.terminate()
            QTimer.singleShot(DEFAULT_TERMINATE_WAIT_MS, lambda: self._finalize_timeout_kill(job_id))
        else:
            job.status = "timed_out"
            self._finalize_job(job_id)

    def _finalize_timeout_kill(self, job_id: str) -> None:
        proc = self._processes.get(job_id)
        job = self._jobs.get(job_id)
        if proc and proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()
        if job and job.is_active:
            job.status = "timed_out"
            self._finalize_job(job_id)

    def _kill_if_needed(self, job_id: str) -> None:
        proc = self._processes.get(job_id)
        job = self._jobs.get(job_id)
        if proc and proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()
        if job and job.status == "cancelling" and job.is_active:
            # finished handler will set cancelled; if still stuck, finalize
            pass

    def _on_process_error(self, job_id: str, err: QProcess.ProcessError) -> None:
        job = self._jobs.get(job_id)
        if not job or not job.is_active:
            return
        # FailedToStart is definitive; others may still get finished()
        if err == QProcess.ProcessError.FailedToStart:
            job.status = "failed"
            job.error_message = f"Failed to start process: {err}"
            self._finalize_job(job_id)

    def _on_process_finished(self, job_id: str, code: int, _status: QProcess.ExitStatus) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        timer = self._timeout_timers.pop(job_id, None)
        if timer:
            timer.stop()
            timer.deleteLater()
        # Drain remaining output
        self._read_stdout(job_id)
        self._read_stderr(job_id)
        job.exit_code = code
        if job.cancellation_requested and job.status in ("cancelling", "running", "starting"):
            job.status = "cancelled"
        elif job.status == "cancelling" and "timeout" in (job.error_message or "").lower():
            job.status = "timed_out"
        elif job.status not in ("timed_out", "cancelled"):
            work = Path(job.output_directory)
            if (work / "iml_error.txt").exists():
                txt = (work / "iml_error.txt").read_text(encoding="utf-8", errors="replace")
                job.error_message = txt
                lines = txt.splitlines()
                job.error_identifier = lines[0] if lines else ""
                job.status = "failed"
            elif code != 0:
                job.status = "failed"
                if not job.error_message:
                    job.error_message = (job.stderr or f"Process exit code {code}")[:2000]
            else:
                job.status = "completed"
        self._finalize_job(job_id)

    def _on_engine_finished(self, job_id: str, payload: dict) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        status = payload.get("status", "error")
        mapping = {
            "ok": "completed",
            "error": "failed",
            "timeout": "timed_out",
            "cancelled": "cancelled",
            "no_backend": "failed",
        }
        if job.cancellation_requested and status != "ok":
            job.status = "cancelled"
        else:
            job.status = mapping.get(status, "failed")
        job.stdout = payload.get("stdout", "")
        job.stderr = payload.get("stderr", "")
        job.error_message = payload.get("error_message", "")
        job.error_identifier = payload.get("error_identifier", "")
        job.stack = payload.get("stack", "")
        job.elapsed_s = float(payload.get("elapsed_s") or 0)
        job.source_mats_unchanged = bool(payload.get("source_mats_unchanged", True))
        job.result = payload
        job.process_state = "idle"
        self._emit(job)
        self.job_finished.emit(job)
        self._release_worker(job_id)

    def _on_engine_failed(self, job_id: str, message: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.status = "failed"
        job.error_message = message
        job.stack = message
        job.process_state = "idle"
        self._finalize_job(job_id)

    def _finalize_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        started = self._started_at.get(job_id)
        if started:
            job.elapsed_s = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
        work = Path(job.output_directory) if job.output_directory else None
        outs: dict[str, Any] = {}
        files: list[str] = []
        diary = ""
        if work and work.is_dir():
            outs, files = _load_outputs(work)
            diary_path = work / "diary.txt"
            if diary_path.exists():
                diary = diary_path.read_text(encoding="utf-8", errors="replace")
        unchanged = all(
            Path(p).is_file() and sha256_file(p) == h for p, h in job.source_hashes.items()
        )
        job.source_mats_unchanged = unchanged
        status_map = {
            "completed": "ok",
            "failed": "error",
            "timed_out": "timeout",
            "cancelled": "cancelled",
        }
        job.result = MatlabRunResult(
            status=status_map.get(job.status, "error"),
            backend=job.backend,
            elapsed_s=job.elapsed_s,
            stdout=job.stdout,
            stderr=job.stderr,
            diary=diary,
            error_message=job.error_message,
            error_identifier=job.error_identifier,
            stack=job.stack,
            outputs=outs,
            output_files=files,
            work_dir=job.output_directory,
            provenance={
                "script": job.source_path,
                "job_id": job.job_id,
                "script_id": job.script_id,
                "trust_status": job.trust_status,
            },
            source_mats_unchanged=unchanged,
        ).to_dict()
        job.process_state = "idle"
        self._emit(job)
        self.job_finished.emit(job)
        self._release_worker(job_id)

    def _release_worker(self, job_id: str) -> None:
        timer = self._timeout_timers.pop(job_id, None)
        if timer:
            timer.stop()
            timer.deleteLater()
        proc = self._processes.pop(job_id, None)
        if proc is not None:
            proc.deleteLater()
        worker = self._engine_workers.pop(job_id, None)
        if worker is not None:
            if worker.isRunning():
                _LOG.error("engine worker still running at release; waiting: %s", job_id)
                worker.wait(DEFAULT_SHUTDOWN_WAIT_MS)
            worker.deleteLater()
        self._started_at.pop(job_id, None)

    def _release_finished_workers(self) -> None:
        for job_id in list(self._processes.keys()) + list(self._engine_workers.keys()):
            job = self._jobs.get(job_id)
            if job and not job.is_active:
                self._release_worker(job_id)

    def _emit(self, job: MatlabJob) -> None:
        self.job_updated.emit(job)
