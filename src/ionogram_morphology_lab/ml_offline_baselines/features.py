"""Deterministic, candidate-free single-frame pool16 features."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .constants import FEATURE_COUNT, FEATURE_EXTRACTOR_VERSION, POOL_SIZE

FEATURE_CONTRACT: dict[str, Any] = {
    "version": FEATURE_EXTRACTOR_VERSION,
    "feature_count": FEATURE_COUNT,
    "pool_size": POOL_SIZE,
    "input": "single_amplitude_frame",
    "candidate_features": False,
    "temporal_features": False,
    "scaler_fit_scope": "train_only",
}


def normalize_frame(frame: np.ndarray) -> np.ndarray:
    """Robustly normalize one frame: nonfinite values become NaN; finite values
    are centered by their median and divided by IQR (p75-p25), using 1.0 when
    the IQR is zero or nonfinite. The rule is deterministic per frame."""
    array = np.asarray(frame, dtype=float)
    out = array.copy()
    out[~np.isfinite(out)] = np.nan
    finite = out[np.isfinite(out)]
    if not finite.size:
        return out
    median = float(np.median(finite))
    q25, q75 = np.percentile(finite, [25.0, 75.0])
    scale = float(q75 - q25)
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0
    return (out - median) / scale


def pool16_features(frame: np.ndarray) -> np.ndarray:
    """Pool a frame into a 16×16 grid with finite-value means, row-major."""
    array = np.asarray(frame, dtype=float)
    if array.ndim != 2:
        raise ValueError("pool16_features requires a two-dimensional frame")
    rows = np.array_split(np.arange(array.shape[0]), POOL_SIZE)
    cols = np.array_split(np.arange(array.shape[1]), POOL_SIZE)
    pooled = np.empty((POOL_SIZE, POOL_SIZE), dtype=float)
    for i, row_idx in enumerate(rows):
        for j, col_idx in enumerate(cols):
            block = array[np.ix_(row_idx, col_idx)]
            finite = block[np.isfinite(block)]
            pooled[i, j] = float(np.mean(finite)) if finite.size else np.nan
    result = pooled.ravel(order="C")
    assert result.shape == (FEATURE_COUNT,)
    return result


@dataclass
class FeatureScaler:
    """Train-only standardizer; missing pooled values are imputed by train means."""
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "FeatureScaler":
        data = np.asarray(X, dtype=float)
        if data.ndim != 2 or not data.shape[0]:
            raise ValueError("FeatureScaler.fit requires nonempty 2-D training data")
        means = np.nanmean(data, axis=0)
        means[~np.isfinite(means)] = 0.0
        filled = np.where(np.isfinite(data), data, means)
        scale = np.std(filled, axis=0)
        scale[~np.isfinite(scale) | (scale == 0)] = 1.0
        self.mean_, self.scale_ = means, scale
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise ValueError("FeatureScaler is not fitted")
        data = np.asarray(X, dtype=float)
        if data.shape[-1] != len(self.mean_):
            raise ValueError("Feature count does not match fitted scaler")
        filled = np.where(np.isfinite(data), data, self.mean_)
        return (filled - self.mean_) / self.scale_

    def to_dict(self) -> dict[str, list[float]]:
        if self.mean_ is None or self.scale_ is None:
            raise ValueError("FeatureScaler is not fitted")
        return {"mean": self.mean_.tolist(), "scale": self.scale_.tolist()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureScaler":
        return cls(np.asarray(data["mean"], dtype=float), np.asarray(data["scale"], dtype=float))


def extract_features_for_frame(frame: np.ndarray) -> np.ndarray:
    result = pool16_features(normalize_frame(frame))
    assert result.shape == (FEATURE_COUNT,)
    return result
