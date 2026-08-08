"""Fail-closed morphology label validation for ML-C.1 development evaluation."""
from __future__ import annotations

from typing import Any, Iterable

from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES

from .errors import LabelIntegrityError

# Task A Spread-F morphology classification — human expert morphology tokens.
CANONICAL_MORPHOLOGY_LABELS: frozenset[str] = frozenset(HUMAN_MORPHOLOGY_CODES)


def invalid_prediction_message(label: str, lang: str = "en") -> str:
    if str(lang).lower().startswith("ru"):
        return (
            f"Недопустимая метка морфологии прогноза: `{label}`.\n"
            "Оценка прогнозов остановлена."
        )
    return (
        f"Invalid predicted morphology label: `{label}`.\n"
        "Prediction evaluation was stopped."
    )


def is_canonical_morphology_label(label: Any) -> bool:
    if not isinstance(label, str):
        return False
    return label in CANONICAL_MORPHOLOGY_LABELS


def assert_canonical_labels(
    labels: Iterable[Any],
    *,
    role: str,
    lang: str = "en",
) -> None:
    for raw in labels:
        token = str(raw) if raw is not None else ""
        if not is_canonical_morphology_label(token):
            if role == "prediction":
                raise LabelIntegrityError(invalid_prediction_message(token, lang))
            if str(lang).lower().startswith("ru"):
                raise LabelIntegrityError(
                    f"Недопустимая метка морфологии ({role}): `{token}`.\n"
                    "Оценка прогнозов остановлена."
                )
            raise LabelIntegrityError(
                f"Invalid morphology label ({role}): `{token}`.\n"
                "Prediction evaluation was stopped."
            )


def assert_train_known_predictions(
    predictions: Iterable[Any],
    train_labels: Iterable[Any],
    *,
    lang: str = "en",
) -> None:
    known = {str(x) for x in train_labels}
    for raw in predictions:
        token = str(raw)
        if token not in known:
            if str(lang).lower().startswith("ru"):
                raise LabelIntegrityError(
                    f"Прогноз `{token}` не входит в классы TRAIN.\n"
                    "Оценка прогнозов остановлена."
                )
            raise LabelIntegrityError(
                f"Predicted label `{token}` is not a TRAIN-known class.\n"
                "Prediction evaluation was stopped."
            )


def validate_evaluation_labels(
    *,
    y_train: list[str],
    y_dev: list[str],
    predictions: list[str],
    lang: str = "en",
) -> list[str]:
    """Validate labels and return deterministic confusion-matrix axes.

    Axes are the sorted union of TRAIN and DEVELOPMENT reference labels only.
    Malformed prediction tokens must never become matrix classes.
    """
    assert_canonical_labels(y_train, role="train", lang=lang)
    assert_canonical_labels(y_dev, role="development reference", lang=lang)
    assert_canonical_labels(predictions, role="prediction", lang=lang)
    assert_train_known_predictions(predictions, y_train, lang=lang)
    # Predictions are validated separately; they must already be subset of train.
    axes = sorted(set(y_train) | set(y_dev))
    if not axes:
        raise LabelIntegrityError("No valid morphology classes for evaluation")
    # Ensure every prediction is representable on the matrix
    for pred in predictions:
        if pred not in axes:
            # Train-known but somehow missing from axes — include train labels.
            axes = sorted(set(axes) | set(y_train))
            break
    for pred in predictions:
        if pred not in axes:
            raise LabelIntegrityError(
                invalid_prediction_message(str(pred), lang)
            )
    return axes


def scan_prediction_rows_for_invalid_labels(
    rows: Iterable[dict[str, Any]],
) -> list[str]:
    """Return invalid predicted labels found in historical prediction rows."""
    bad: list[str] = []
    for row in rows:
        pred = row.get("prediction", row.get("predicted_label", ""))
        if pred is None or pred == "":
            continue
        token = str(pred)
        if not is_canonical_morphology_label(token) and token not in bad:
            bad.append(token)
    return bad
