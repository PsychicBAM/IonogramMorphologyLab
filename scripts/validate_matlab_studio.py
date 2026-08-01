#!/usr/bin/env python3
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    from ionogram_morphology_lab.matlab_studio.api_bridge import API_FUNCTIONS
    from ionogram_morphology_lab.matlab_studio.backends import detect_backends
    from ionogram_morphology_lab.matlab_studio.library import ScriptLibrary
    from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, validate_manifest
    from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest, run_matlab_job
    errors = []
    errors += [] if len(API_FUNCTIONS) == 15 else ["API helper count"]
    errors += [] if any(b.backend_id == "none" and b.available for b in detect_backends()) else ["none backend"]
    errors += [] if not validate_manifest(ScriptManifest(plugin_id="x", name_en="X", name_ru="X")) else ["manifest"]
    with tempfile.TemporaryDirectory() as td:
        lib = ScriptLibrary(Path(td) / "library")
        p = Path(td) / "a.m"; p.write_text("disp('x');", encoding="utf-8")
        lib.import_file(p)
        result = run_matlab_job(MatlabRunRequest(p, "a.m", backend="none"))
        errors += [] if result.status == "no_backend" else ["none runner isolation"]
    if errors: print("FAIL", "; ".join(errors)); return 1
    print("validate_matlab_studio OK"); return 0
if __name__ == "__main__": sys.exit(main())
