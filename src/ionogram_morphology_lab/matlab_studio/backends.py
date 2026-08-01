"""MATLAB / Octave / external-process backend detection."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, asdict, field
from typing import Any


@dataclass
class BackendInfo:
    backend_id: str  # matlab_engine | octave | external_matlab | none
    available: bool
    version: str = ""
    path: str = ""
    status: str = ""
    warnings: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_matlab_engine() -> BackendInfo:
    try:
        import matlab.engine  # type: ignore

        ver = getattr(matlab.engine, "__version__", "unknown")
        return BackendInfo(
            backend_id="matlab_engine",
            available=True,
            version=str(ver),
            status="detected",
            features=["workspace", "eval", "feval", "figures_via_export"],
        )
    except Exception as exc:  # noqa: BLE001
        return BackendInfo(
            backend_id="matlab_engine",
            available=False,
            status=f"unavailable:{exc}",
            warnings=["Install MATLAB Engine for Python to enable this backend."],
        )


def detect_octave(executable: str = "") -> BackendInfo:
    exe = executable or shutil.which("octave-cli") or shutil.which("octave") or ""
    if not exe:
        return BackendInfo(
            backend_id="octave",
            available=False,
            status="not_found",
            warnings=["Octave compatibility with MATLAB is incomplete."],
        )
    try:
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        ver = (proc.stdout or proc.stderr or "").splitlines()[0] if (proc.stdout or proc.stderr) else ""
        return BackendInfo(
            backend_id="octave",
            available=True,
            version=ver,
            path=exe,
            status="detected",
            warnings=["MATLAB and Octave compatibility is not complete."],
            features=["batch_script", "stdout"],
        )
    except Exception as exc:  # noqa: BLE001
        return BackendInfo(backend_id="octave", available=False, status=str(exc), path=exe)


def detect_external_matlab(executable: str = "") -> BackendInfo:
    exe = executable or shutil.which("matlab") or ""
    if not exe:
        return BackendInfo(backend_id="external_matlab", available=False, status="not_found")
    return BackendInfo(
        backend_id="external_matlab",
        available=True,
        path=exe,
        status="detected",
        features=["-batch", "temp_runner", "stdout"],
    )


def detect_backends(matlab_exe: str = "", octave_exe: str = "") -> list[BackendInfo]:
    return [
        detect_matlab_engine(),
        detect_external_matlab(matlab_exe),
        detect_octave(octave_exe),
        BackendInfo(
            backend_id="none",
            available=True,
            status="editor_only",
            features=["edit", "library", "manifest", "versioning"],
            warnings=["Execution disabled until a backend is available."],
        ),
    ]


def select_backend(
    preference: str = "auto",
    matlab_exe: str = "",
    octave_exe: str = "",
) -> BackendInfo:
    backends = detect_backends(matlab_exe, octave_exe)
    by_id = {b.backend_id: b for b in backends}
    if preference and preference != "auto":
        b = by_id.get(preference)
        if b and (b.available or preference == "none"):
            return b
        return BackendInfo(
            backend_id=preference,
            available=False,
            status="requested_unavailable",
            warnings=[f"Requested backend '{preference}' is not available."],
        )
    for key in ("matlab_engine", "external_matlab", "octave"):
        if by_id[key].available:
            return by_id[key]
    return by_id["none"]
