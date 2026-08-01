#!/usr/bin/env python3
"""Headless project/import/audit/cache/features/rules/export smoke test."""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    from ionogram_morphology_lab.instrument_profiles.schema import InstrumentProfile, save_profile
    from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest, run_matlab_job
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.projects.pipeline import batch_analyze
    from ionogram_morphology_lab.reports.export_reports import export_run_reports
    from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
    from ionogram_morphology_lab.utils.hashing import sha256_file
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        root = Path(td); syn = root / "syn"; write_synthetic_mat_library(syn)
        profile = InstrumentProfile(profile_id="v1_e2e", profile_name="v1 e2e", frames_per_file=3, height_bins=256, frequency_bins=400, frequency_start_mhz=1.5, frequency_step_mhz=.019, expected_amplitude_shape=[768, 400], profile_verification_status="user-defined-unverified")
        save_profile(profile)
        source = syn / "demo_horizontally_diffuse.mat"; before = sha256_file(source)
        project = create_project("v1_e2e", workspace_parent=root / "workspaces"); project.profile_id = profile.profile_id
        summary = batch_analyze(project, [source], frame_indices=[1, 2], max_workers=1)
        report = export_run_reports(Path(summary["run_root"]), language="en")
        result = run_matlab_job(MatlabRunRequest(root / "missing.m", "missing.m", backend="none"))
        if summary["n_results"] < 1 or not Path(report["csv"]).is_file() or sha256_file(source) != before or result.status != "no_backend":
            print("FAIL end-to-end assertions"); return 1
    print("validate_end_to_end OK"); return 0
if __name__ == "__main__": sys.exit(main())
