"""Future ML model interfaces — no Article 3 training in IML-1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

MODEL_INTERFACE_NOTE = (
    "IML-1 does not train a final ML model. Article 3 labels remain inaccessible. "
    "Future models may use interpretable features with date-based splits."
)


class MorphologyModel(ABC):
    name: str = "base"
    version: str = "none"

    @abstractmethod
    def predict_features(self, features: dict[str, float]) -> dict[str, Any]:
        """Return candidate morphology proposal or abstain."""

    def is_available(self) -> bool:
        return False


class NullModel(MorphologyModel):
    name = "null"
    version = "none"

    def predict_features(self, features: dict[str, float]) -> dict[str, Any]:
        return {
            "status": "not_available",
            "candidate_morphology": "abstain",
            "note": MODEL_INTERFACE_NOTE,
        }


# Reserved names for future implementations (stubs only)
SUPPORTED_FUTURE_MODELS = [
    "logistic_regression",
    "svm",
    "random_forest",
    "gradient_boosting",
    "knn",
    "calibrated_ensemble",
    "cnn_vision_later",
]
