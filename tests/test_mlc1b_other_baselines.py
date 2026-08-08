"""ML-C.1b — nearest-centroid / logistic canonical label outputs."""
from __future__ import annotations

import numpy as np

from ionogram_morphology_lab.ml_offline_baselines.baselines import (
    LogisticRegressionBaseline,
    NearestCentroidBaseline,
)
from ionogram_morphology_lab.ml_offline_baselines.label_integrity import (
    is_canonical_morphology_label,
)

LABELS = (
    "frequency_spread",
    "mixed_spread",
    "range_spread",
    "no_supported_visible_spread",
    "indeterminate",
)


def _toy_xy():
    X = np.array(
        [
            [0.0, 0.0],
            [0.1, 0.0],
            [9.0, 9.0],
            [9.1, 9.0],
            [4.0, 0.0],
            [4.1, 0.1],
        ],
        dtype=float,
    )
    y = [
        "frequency_spread",
        "frequency_spread",
        "mixed_spread",
        "mixed_spread",
        "range_spread",
        "range_spread",
    ]
    return X, y


def test_nearest_centroid_output_is_valid_canonical_label():
    X, y = _toy_xy()
    preds = NearestCentroidBaseline().fit(X, y).predict(X)
    assert all(is_canonical_morphology_label(str(p)) for p in preds)
    assert all(str(p) in set(y) for p in preds)
    assert all(len(str(p)) > 1 for p in preds)
    payload = NearestCentroidBaseline().fit(X, y).to_dict()
    assert all(is_canonical_morphology_label(c) for c in payload["classes"])
    restored = NearestCentroidBaseline.from_dict(payload)
    assert all(is_canonical_morphology_label(str(p)) for p in restored.predict(X))


def test_logistic_output_is_valid_canonical_label():
    X, y = _toy_xy()
    model = LogisticRegressionBaseline(7).fit(X, y)
    preds = model.predict(X)
    assert all(is_canonical_morphology_label(str(p)) for p in preds)
    assert all(len(str(p)) > 1 for p in preds)
    payload = model.to_dict()
    assert all(is_canonical_morphology_label(c) for c in payload["classes"])
    restored = LogisticRegressionBaseline.from_dict(payload)
    assert all(is_canonical_morphology_label(str(p)) for p in restored.predict(X))


def test_string_indexing_trap_labels_remain_full():
    for label in LABELS:
        assert label[0] != label
        assert len(label) > 1
