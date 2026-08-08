"""ML-C.1b — Majority Class full-label integrity (mixed_spread must not become m)."""
from __future__ import annotations

import numpy as np

from ionogram_morphology_lab.ml_offline_baselines.baselines import MajorityClassBaseline
from ionogram_morphology_lab.ui.build_identity import collect_build_identity


FULL_LABELS = (
    "frequency_spread",
    "mixed_spread",
    "range_spread",
    "no_supported_visible_spread",
    "indeterminate",
)


def test_build_identity_mlc1b():
    assert collect_build_identity(compute_sha=False)["release_phase"] == "ML-C.1b"


def test_majority_preserves_mixed_spread_full_string():
    model = MajorityClassBaseline().fit(
        ["mixed_spread", "mixed_spread", "frequency_spread"]
    )
    assert model.majority_class_ == "mixed_spread"
    preds = model.predict(5)
    assert preds.tolist() == ["mixed_spread"] * 5
    assert all(p == "mixed_spread" for p in preds)
    assert all(len(str(p)) > 1 for p in preds)


def test_majority_never_returns_first_character():
    for label in FULL_LABELS:
        model = MajorityClassBaseline().fit([label] * 3)
        preds = model.predict(4)
        assert model.majority_class_ == label
        assert preds.tolist() == [label] * 4
        assert preds[0] != label[0]


def test_majority_serialization_reload_preserves_full_target():
    fitted = MajorityClassBaseline().fit(["mixed_spread"] * 4 + ["range_spread"])
    payload = fitted.to_dict()
    assert payload["majority_class"] == "mixed_spread"
    restored = MajorityClassBaseline.from_dict(payload)
    assert restored.majority_class_ == "mixed_spread"
    assert restored.predict(3).tolist() == ["mixed_spread"] * 3


def test_np_full_dtype_str_reproduces_historical_bug():
    """Document the ML-C.1a root cause; product code must not use this pattern."""
    truncated = np.full(3, "mixed_spread", dtype=str)
    assert truncated.dtype == np.dtype("<U1")
    assert truncated.tolist() == ["m", "m", "m"]
