"""ML-C.1b — Error Analysis record completeness (development-only)."""
from __future__ import annotations

import json
from pathlib import Path

from ionogram_morphology_lab.ml_offline_baselines.constants import BASELINE_MAJORITY
from ionogram_morphology_lab.ml_offline_baselines.display_labels import format_optional_cell
from ionogram_morphology_lab.ml_offline_baselines.metrics import error_cases
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from tests.mlc1_fixtures import build_mlc1_fixture


def test_error_cases_populated_fields():
    items = [
        {
            "item_id": "item_a",
            "atomic_group_id": "ag_1",
            "sequence_id": "seq_1",
            "source_date": "2020-01-03",
        },
        {
            "item_id": "item_b",
            "atomic_group_id": "ag_1",
            "sequence_id": "seq_1",
            "source_date": "2020-01-03",
        },
    ]
    rows = error_cases(
        items,
        ["range_spread", "frequency_spread"],
        ["mixed_spread", "frequency_spread"],
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["item_id"] == "item_a"
    assert row["expert_reference"] == "range_spread"
    assert row["prediction"] == "mixed_spread"
    assert row["atomic_group_id"] == "ag_1"
    assert row["source_date"] == "2020-01-03"
    assert row["correct"] is False


def test_missing_optional_values_render_em_dash():
    assert format_optional_cell(None) == "—"
    assert format_optional_cell("") == "—"
    assert format_optional_cell("ag_1") == "ag_1"


def test_development_predictions_complete_and_no_holdout(tmp_path: Path):
    root, mid, index, _, manifests = build_mlc1_fixture(tmp_path)
    store = OfflineBaselineStore(root)
    config = ExperimentConfig(
        "qa", "tester", mid, "spread_f_morphology_classification", BASELINE_MAJORITY, seed=5
    )
    draft = store.create_draft(config)
    assert store.validate(draft.experiment_id, manifests, index).state == "validated"
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    base = store.path_for(completed.experiment_id)
    rows = [
        json.loads(line)
        for line in (base / "predictions_development.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(rows) == 9
    for row in rows:
        assert row.get("item_id")
        assert row.get("expert_reference")
        assert row.get("prediction")
        assert row.get("atomic_group_id")
        assert row.get("source_date")
        assert "correct" in row
        assert "m" != row["prediction"]
        assert len(str(row["prediction"])) > 1
        blob = json.dumps(row).lower()
        assert "holdout" not in blob
    errors = [
        json.loads(line)
        for line in (base / "error_cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    for row in errors:
        assert row.get("expert_reference") or row.get("expert_label")
        assert row.get("prediction") or row.get("predicted_label")
        assert row.get("atomic_group_id")
    assert not (base / "predictions_holdout.jsonl").exists()
