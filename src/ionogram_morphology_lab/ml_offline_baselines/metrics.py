"""Development-only agreement metrics against frozen expert labels."""
from __future__ import annotations

from typing import Any


def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal length")
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for actual, predicted in zip(y_true, y_pred):
        if actual not in index or predicted not in index:
            raise ValueError("All labels must be declared in labels")
        matrix[index[actual]][index[predicted]] += 1
    return {"labels": list(labels), "matrix": matrix}


def per_class_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[dict[str, Any]]:
    cm = confusion_matrix(y_true, y_pred, labels)["matrix"]
    result: list[dict[str, Any]] = []
    for i, label in enumerate(labels):
        tp = cm[i][i]
        fp = sum(cm[row][i] for row in range(len(labels)) if row != i)
        fn = sum(cm[i][col] for col in range(len(labels)) if col != i)
        support = sum(cm[i])
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        result.append(
            {
                "class": label,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
            }
        )
    return result


def macro_f1(per_class: list[dict[str, Any]]) -> float | None:
    values = [row["f1"] for row in per_class if row.get("f1") is not None]
    return sum(values) / len(values) if values else None


def overall_agreement(y_true: list[str], y_pred: list[str]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal length")
    return sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0


def build_metrics_report(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    per_class = per_class_metrics(y_true, y_pred, labels)
    return {
        "scope": "development_only",
        "not_independent_validation": True,
        "wording": "Development-only agreement with frozen expert reference labels.",
        "sample_count": len(y_true),
        "valid_target_classes": list(labels),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels),
        "per_class": per_class,
        "macro_f1": macro_f1(per_class),
        "overall_agreement": overall_agreement(y_true, y_pred),
    }


def error_cases(items: list[Any], y_true: list[str], y_pred: list[str]) -> list[dict[str, Any]]:
    """Incorrect DEVELOPMENT rows with UI-aligned field names (plus legacy aliases)."""
    if not (len(items) == len(y_true) == len(y_pred)):
        raise ValueError("Items, y_true, and y_pred must have equal length")
    output = []
    for item, actual, predicted in zip(items, y_true, y_pred):
        if actual == predicted:
            continue
        get = item.get if isinstance(item, dict) else lambda k, d="": getattr(item, k, d)
        row = {
            "item_id": get("item_id", ""),
            "atomic_group_id": get("atomic_group_id", ""),
            "sequence_id": get("sequence_id", ""),
            "source_date": get("source_date", ""),
            "expert_reference": actual,
            "prediction": predicted,
            "correct": False,
            # Legacy aliases retained for older readers (not used by normal UI)
            "expert_label": actual,
            "predicted_label": predicted,
        }
        output.append(row)
    return output
