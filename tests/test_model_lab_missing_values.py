from __future__ import annotations

import numpy as np
import pytest

from ionogram_morphology_lab.classifiers.model_lab import ModelLab, ModelLabValidationError


def _dataset() -> dict:
    return {
        "X": np.array(
            [
                [0.0, np.nan, np.nan],
                [1.0, 2.0, np.nan],
                [0.1, 3.0, np.nan],
                [1.1, 4.0, np.nan],
            ]
        ),
        "y": np.array(["a", "b", "a", "b"], dtype=object),
        "dates": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        "features": ["f1", "f2", "all_missing"],
    }


def test_training_blocks_nonfinite_values_when_imputation_disabled(tmp_path):
    with pytest.raises(ModelLabValidationError) as raised:
        ModelLab(tmp_path).train(_dataset(), kind="logistic_regression", allow_imputation=False)
    assert raised.value.code == "missing_values_detected"
    assert "пропущенные" in raised.value.message_ru


def test_training_documents_median_imputation_and_removed_columns(tmp_path):
    card = ModelLab(tmp_path).train(
        _dataset(), kind="logistic_regression", allow_imputation=True, model_id="imputed"
    )
    manifest = card.training_manifest
    assert card.features == ["f1", "f2"]
    assert manifest["imputation_method"] == "median_with_missing_indicator"
    assert manifest["columns_imputed"] == ["f2"]
    assert manifest["columns_removed"] == ["all_missing"]
    assert manifest["preprocessing_version"] == "iml-ml-preproc-1.0"


def test_required_all_missing_feature_is_rejected(tmp_path):
    dataset = _dataset()
    dataset["required_features"] = ["all_missing"]
    with pytest.raises(ModelLabValidationError, match="required feature"):
        ModelLab(tmp_path).train(dataset)


def test_grouped_split_requires_more_than_one_date_group(tmp_path):
    dataset = _dataset()
    dataset["dates"] = ["2024-01-01"] * 4
    with pytest.raises(ModelLabValidationError) as raised:
        ModelLab(tmp_path).train(dataset)
    assert raised.value.code == "invalid_grouped_split"
