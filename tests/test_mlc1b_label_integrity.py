"""ML-C.1b — fail-closed prediction label integrity."""
from __future__ import annotations

import pytest

from ionogram_morphology_lab.ml_offline_baselines.errors import LabelIntegrityError
from ionogram_morphology_lab.ml_offline_baselines.label_integrity import (
    validate_evaluation_labels,
)
from ionogram_morphology_lab.ml_offline_baselines.metrics import (
    build_metrics_report,
    confusion_matrix,
)


def test_invalid_prediction_m_fails_closed():
    with pytest.raises(LabelIntegrityError) as exc:
        validate_evaluation_labels(
            y_train=["mixed_spread", "frequency_spread"],
            y_dev=["range_spread", "frequency_spread"],
            predictions=["m", "m"],
        )
    assert "`m`" in str(exc.value)
    assert "stopped" in str(exc.value).lower() or "остановлена" in str(exc.value)


def test_invalid_prediction_ru_message():
    with pytest.raises(LabelIntegrityError) as exc:
        validate_evaluation_labels(
            y_train=["mixed_spread"],
            y_dev=["mixed_spread"],
            predictions=["m"],
            lang="ru",
        )
    assert "Недопустимая метка морфологии прогноза" in str(exc.value)
    assert "Оценка прогнозов остановлена" in str(exc.value)


def test_invalid_prediction_does_not_create_trusted_metrics():
    y_true = ["frequency_spread"] * 6 + ["range_spread"] * 3
    y_pred = ["m"] * 9
    with pytest.raises(LabelIntegrityError):
        labels = validate_evaluation_labels(
            y_train=["mixed_spread"] * 10 + ["frequency_spread"] * 5,
            y_dev=y_true,
            predictions=y_pred,
        )
        build_metrics_report(y_true, y_pred, labels)  # pragma: no cover


def test_malformed_class_not_added_to_confusion_matrix():
    with pytest.raises(LabelIntegrityError):
        validate_evaluation_labels(
            y_train=["mixed_spread", "frequency_spread"],
            y_dev=["frequency_spread", "range_spread"],
            predictions=["m", "mixed_spread"],
        )
    # Valid path never admits `m`
    labels = validate_evaluation_labels(
        y_train=["mixed_spread", "frequency_spread"],
        y_dev=["frequency_spread", "range_spread"],
        predictions=["mixed_spread", "mixed_spread"],
    )
    assert "m" not in labels
    cm = confusion_matrix(
        ["frequency_spread", "range_spread"],
        ["mixed_spread", "mixed_spread"],
        labels,
    )
    assert "m" not in cm["labels"]
