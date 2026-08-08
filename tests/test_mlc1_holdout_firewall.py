import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_offline_baselines.errors import ProtocolViolation
from ionogram_morphology_lab.ml_offline_baselines.holdout_firewall import (
    aggregate_holdout_metadata, forbid_holdout_reference_path, safe_open_text,
)
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from tests.mlc1_fixtures import build_mlc1_fixture


def test_reference_label_opening_is_blocked(tmp_path: Path):
    path = tmp_path / "holdout_reference_labels.jsonl"; path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ProtocolViolation): forbid_holdout_reference_path(path)
    with pytest.raises(ProtocolViolation):
        with safe_open_text(path): pass


def test_run_writes_no_holdout_outputs_or_labels(tmp_path: Path):
    root, mid, index, _, manifests = build_mlc1_fixture(tmp_path)
    store = OfflineBaselineStore(root)
    record = store.create_draft(ExperimentConfig("qa", "a", mid, "spread_f_morphology_classification", "iml-majority-class-baseline-0.1.0"))
    assert store.validate(record.experiment_id, manifests, index).state == "validated"
    done = run_experiment(store, manifests, record.experiment_id, index)
    names = {item.name for item in store.path_for(done.experiment_id).iterdir()}
    assert not {name for name in names if "holdout" in name and ("pred" in name or "metric" in name)}
    summary = json.loads((store.path_for(done.experiment_id) / "experiment_summary.json").read_text())
    assert "label" not in json.dumps(summary).lower()


def test_holdout_role_is_rejected_in_preflight(tmp_path: Path):
    root, mid, index, _, manifests = build_mlc1_fixture(tmp_path)
    train = manifests.path_for(mid) / "train_manifest.jsonl"
    row = json.loads(train.read_text().splitlines()[0]); row["role"] = "untouched_holdout"
    train.write_text(json.dumps(row) + "\n", encoding="utf-8")
    store = OfflineBaselineStore(root)
    record = store.create_draft(ExperimentConfig("qa", "a", mid, "spread_f_morphology_classification", "iml-majority-class-baseline-0.1.0"))
    assert store.validate(record.experiment_id, manifests, index).state == "draft"


def test_aggregate_metadata_has_no_reference_labels():
    result = aggregate_holdout_metadata({"holdout_sealed": True}, 3, 1)
    assert "label" not in result
