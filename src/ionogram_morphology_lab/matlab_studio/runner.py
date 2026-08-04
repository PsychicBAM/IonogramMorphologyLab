"""Isolated MATLAB / Octave job execution — failures must not crash the GUI."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import traceback
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import savemat, loadmat

from ionogram_morphology_lab.matlab_studio.backends import BackendInfo, select_backend
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir


@dataclass
class MatlabRunRequest:
    script_path: Path | str
    entrypoint: str
    backend: str = "auto"
    matlab_executable: str = ""
    octave_executable: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)
    timeout_s: int = 120
    work_dir: Path | str | None = None
    allow_external_write: bool = False
    source_mat_paths: list[str] = field(default_factory=list)


@dataclass
class MatlabRunResult:
    status: str  # ok | error | timeout | cancelled | no_backend
    backend: str
    elapsed_s: float
    stdout: str = ""
    stderr: str = ""
    diary: str = ""
    error_message: str = ""
    error_identifier: str = ""
    stack: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    output_files: list[str] = field(default_factory=list)
    work_dir: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    source_mats_unchanged: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # numpy-safe
        safe_out = {}
        for k, v in self.outputs.items():
            if isinstance(v, np.ndarray):
                safe_out[k] = {"type": "ndarray", "shape": list(v.shape), "dtype": str(v.dtype)}
            else:
                try:
                    json.dumps(v)
                    safe_out[k] = v
                except TypeError:
                    safe_out[k] = str(v)
        d["outputs"] = safe_out
        return d


def _write_inputs(work: Path, inputs: dict[str, Any], parameters: dict[str, Any]) -> Path:
    payload = {"parameters": parameters}
    for k, v in inputs.items():
        if isinstance(v, np.ndarray):
            savemat(str(work / f"in_{k}.mat"), {k: v}, do_compression=True)
            payload[k] = f"in_{k}.mat"
        else:
            payload[k] = v
    meta = work / "iml_inputs.json"
    meta.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    # Merge into existing bridge MAT (preserve axes/metadata written by prepare_run_workspace)
    bridge = work / "iml_bridge_inputs.mat"
    mat_vars: dict[str, Any] = {}
    if bridge.exists():
        try:
            existing = loadmat(str(bridge), simplify_cells=True)
            for k, v in existing.items():
                if not k.startswith("__"):
                    mat_vars[k] = v
        except Exception:  # noqa: BLE001
            pass
    for k, v in inputs.items():
        if isinstance(v, np.ndarray):
            mat_vars[k] = v
            # canonical names used by helpers
            if k in {"iml_current_frame", "current_frame", "frame"}:
                mat_vars["iml_current_frame"] = v
    mat_vars["iml_parameters"] = parameters
    savemat(str(bridge), mat_vars, do_compression=True)
    return meta


def _make_runner_script(work: Path, script_path: Path, entrypoint: str) -> Path:
    # Copy script into work dir
    dest = work / script_path.name
    shutil.copy2(script_path, dest)
    # Function files cannot be executed with run(); call the function instead.
    src_text = script_path.read_text(encoding="utf-8", errors="replace")
    stem = script_path.stem
    is_function = bool(
        re.search(rf"^\s*function\b", src_text, flags=re.MULTILINE)
    )
    call_name = Path(entrypoint).stem if entrypoint else stem
    if is_function:
        invoke = (
            f"  if exist('{call_name}','file')==2 || exist('{call_name}','builtin')\n"
            f"    iml_result = {call_name}();\n"
            f"  else\n"
            f"    error('iml:missingFunction','Function {call_name} not found');\n"
            f"  end"
        )
    else:
        # Script entry: prefer explicit entrypoint path inside work dir
        ep = dest.name if not entrypoint else Path(entrypoint).name
        invoke = f"  run('{ep}');"
    # Function entry avoids MATLAB R2019a `run()` path (known invalid-character failures on some hosts).
    runner = work / "iml_batch_entry.m"
    runner.write_text(
        "\n".join(
            [
                "function iml_batch_entry()",
                "try",
                f"  addpath('{Path(work).resolve().as_posix()}');",
                f"  addpath('{Path(script_path).resolve().parent.as_posix()}');",
                "  if exist('iml_bridge_inputs.mat','file')",
                "    load('iml_bridge_inputs.mat');",
                "  end",
                invoke,
                "  wh = whos;",
                "  if ~isempty(wh)",
                "    save('iml_bridge_outputs.mat', wh.name, '-v7');",
                "  end",
                "catch ME",
                "  fid = fopen('iml_error.txt','w');",
                "  fprintf(fid, '%s\\n%s\\n', ME.identifier, getReport(ME,'extended'));",
                "  fclose(fid);",
                "  rethrow(ME);",
                "end",
                "end",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return runner


def _load_outputs(work: Path) -> tuple[dict[str, Any], list[str]]:
    outs: dict[str, Any] = {}
    files = [str(p) for p in work.glob("*") if p.is_file()]
    mat_out = work / "iml_bridge_outputs.mat"
    if mat_out.exists():
        try:
            data = loadmat(str(mat_out), simplify_cells=True)
            for k, v in data.items():
                if k.startswith("__"):
                    continue
                outs[k] = v
        except Exception:  # noqa: BLE001
            pass
    # common saved artifacts
    for p in work.glob("out_*.*"):
        files.append(str(p))
    return outs, files


def run_matlab_job(req: MatlabRunRequest, cancel_flag: callable | None = None) -> MatlabRunResult:
    t0 = datetime.now(timezone.utc)
    backend = select_backend(req.backend, req.matlab_executable, req.octave_executable)
    if backend.backend_id == "none" or not backend.available:
        if backend.backend_id == "none":
            return MatlabRunResult(
                status="no_backend",
                backend="none",
                elapsed_s=0.0,
                error_message=(
                    "No MATLAB/Octave execution backend is available. "
                    "Editing and packaging still work; execution is disabled."
                ),
            )
        return MatlabRunResult(
            status="no_backend",
            backend=backend.backend_id,
            elapsed_s=0.0,
            error_message=backend.status,
        )

    source_hashes = {p: sha256_file(p) for p in req.source_mat_paths if Path(p).is_file()}
    work = Path(req.work_dir).resolve() if req.work_dir else Path(tempfile.mkdtemp(prefix="iml_matlab_"))
    ensure_dir(work)
    script_path = Path(req.script_path).resolve()
    _write_inputs(work, req.inputs, req.parameters)
    runner = _make_runner_script(work, script_path, req.entrypoint)

    stdout = stderr = diary = ""
    status = "ok"
    err_msg = err_id = stack = ""
    try:
        if cancel_flag and cancel_flag():
            return MatlabRunResult(status="cancelled", backend=backend.backend_id, elapsed_s=0.0, work_dir=str(work))

        if backend.backend_id == "matlab_engine":
            stdout, stderr, status, err_msg, err_id, stack = _run_engine(work, runner, req.timeout_s)
        elif backend.backend_id == "external_matlab":
            stdout, stderr, status, err_msg = _run_external(
                backend.path or req.matlab_executable,
                work,
                runner,
                req.timeout_s,
                matlab=True,
                cancel_flag=cancel_flag,
            )
        elif backend.backend_id == "octave":
            stdout, stderr, status, err_msg = _run_external(
                backend.path or req.octave_executable,
                work,
                runner,
                req.timeout_s,
                matlab=False,
                cancel_flag=cancel_flag,
            )
        else:
            status = "no_backend"
            err_msg = "unsupported backend"

        if status != "cancelled" and (work / "iml_error.txt").exists():
            txt = (work / "iml_error.txt").read_text(encoding="utf-8", errors="replace")
            lines = txt.splitlines()
            err_id = lines[0] if lines else ""
            err_msg = txt
            status = "error"
        diary_path = work / "diary.txt"
        if diary_path.exists():
            diary = diary_path.read_text(encoding="utf-8", errors="replace")
        if cancel_flag and cancel_flag() and status == "ok":
            status = "cancelled"
            err_msg = "cancelled by user"
    except subprocess.TimeoutExpired:
        status = "timeout"
        err_msg = f"Execution exceeded timeout ({req.timeout_s}s)"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        err_msg = str(exc)
        stack = traceback.format_exc()

    outs, files = _load_outputs(work)
    unchanged = all(
        Path(p).is_file() and sha256_file(p) == h for p, h in source_hashes.items()
    )
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    return MatlabRunResult(
        status=status,
        backend=backend.backend_id,
        elapsed_s=round(elapsed, 3),
        stdout=stdout,
        stderr=stderr,
        diary=diary,
        error_message=err_msg,
        error_identifier=err_id,
        stack=stack,
        outputs=outs,
        output_files=files,
        work_dir=str(work),
        provenance={
            "script": str(script_path),
            "entrypoint": req.entrypoint,
            "parameters": req.parameters,
            "created_at": t0.isoformat(),
            "backend_version": backend.version,
            "allow_external_write": req.allow_external_write,
        },
        source_mats_unchanged=unchanged,
    )


def _run_engine(work: Path, runner: Path, timeout_s: int) -> tuple[str, str, str, str, str, str]:
    import matlab.engine  # type: ignore

    eng = matlab.engine.start_matlab()
    try:
        eng.cd(str(work), nargout=0)
        eng.diary(str(work / "diary.txt"), nargout=0)
        # matlab engine has limited timeout; rely on Future if available
        eng.run(str(runner.name), nargout=0)
        eng.diary("off", nargout=0)
        return "", "", "ok", "", "", ""
    except Exception as exc:  # noqa: BLE001
        return "", str(exc), "error", str(exc), getattr(exc, "identifier", ""), traceback.format_exc()
    finally:
        try:
            eng.quit()
        except Exception:  # noqa: BLE001
            pass


def _run_external(
    exe: str,
    work: Path,
    runner: Path,
    timeout_s: int,
    matlab: bool,
    cancel_flag: callable | None = None,
) -> tuple[str, str, str, str]:
    """Run external MATLAB/Octave with argument list (no shell). Cancel-aware."""
    work_abs = Path(work).resolve()
    # Use absolute POSIX path; avoid relative cd when cwd is already the work dir.
    work_posix = work_abs.as_posix().replace("'", "''")
    if matlab:
        cmd = [exe, "-batch", f"cd('{work_posix}'); iml_batch_entry();"]
    else:
        cmd = [exe, "--quiet", "--eval", f"cd('{work_posix}'); iml_batch_entry();"]
    # Prefer Popen so cancel_flag can terminate mid-run (GUI path uses QProcess instead).
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(work_abs),
        shell=False,
    )
    import time

    t0 = time.monotonic()
    while True:
        if cancel_flag and cancel_flag():
            proc.terminate()
            try:
                out, err = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate(timeout=2)
            return out or "", err or "", "cancelled", "cancelled by user"
        rc = proc.poll()
        if rc is not None:
            out, err = proc.communicate()
            status = "ok" if rc == 0 else "error"
            return out or "", err or "", status, (err or "")[:2000]
        if time.monotonic() - t0 > max(1, int(timeout_s)):
            proc.terminate()
            try:
                out, err = proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate(timeout=2)
            raise subprocess.TimeoutExpired(cmd, timeout_s, output=out, stderr=err)
        time.sleep(0.05)
