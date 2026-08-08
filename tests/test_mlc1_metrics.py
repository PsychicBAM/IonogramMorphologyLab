from ionogram_morphology_lab.ml_offline_baselines.metrics import build_metrics_report, confusion_matrix, macro_f1, per_class_metrics


def test_confusion_matrix_and_macro_f1():
    cm = confusion_matrix(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert cm["matrix"] == [[1, 1], [0, 1]]
    assert macro_f1(per_class_metrics(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])) == 0.6666666666666666


def test_undefined_metrics_are_none_and_report_is_development_only():
    rows = per_class_metrics(["a"], ["a"], ["a", "b"])
    assert rows[1]["f1"] is None
    report = build_metrics_report(["a"], ["a"], ["a", "b"])
    assert report["scope"] == "development_only"
    assert not any("holdout" in key for key in report)
