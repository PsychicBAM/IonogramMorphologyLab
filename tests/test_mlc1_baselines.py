import numpy as np

from ionogram_morphology_lab.ml_offline_baselines.baselines import LogisticRegressionBaseline, MajorityClassBaseline, NearestCentroidBaseline


def test_majority_is_deterministic():
    first = MajorityClassBaseline().fit(["b", "a", "a", "b"])
    assert first.predict(3).tolist() == ["a"] * 3


def test_centroid_is_deterministic():
    X = np.array([[0., 0.], [0., 1.], [9., 9.], [10., 9.]])
    y = ["a", "a", "b", "b"]
    assert np.array_equal(NearestCentroidBaseline().fit(X, y).predict(X), NearestCentroidBaseline().fit(X, y).predict(X))


def test_logistic_is_seed_deterministic():
    X = np.array([[0., 0.], [0., 1.], [9., 9.], [10., 9.]])
    y = ["a", "a", "b", "b"]
    assert np.array_equal(LogisticRegressionBaseline(7).fit(X, y).predict(X), LogisticRegressionBaseline(7).fit(X, y).predict(X))
