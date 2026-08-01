#!/usr/bin/env python3
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, save_manifest, validate_manifest
    from ionogram_morphology_lab.matlab_studio.plugins import PluginRegistry
    with tempfile.TemporaryDirectory() as td:
        manifest = Path(td) / "plugin.iml-matlab.yaml"
        item = ScriptManifest(plugin_id="validator_plugin", name_en="Validator", name_ru="Валидатор")
        save_manifest(item, manifest)
        if validate_manifest(item): print("FAIL manifest validation"); return 1
        registry = PluginRegistry(Path(td) / "plugins.json")
        registry.register(manifest)
        registry.disable("validator_plugin", "test")
        if registry.enabled_plugins(): print("FAIL disable"); return 1
        registry.enable("validator_plugin")
        if len(registry.enabled_plugins()) != 1: print("FAIL enable"); return 1
        if not PluginRegistry(Path(td) / "plugins.json").get_manifest("validator_plugin"): print("FAIL load"); return 1
    print("validate_matlab_plugin_system OK"); return 0
if __name__ == "__main__": sys.exit(main())
