from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import savemat

from ionogram_morphology_lab.matlab_studio.api_bridge import API_FUNCTIONS, prepare_run_workspace
from ionogram_morphology_lab.matlab_studio.backends import detect_backends
from ionogram_morphology_lab.matlab_studio.library import ScriptLibrary
from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, save_manifest, validate_manifest
from ionogram_morphology_lab.matlab_studio.plugins import PluginRegistry
from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest, run_matlab_job
from ionogram_morphology_lab.utils.hashing import sha256_file


def test_backend_detection_returns_editor_backend():
    backends = detect_backends()
    assert backends
    assert any(backend.backend_id == "none" for backend in backends)


def test_unavailable_backend_never_reports_success(tmp_path):
    script = tmp_path / "demo.m"
    script.write_text("disp('hello');", encoding="utf-8")
    result = run_matlab_job(
        MatlabRunRequest(script_path=script, entrypoint="demo.m", backend="none")
    )
    assert result.status == "no_backend"


def test_manifest_validation():
    assert validate_manifest(ScriptManifest(plugin_id="demo", name_ru="Демо", name_en="Demo")) == []
    invalid = ScriptManifest(plugin_id="", name_ru="Демо", name_en="Demo", timeout=0)
    assert {"missing_plugin_id", "invalid_timeout"} <= set(validate_manifest(invalid))


def test_library_save_history_diff_and_restore(tmp_path):
    library = ScriptLibrary(tmp_path / "library")
    first = library.save_text("demo", "x = 1;\n", comment="initial")
    first_copy = tmp_path / "first.m"
    first_copy.write_text(Path(first.source_file).read_text(encoding="utf-8"), encoding="utf-8")
    second = library.save_text("demo", "x = 2;\n", comment="change")
    assert "x = 2" in Path(second.source_file).read_text(encoding="utf-8")
    assert "-x = 1;" in library.diff(first_copy, second.source_file)
    history = library.history("demo")
    assert history
    restored = library.restore_version("demo", first_copy)
    assert "x = 1" in Path(restored.source_file).read_text(encoding="utf-8")


def test_api_bridge_workspace_and_function_count(tmp_path):
    work = prepare_run_workspace(tmp_path, current_frame=np.ones((2, 2)), metadata={"source": "test"})
    assert (work / "iml_bridge_inputs.mat").exists()
    assert (work / "iml_metadata.json").exists()
    assert len(API_FUNCTIONS) == 15


def test_source_mat_hash_unchanged_after_run_attempt(tmp_path):
    source = tmp_path / "source.mat"
    savemat(source, {"Amp_all": np.ones((2, 2))})
    before = sha256_file(source)
    script = tmp_path / "demo.m"
    script.write_text("disp('hello');", encoding="utf-8")
    result = run_matlab_job(
        MatlabRunRequest(
            script_path=script,
            entrypoint="demo.m",
            backend="none",
            source_mat_paths=[str(source)],
        )
    )
    assert result.status == "no_backend"
    assert sha256_file(source) == before


def test_plugin_enable_disable_isolation(tmp_path):
    manifest_path = save_manifest(
        ScriptManifest(plugin_id="plug", name_ru="Плагин", name_en="Plugin"),
        tmp_path / "plug.iml-matlab.yaml",
    )
    registry = PluginRegistry(tmp_path / "plugins.json")
    registry.register(manifest_path)
    registry.disable("plug", "test")
    assert registry.enabled_plugins() == []
    registry.enable("plug")
    assert [plugin.plugin_id for plugin in registry.enabled_plugins()] == ["plug"]
