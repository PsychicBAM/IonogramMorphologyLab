from __future__ import annotations

import json
from pathlib import Path

from ionogram_morphology_lab.database.project_db import ProjectDatabase
from ionogram_morphology_lab.i18n import I18n
from ionogram_morphology_lab.projects.model import create_project
from ionogram_morphology_lab.projects.pipeline import batch_analyze
from ionogram_morphology_lab.reports.export_reports import export_run_reports
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import app_root


def test_project_batch_export_audit(tmp_path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    # Use generic-like small mats with Amp_all — profile expects 368640; audit may warn.
    # Point project profile to a user profile saved for small stacks.
    from ionogram_morphology_lab.instrument_profiles.schema import InstrumentProfile, save_profile

    prof = InstrumentProfile(
        profile_id="syn_test_profile",
        profile_name="Synthetic test",
        frames_per_file=3,
        height_bins=256,
        frequency_bins=400,
        frequency_start_mhz=1.5,
        frequency_step_mhz=0.019,
        expected_amplitude_shape=[768, 400],
        profile_verification_status="user-defined-unverified",
        warnings=["synthetic test profile"],
    )
    save_profile(prof)

    project = create_project("pytest_iml", language="en", workspace_parent=tmp_path / "ws")
    project.profile_id = "syn_test_profile"
    mats = [syn / "demo_horizontally_diffuse.mat", syn / "demo_vertically_diffuse.mat"]
    before = {str(m): sha256_file(m) for m in mats}
    summary = batch_analyze(project, mats, frame_indices=[1, 2], frame_step=1, max_workers=1)
    assert summary["n_results"] >= 2
    after = {str(m): sha256_file(m) for m in mats}
    assert before == after

    run_root = Path(summary["run_root"])
    assert (run_root / "exports" / "reproducibility_manifest.json").exists()
    paths = export_run_reports(run_root, language="en")
    assert Path(paths["csv"]).exists()
    assert Path(paths["html"]).exists()
    export_run_reports(run_root, language="ru")

    db = ProjectDatabase(Path(project.root) / "project.sqlite")
    frames = db.list_frame_results(summary["run_id"])
    assert frames
    auto = frames[0]["auto"]
    assert "limitations" in auto
    assert auto["model_version"] == "none"
    db.update_human_decision(frames[0]["frame_id"], {"decision": "accept"})
    frames2 = db.list_frame_results(summary["run_id"])
    assert frames2[0]["human"]["decision"] == "accept"
    assert frames2[0]["auto"]["candidate_morphology"] == auto["candidate_morphology"]


def test_canonical_values_language_independent():
    # morphology keys stay English internally in i18n morphology.* values differ by language
    en = I18n("en").t("morphology.frequency")
    ru = I18n("ru").t("morphology.frequency")
    assert en != ru
    # internal canonical token unchanged in code paths
    from ionogram_morphology_lab.rules.engine import CANONICAL_MORPHOLOGY

    assert "frequency" in CANONICAL_MORPHOLOGY
