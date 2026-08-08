from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_offline_baselines.constants import OFFLINE_BASELINE_PROTOCOL_VERSION, SUPPORTED_TASK
from ionogram_morphology_lab.ml_offline_baselines.errors import PreflightError
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.preflight import run_preflight
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from tests.mlc1_fixtures import build_mlc1_fixture


def _config(mid, task=SUPPORTED_TASK):
    return ExperimentConfig("qa", "tester", mid, task, "iml-majority-class-baseline-0.1.0")


def test_frozen_manifest_is_accepted_and_identity_is_mlc1(tmp_path: Path):
    root, mid, index, *_ = build_mlc1_fixture(tmp_path)
    assert run_preflight(root, mid, _config(mid), index).ok
    assert collect_build_identity(compute_sha=False)["release_phase"] == "ML-C.1b"
    assert OFFLINE_BASELINE_PROTOCOL_VERSION


@pytest.mark.parametrize("damage", ["draft", "missing_lock", "corrupt_lock"])
def test_unfrozen_or_invalid_holdout_lock_is_rejected(tmp_path: Path, damage: str):
    root, mid, index, _, store = build_mlc1_fixture(tmp_path)
    path = store.path_for(mid)
    if damage == "draft":
        manifest = store.load_manifest_set(mid); manifest.lifecycle_state = "draft"; store._save_manifest_set(manifest)
    elif damage == "missing_lock":
        (path / "holdout_lock.json").unlink()
    else:
        (path / "holdout_lock.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PreflightError):
        run_preflight(root, mid, _config(mid), index)


def test_only_task_a_contract_is_supported(tmp_path: Path):
    root, mid, index, *_ = build_mlc1_fixture(tmp_path)
    with pytest.raises(PreflightError):
        run_preflight(root, mid, _config(mid, "unsupported_task"), index)
