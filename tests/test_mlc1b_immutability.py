"""ML-C.1b — historical malformed completed experiments are not rewritten."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ionogram_morphology_lab.ml_offline_baselines.label_integrity import (
    scan_prediction_rows_for_invalid_labels,
)


QA_ROOT = Path(__file__).resolve().parents[1] / (
    "workspaces/MLC1_Offline_Baselines_QA_8a22c20228f2/model_lab/ml_c_baselines"
)


def test_old_malformed_completed_experiment_is_not_rewritten():
    source = QA_ROOT / "mlc_607b3d3f01fa"
    if not source.is_dir():
        # Workspace QA fixture may be absent in CI clones
        return
    pred_path = source / "predictions_development.jsonl"
    before = pred_path.read_bytes()
    rows = [
        json.loads(line)
        for line in pred_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    bad = scan_prediction_rows_for_invalid_labels(rows)
    assert "m" in bad
    # Read-only scan must not mutate
    after = pred_path.read_bytes()
    assert before == after
    model = json.loads((source / "model_artifact.json").read_text(encoding="utf-8"))
    assert model.get("majority_class") == "mixed_spread"


def test_copy_of_malformed_artifact_stays_intact(tmp_path: Path):
    source = QA_ROOT / "mlc_607b3d3f01fa"
    if not source.is_dir():
        return
    dest = tmp_path / "historical"
    shutil.copytree(source, dest)
    before = (dest / "predictions_development.jsonl").read_bytes()
    rows = [
        json.loads(line)
        for line in (dest / "predictions_development.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert scan_prediction_rows_for_invalid_labels(rows) == ["m"]
    assert (dest / "predictions_development.jsonl").read_bytes() == before
