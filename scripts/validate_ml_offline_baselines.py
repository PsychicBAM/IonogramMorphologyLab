"""Fail-closed static and runtime validation for ML-C.1 artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "ionogram_morphology_lab" / "ml_offline_baselines"
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.ml_offline_baselines.label_integrity import (  # noqa: E402
    is_canonical_morphology_label,
)


def fail(message: str) -> None:
    raise RuntimeError(f"ML-C.1 validation failed: {message}")


def validate_static() -> None:
    constants = (PACKAGE / "constants.py").read_text(encoding="utf-8")
    for required in (
        "OFFLINE_BASELINE_PROTOCOL_VERSION",
        "FEATURE_EXTRACTOR_VERSION",
        "BASELINE_MAJORITY",
        "BASELINE_NEAREST_CENTROID",
        "BASELINE_LOGISTIC",
        "FORBIDDEN_PREDICTOR_KEYS",
        "NO_CLAIM_STATEMENT_EN",
    ):
        if required not in constants:
            fail(f"missing constants contract: {required}")
    if not (PACKAGE / "holdout_firewall.py").is_file():
        fail("holdout firewall module missing")
    if not (PACKAGE / "label_integrity.py").is_file():
        fail("label integrity module missing")
    source = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py"))
    if "RuleEngine" in source:
        fail("production RuleEngine wiring is forbidden")
    baselines = (PACKAGE / "baselines.py").read_text(encoding="utf-8")
    # Ban the ML-C.1a truncation pattern: np.full(..., dtype=str) → <U1>
    if "np.full(" in baselines and "dtype=str" in baselines.split("def predict", 1)[-1].split("def ", 1)[0]:
        fail("Majority predict must not use np.full(..., dtype=str) (truncates to <U1>)")
    no_claim = constants[
        constants.index("NO_CLAIM_STATEMENT_EN") : constants.index("NO_CLAIM_STATEMENT_RU")
    ]
    if "independent validation" not in no_claim.lower() or "not " not in no_claim.lower():
        fail("NO_CLAIM does not disclaim independent validation")
    for path in PACKAGE.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "holdout_reference_labels" in text and path.name not in {
            "holdout_firewall.py",
            "preflight.py",
            "store.py",
            "constants.py",
        }:
            fail(f"unapproved holdout reference access pattern: {path.name}")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _is_under_workspaces(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return "workspaces" in parts


def _historical_invalid_labels(predictions: list[dict], cm_labels: list) -> list[str]:
    bad: list[str] = []
    for row in predictions:
        pred = str(row.get("prediction", row.get("predicted_label", "")) or "")
        if pred and not is_canonical_morphology_label(pred) and pred not in bad:
            bad.append(pred)
    for label in cm_labels:
        token = str(label)
        if token and not is_canonical_morphology_label(token) and token not in bad:
            bad.append(token)
    return bad


def _validate_completed_experiment(experiment: Path, warnings: list[str]) -> None:
    names = {child.name for child in experiment.iterdir()}
    if {"predictions_holdout.jsonl", "metrics_holdout.json"} & names:
        fail(f"holdout result artifact in {experiment}")
    summary = experiment / "experiment_summary.json"
    if summary.exists():
        payload = json.loads(summary.read_text(encoding="utf-8"))
        if payload.get("metrics_scope") != "development_only":
            fail(f"invalid metric scope in {experiment}")
        if any("holdout" in key and "status" not in key for key in payload):
            fail(f"holdout metric field in {experiment}")

    preds_path = experiment / "predictions_development.jsonl"
    metrics_path = experiment / "metrics_development.json"
    if not (preds_path.exists() and metrics_path.exists()):
        return

    predictions = _read_jsonl(preds_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    sample_count = int(metrics.get("sample_count") or 0)
    if sample_count and len(predictions) != sample_count:
        fail(
            f"prediction count {len(predictions)} != DEVELOPMENT denominator "
            f"{sample_count} in {experiment}"
        )

    cm = metrics.get("confusion_matrix") or {}
    cm_labels = list(cm.get("labels") or [])
    historical_bad = _historical_invalid_labels(predictions, cm_labels)
    if historical_bad and _is_under_workspaces(experiment):
        # Do not rewrite historical malformed QA; surface and continue.
        warnings.append(
            f"HISTORICAL_INVALID: {experiment.name} contains invalid morphology "
            f"label(s) {historical_bad}; not rewritten. Create a new experiment."
        )
        return

    for row in predictions:
        pred = str(row.get("prediction", row.get("predicted_label", "")) or "")
        ref = str(row.get("expert_reference", row.get("expert_label", "")) or "")
        if ref and not is_canonical_morphology_label(ref):
            fail(f"invalid reference morphology label `{ref}` in {experiment}")
        if pred and not is_canonical_morphology_label(pred):
            fail(
                f"Prediction artifact contains an invalid morphology label `{pred}` "
                f"in {experiment}"
            )

    for label in cm_labels:
        if not is_canonical_morphology_label(str(label)):
            fail(f"invalid confusion-matrix class `{label}` in {experiment}")

    model_path = experiment / "model_artifact.json"
    if model_path.exists():
        model = json.loads(model_path.read_text(encoding="utf-8"))
        majority = model.get("majority_class")
        if majority is not None and str(majority) and not is_canonical_morphology_label(str(majority)):
            fail(f"invalid majority_class `{majority}` in {experiment}")
        for label in model.get("classes") or []:
            if not is_canonical_morphology_label(str(label)):
                fail(f"invalid model class `{label}` in {experiment}")

    errors = _read_jsonl(experiment / "error_cases.jsonl")
    pred_ids = {row.get("item_id") for row in predictions}
    for row in errors:
        if row.get("item_id") not in pred_ids:
            fail(f"error-case item not in development predictions: {experiment}")

    for row in predictions:
        blob = json.dumps(row, ensure_ascii=False).lower()
        if "/holdout/" in blob or "role\": \"holdout\"" in blob:
            fail(f"holdout contamination marker in development predictions: {experiment}")


def validate_experiments(base: Path) -> list[str]:
    warnings: list[str] = []
    for directory in base.rglob("ml_c_baselines"):
        for experiment in directory.iterdir():
            if not experiment.is_dir():
                continue
            _validate_completed_experiment(experiment, warnings)
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        validate_static()
        warnings = validate_experiments(args.path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"WARNING: {warning}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
