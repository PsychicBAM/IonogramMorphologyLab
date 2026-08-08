from pathlib import Path

import pytest
import json

from ionogram_morphology_lab.ml_offline_baselines.constants import BASELINE_MAJORITY, BASELINE_NEAREST_CENTROID
from ionogram_morphology_lab.ml_offline_baselines.errors import ImmutabilityError
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from tests.mlc1_fixtures import build_mlc1_fixture


@pytest.mark.parametrize("baseline", [BASELINE_MAJORITY, BASELINE_NEAREST_CENTROID])
def test_end_to_end_development_only_run(tmp_path: Path, baseline: str):
    root, mid, index, _, manifests = build_mlc1_fixture(tmp_path)
    store = OfflineBaselineStore(root)
    config = ExperimentConfig("qa", "tester", mid, "spread_f_morphology_classification", baseline, seed=5)
    draft = store.create_draft(config)
    assert store.validate(draft.experiment_id, manifests, index).state == "validated"
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    artifact_names = {path.name for path in store.path_for(completed.experiment_id).iterdir()}
    assert completed.state == "completed"
    assert "predictions_development.jsonl" in artifact_names
    assert not any("holdout" in name for name in artifact_names)
    with pytest.raises(ImmutabilityError):
        store.save_draft(completed, ExperimentConfig("changed", "tester", mid, "spread_f_morphology_classification", baseline))
    revision = store.create_revision(completed.experiment_id, ExperimentConfig("revision", "tester", mid, "spread_f_morphology_classification", baseline))
    assert revision.parent_experiment_id == completed.experiment_id
    ledger = (root / "model_lab/ml_c_baselines/exposure_ledger.jsonl").read_text(encoding="utf-8")
    assert "holdout" not in ledger
