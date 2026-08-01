"""MATLAB Studio — integrated editor, backends, plugins, and isolated execution."""

from .backends import BackendInfo, detect_backends, select_backend
from .runner import MatlabRunRequest, MatlabRunResult, run_matlab_job
from .library import ScriptLibrary, ScriptRecord
from .manifest import ScriptManifest, load_manifest, save_manifest, validate_manifest
from .plugins import PluginRegistry

__all__ = [
    "BackendInfo",
    "detect_backends",
    "select_backend",
    "MatlabRunRequest",
    "MatlabRunResult",
    "run_matlab_job",
    "ScriptLibrary",
    "ScriptRecord",
    "ScriptManifest",
    "load_manifest",
    "save_manifest",
    "validate_manifest",
    "PluginRegistry",
]
