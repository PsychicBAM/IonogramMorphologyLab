"""Deterministic ML-C.1 development-only baseline classifiers."""
from __future__ import annotations

from typing import Any

import numpy as np

from .constants import BASELINE_LOGISTIC, BASELINE_MAJORITY, BASELINE_NEAREST_CENTROID
from .features import FeatureScaler


class MajorityClassBaseline:
    version = BASELINE_MAJORITY

    def __init__(self) -> None:
        self.majority_class_: str | None = None

    def fit(self, y_train: list[str] | np.ndarray) -> "MajorityClassBaseline":
        from collections import Counter

        labels = [str(x) for x in list(y_train)]
        if not labels:
            raise ValueError("Majority baseline requires nonempty training labels")
        counts = Counter(labels)
        max_count = max(counts.values())
        # Deterministic tie-break: lexicographically first among majority labels
        self.majority_class_ = sorted(
            label for label, count in counts.items() if count == max_count
        )[0]
        return self

    def predict(self, n: int) -> np.ndarray:
        if self.majority_class_ is None:
            raise ValueError("Baseline is not fitted")
        # CRITICAL: never use dtype=str with np.full — NumPy truncates to <U1>
        # ("mixed_spread" → "m"). Infer dtype from the full canonical label.
        label = str(self.majority_class_)
        return np.array([label] * int(n), dtype=object)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "majority_class": str(self.majority_class_ or "")}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MajorityClassBaseline":
        model = cls()
        raw = data.get("majority_class")
        if isinstance(raw, (list, tuple)) and raw:
            # Guard against accidental character-list serialization
            raise ValueError(
                f"Invalid majority_class artifact (iterable of characters?): {raw!r}"
            )
        model.majority_class_ = str(raw) if raw is not None else None
        return model


class NearestCentroidBaseline:
    version = BASELINE_NEAREST_CENTROID

    def __init__(self) -> None:
        self.scaler = FeatureScaler()
        self.classes_: np.ndarray | None = None
        self.centroids_: np.ndarray | None = None

    def fit(self, X_train: np.ndarray, y_train: list[str] | np.ndarray) -> "NearestCentroidBaseline":
        X = self.scaler.fit(X_train).transform(X_train)
        y = np.asarray(y_train, dtype=str)
        if len(X) != len(y) or not len(y):
            raise ValueError("Training features and labels must be nonempty and aligned")
        self.classes_ = np.unique(y)
        self.centroids_ = np.vstack([X[y == label].mean(axis=0) for label in self.classes_])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.classes_ is None or self.centroids_ is None:
            raise ValueError("Baseline is not fitted")
        data = self.scaler.transform(X)
        distances = ((data[:, None, :] - self.centroids_[None, :, :]) ** 2).sum(axis=2)
        idx = np.argmin(distances, axis=1)
        return np.array([str(self.classes_[i]) for i in idx], dtype=object)

    def to_dict(self) -> dict[str, Any]:
        if self.classes_ is None or self.centroids_ is None:
            raise ValueError("Baseline is not fitted")
        return {
            "version": self.version,
            "scaler": self.scaler.to_dict(),
            "classes": [str(c) for c in self.classes_.tolist()],
            "centroids": self.centroids_.tolist(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NearestCentroidBaseline":
        model = cls()
        model.scaler = FeatureScaler.from_dict(data["scaler"])
        model.classes_ = np.array([str(c) for c in data["classes"]], dtype=object)
        model.centroids_ = np.asarray(data["centroids"], dtype=float)
        return model


class LogisticRegressionBaseline:
    version = BASELINE_LOGISTIC

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)
        self.scaler = FeatureScaler()
        self.model: Any = None

    def _new_estimator(self) -> Any:
        """Preserve the specified multinomial contract across sklearn API revisions."""
        from sklearn.linear_model import LogisticRegression
        try:
            return LogisticRegression(
                multi_class="multinomial", solver="lbfgs", max_iter=500, C=1.0,
                random_state=self.seed,
            )
        except TypeError:
            # Newer sklearn releases removed the explicit argument; lbfgs selects
            # multinomial behavior automatically for multiclass data.
            return LogisticRegression(
                solver="lbfgs", max_iter=500, C=1.0, random_state=self.seed,
            )

    def fit(self, X_train: np.ndarray, y_train: list[str] | np.ndarray) -> "LogisticRegressionBaseline":
        X = self.scaler.fit(X_train).transform(X_train)
        self.model = self._new_estimator().fit(X, np.asarray(y_train, dtype=str))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Baseline is not fitted")
        raw = self.model.predict(self.scaler.transform(X))
        return np.array([str(v) for v in raw], dtype=object)

    def to_dict(self) -> dict[str, Any]:
        if self.model is None:
            raise ValueError("Baseline is not fitted")
        return {
            "version": self.version,
            "seed": self.seed,
            "scaler": self.scaler.to_dict(),
            "classes": [str(c) for c in self.model.classes_.tolist()],
            "coef": self.model.coef_.tolist(),
            "intercept": self.model.intercept_.tolist(),
            "n_features_in": int(self.model.n_features_in_),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogisticRegressionBaseline":
        model = cls(data.get("seed", 0))
        model.scaler = FeatureScaler.from_dict(data["scaler"])
        restored = model._new_estimator()
        restored.classes_ = np.array([str(c) for c in data["classes"]], dtype=object)
        restored.coef_ = np.asarray(data["coef"], dtype=float)
        restored.intercept_ = np.asarray(data["intercept"], dtype=float)
        restored.n_features_in_ = int(data.get("n_features_in", restored.coef_.shape[1]))
        restored.n_iter_ = np.ones(len(restored.classes_), dtype=np.int32)
        model.model = restored
        return model


_BASELINES = {
    BASELINE_MAJORITY: MajorityClassBaseline,
    BASELINE_NEAREST_CENTROID: NearestCentroidBaseline,
    BASELINE_LOGISTIC: LogisticRegressionBaseline,
}


def get_baseline(version: str) -> type:
    try:
        return _BASELINES[version]
    except KeyError as exc:
        raise ValueError(f"Unsupported baseline version: {version!r}") from exc


def list_baselines() -> list[dict[str, str]]:
    return [
        {"version": version, "name": cls.__name__, "scope": "development_only"}
        for version, cls in _BASELINES.items()
    ]
