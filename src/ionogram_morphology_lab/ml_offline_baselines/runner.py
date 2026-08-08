"""Execution workflow for sealed, development-only ML-C.1 experiments."""
from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .baselines import MajorityClassBaseline, get_baseline
from .exposure import append_exposure
from .features import extract_features_for_frame
from .holdout_firewall import HoldoutAccessGuard, assert_no_holdout_items
from .label_integrity import validate_evaluation_labels
from .metrics import build_metrics_report, error_cases
from .preflight import run_preflight
from .tasks import target_label_from_item


def _as_label_list(values: Any) -> list[str]:
    return [str(v) for v in list(values)]


def run_experiment(
    store: Any, manifest_store: Any, experiment_id: str, source_index: Any,
    progress_cb: Callable[[int, str], None] | None = None,
    cancel_cb: Callable[[], bool] | None = None,
) -> Any:
    """Run train/development only; no holdout manifests, frames, labels, or outputs."""
    guard = HoldoutAccessGuard()
    record = store.load_experiment(experiment_id)
    try:
        if progress_cb:
            progress_cb(5, "Loading train and development manifests")
        preflight = run_preflight(store.project_root, record.config.manifest_set_id, record.config, source_index)
        train, development = preflight.train_items, preflight.development_items
        assert_no_holdout_items(train + development)
        if cancel_cb and cancel_cb():
            return store.mark_cancelled(experiment_id)
        record = store.mark_running(experiment_id)

        def extract(items: list[dict[str, Any]]) -> np.ndarray:
            vectors = []
            for item in items:
                if cancel_cb and cancel_cb():
                    raise InterruptedError("cancelled")
                path = source_index.resolve(item["source_sha256"])
                vectors.append(extract_features_for_frame(source_index.resolve_frame(path, item["frame_index"])))
            return np.vstack(vectors)

        if progress_cb:
            progress_cb(25, "Extracting single-frame features")
        X_train, X_dev = extract(train), extract(development)
        y_train = _as_label_list(target_label_from_item(item) for item in train)
        y_dev = _as_label_list(target_label_from_item(item) for item in development)
        if not all(y_train) or not all(y_dev):
            raise ValueError("Missing frozen expert target label")
        if progress_cb:
            progress_cb(55, "Fitting baseline")
        cls = get_baseline(record.config.baseline_version)
        model = cls() if cls is MajorityClassBaseline else cls(record.config.seed) if cls.__name__ == "LogisticRegressionBaseline" else cls()
        model.fit(y_train) if isinstance(model, MajorityClassBaseline) else model.fit(X_train, y_train)
        if cancel_cb and cancel_cb():
            return store.mark_cancelled(experiment_id)
        if progress_cb:
            progress_cb(70, "Predicting development set")
        predictions = _as_label_list(
            model.predict(len(development))
            if isinstance(model, MajorityClassBaseline)
            else model.predict(X_dev)
        )
        # Fail closed before trusted metrics / confusion matrix construction
        labels = validate_evaluation_labels(
            y_train=y_train, y_dev=y_dev, predictions=predictions
        )
        metrics = build_metrics_report(y_dev, predictions, labels)
        rows = []
        for item, prediction, true_label in zip(development, predictions, y_dev):
            rows.append(
                {
                    "item_id": item.get("item_id"),
                    "atomic_group_id": item.get("atomic_group_id"),
                    "sequence_id": item.get("sequence_id"),
                    "source_date": item.get("source_date"),
                    "expert_reference": true_label,
                    "prediction": prediction,
                    "correct": prediction == true_label,
                }
            )
        if progress_cb:
            progress_cb(88, "Writing development artifacts")
        guard.assert_clean()
        model_dict = model.to_dict()
        scaler = model_dict.get("scaler") if isinstance(model_dict, dict) else None
        completed = store.save_completed(
            experiment_id,
            model=model_dict,
            predictions=rows,
            metrics=metrics,
            errors=error_cases(development, y_dev, predictions),
            run_metadata={
                "train_count": len(train),
                "development_count": len(development),
                "manifest_hash": preflight.manifest_hash,
                "holdout_status": "SEALED_UNUSED",
            },
            extras={
                "feature_scaler": scaler or {},
                "train_item_index": [
                    {
                        "item_id": it.get("item_id"),
                        "atomic_group_id": it.get("atomic_group_id"),
                        "role": "train",
                    }
                    for it in train
                ],
                "development_item_index": [
                    {
                        "item_id": it.get("item_id"),
                        "atomic_group_id": it.get("atomic_group_id"),
                        "role": "development",
                    }
                    for it in development
                ],
                "source_manifest_snapshot": {
                    "manifest_set_id": record.config.manifest_set_id,
                    "manifest_hash": preflight.manifest_hash,
                    "lifecycle_state": "frozen",
                    "holdout_status": "SEALED",
                },
                "environment": {
                    "protocol_version": record.protocol_version,
                    "baseline_version": record.config.baseline_version,
                    "feature_extractor_version": record.config.feature_extractor_version,
                    "seed": record.config.seed,
                },
            },
        )
        append_exposure(store.project_root, experiment_id, "train", [item["item_id"] for item in train])
        append_exposure(store.project_root, experiment_id, "development", [item["item_id"] for item in development])
        if progress_cb:
            progress_cb(100, "Completed development-only baseline")
        return completed
    except InterruptedError:
        return store.mark_cancelled(experiment_id)
    except Exception as exc:
        store.mark_failed(experiment_id, str(exc))
        raise
