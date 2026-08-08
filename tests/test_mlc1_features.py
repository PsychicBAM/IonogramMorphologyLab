import numpy as np

from ionogram_morphology_lab.ml_offline_baselines.features import FEATURE_CONTRACT, FeatureScaler, extract_features_for_frame


def test_pool16_is_deterministic_and_has_256_features():
    frame = np.arange(256 * 400, dtype=float).reshape(256, 400)
    assert np.array_equal(extract_features_for_frame(frame), extract_features_for_frame(frame))
    assert extract_features_for_frame(frame).shape == (256,)


def test_feature_contract_excludes_candidate_and_identity():
    assert FEATURE_CONTRACT["candidate_features"] is False
    assert FEATURE_CONTRACT["input"] == "single_amplitude_frame"
    assert FEATURE_CONTRACT["scaler_fit_scope"] == "train_only"


def test_scaler_is_fit_only_on_train():
    train = np.array([[1., 2.], [3., 4.]])
    dev = np.array([[10_000., -10_000.]])
    one, two = FeatureScaler().fit(train), FeatureScaler().fit(train)
    two.transform(dev)
    assert np.array_equal(one.mean_, two.mean_)
    assert np.array_equal(one.scale_, two.scale_)
