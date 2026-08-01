from __future__ import annotations

import hashlib
import json

import numpy as np

from ionogram_morphology_lab.classifiers.model_lab import (
    ModelLab,
    is_foreign_model,
)


def _write_unconfirmed_model(lab: ModelLab, model_id: str = "imported") -> None:
    model_dir = lab.root / "models" / model_id
    model_dir.mkdir(parents=True)
    payload = b"not a joblib file"
    (model_dir / "model.joblib").write_bytes(payload)
    (model_dir / "model_card.json").write_text(
        json.dumps(
            {
                "model_id": model_id,
                "kind": "imported",
                "status": "development",
                "features": ["f1"],
                "origin": "imported",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "trust_status": "unconfirmed",
                "foreign_warning": "Imported model warning",
            }
        ),
        encoding="utf-8",
    )


def test_unconfirmed_model_is_not_deserialized(tmp_path, monkeypatch):
    lab = ModelLab(tmp_path / "lab")
    _write_unconfirmed_model(lab)
    loaded = False

    def fail_load(_path):
        nonlocal loaded
        loaded = True
        raise AssertionError("joblib.load must not be called")

    monkeypatch.setattr("joblib.load", fail_load)
    result = lab.predict_features("imported", {"f1": 1.0})
    assert result["status"] == "trust_confirmation_required"
    assert loaded is False


def test_confirm_trust_persists_and_imported_remains_foreign(tmp_path):
    lab = ModelLab(tmp_path / "lab")
    _write_unconfirmed_model(lab)
    assert lab.require_trust_confirmation("imported") is True
    card = lab.confirm_trust("imported")
    assert card["trust_status"] == "user"
    assert is_foreign_model(card) is True
    assert card["foreign_warning"]
    assert lab.require_trust_confirmation("imported") is False


def test_train_writes_model_digest_and_manifest(tmp_path):
    lab = ModelLab(tmp_path / "lab")
    dataset = {
        "X": np.array([[0.0], [1.0], [0.1], [1.1], [0.2], [1.2], [0.3], [1.3]]),
        "y": np.array(["a", "b", "a", "b", "a", "b", "a", "b"], dtype=object),
        "dates": [f"day-{i}" for i in range(8)],
        "features": ["f1"],
        "classes": ["a", "b"],
        "class_counts": {"a": 4, "b": 4},
        "path": "memory",
    }
    card = lab.train(dataset, kind="random_forest", split_method="random", model_id="local")
    model_dir = lab.root / "models" / "local"
    assert card.origin == "local_trained"
    assert card.trust_status == "user"
    assert card.sha256 == (model_dir / "model.sha256").read_text(encoding="ascii").strip()
    assert hashlib.sha256((model_dir / "model.joblib").read_bytes()).hexdigest() == card.sha256
    assert card.training_manifest_path == str(model_dir / "training_manifest.json")
