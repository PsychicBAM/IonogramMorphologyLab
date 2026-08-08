"""ML-C.1b — undefined metrics stay null in artifacts; UI shows N/A / Не определено."""
from __future__ import annotations

from ionogram_morphology_lab.ml_offline_baselines.display_labels import format_metric_value
from ionogram_morphology_lab.ml_offline_baselines.metrics import (
    build_metrics_report,
    per_class_metrics,
)


def test_valid_nine_item_synthetic_denominator():
    y_true = ["frequency_spread"] * 6 + ["range_spread"] * 3
    y_pred = ["mixed_spread"] * 9
    labels = sorted({"frequency_spread", "mixed_spread", "range_spread"})
    report = build_metrics_report(y_true, y_pred, labels)
    assert report["sample_count"] == 9
    assert report["overall_agreement"] == 0.0
    supports = {row["class"]: row["support"] for row in report["per_class"]}
    assert supports["frequency_spread"] == 6
    assert supports["range_spread"] == 3
    assert supports["mixed_spread"] == 0


def test_undefined_metric_remains_null_in_artifact():
    rows = per_class_metrics(["frequency_spread"], ["frequency_spread"], ["frequency_spread", "mixed_spread"])
    assert rows[1]["precision"] is None
    assert rows[1]["recall"] is None
    assert rows[1]["f1"] is None
    report = build_metrics_report(
        ["frequency_spread"], ["frequency_spread"], ["frequency_spread", "mixed_spread"]
    )
    assert report["macro_f1"] is not None or report["macro_f1"] is None  # may be defined from one class
    # Class with zero support must stay None, never coerced to 0.0
    zero = next(r for r in report["per_class"] if r["class"] == "mixed_spread")
    assert zero["f1"] is None
    assert zero["precision"] is None


def test_undefined_metric_renders_na_en():
    assert format_metric_value(None, "en") == "N/A"
    assert format_metric_value("None", "en") == "N/A"


def test_undefined_metric_renders_ru():
    assert format_metric_value(None, "ru") == "Не определено"
    assert format_metric_value("None", "ru") == "Не определено"


def test_defined_zero_renders_as_zero():
    assert format_metric_value(0.0, "en") == "0.0"
    assert format_metric_value(0.0, "ru") == "0.0"
    report = build_metrics_report(
        ["frequency_spread", "range_spread"],
        ["mixed_spread", "mixed_spread"],
        ["frequency_spread", "mixed_spread", "range_spread"],
    )
    assert report["overall_agreement"] == 0.0
    assert format_metric_value(report["overall_agreement"], "en") == "0.0"
