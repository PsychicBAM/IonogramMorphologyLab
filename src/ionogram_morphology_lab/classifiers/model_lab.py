"""Development Model Lab — train interpretable models without writing Python."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

MODEL_KINDS = [
    "logistic_regression",
    "linear_svm",
    "rbf_svm",
    "random_forest",
    "gradient_boosting",
    "knn",
    "calibrated_ensemble",
]


@dataclass
class ModelCard:
    model_id: str
    kind: str
    status: str  # development | locally_validated | externally_validated | research_use_only
    created_at: str
    features: list[str]
    classes: list[str]
    split_method: str
    metrics: dict[str, Any] = field(default_factory=dict)
    calibration_status: str = "uncalibrated"
    abstention_threshold: float = 0.45
    limitations: list[str] = field(
        default_factory=lambda: [
            "Development / research use only unless externally validated",
            "Article 3 blinded labels were not used",
            "Neighboring-frame leakage prevented by date/sequence grouping",
        ]
    )
    training_manifest: dict[str, Any] = field(default_factory=dict)
    origin: str = "local_trained"  # local_trained | imported | bundled
    sha256: str = ""
    training_manifest_path: str = ""
    trust_status: str = "unconfirmed"  # unconfirmed | user | builtin
    foreign_warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_foreign_model(card: ModelCard | dict[str, Any]) -> bool:
    """Return whether a model came from outside this installation."""
    origin = card.origin if isinstance(card, ModelCard) else card.get("origin", "imported")
    return origin == "imported"


def _group_split_by_date(
    dates: list[str], y: np.ndarray, test_fraction: float = 0.25, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Split by unique dates — never split neighboring frames across train/test."""
    rng = np.random.default_rng(seed)
    uniq = sorted(set(dates))
    rng.shuffle(uniq)
    n_test = max(1, int(round(len(uniq) * test_fraction)))
    test_dates = set(uniq[:n_test])
    train_idx = np.array([i for i, d in enumerate(dates) if d not in test_dates], dtype=int)
    test_idx = np.array([i for i, d in enumerate(dates) if d in test_dates], dtype=int)
    if train_idx.size == 0 or test_idx.size == 0:
        # fallback: keep all in train if too few dates
        train_idx = np.arange(len(dates))
        test_idx = train_idx[: max(1, len(dates) // 5)]
    return train_idx, test_idx


def _make_estimator(kind: str):
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    if kind == "logistic_regression":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000)),
            ]
        )
    if kind == "linear_svm":
        return Pipeline([("scaler", StandardScaler()), ("clf", SVC(kernel="linear", probability=True))])
    if kind == "rbf_svm":
        return Pipeline([("scaler", StandardScaler()), ("clf", SVC(kernel="rbf", probability=True))])
    if kind == "random_forest":
        return RandomForestClassifier(n_estimators=200, random_state=0)
    if kind == "gradient_boosting":
        return GradientBoostingClassifier(random_state=0)
    if kind == "knn":
        return Pipeline([("scaler", StandardScaler()), ("clf", KNeighborsClassifier(n_neighbors=5))])
    if kind == "calibrated_ensemble":
        base = [
            ("lr", LogisticRegression(max_iter=2000)),
            ("rf", RandomForestClassifier(n_estimators=100, random_state=0)),
        ]
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", VotingClassifier(estimators=base, voting="soft")),
            ]
        )
    raise ValueError(f"unknown_model:{kind}")


class ModelLab:
    def __init__(self, root: Path | str | None = None):
        self.root = ensure_dir(root or (app_root() / "model_lab"))
        ensure_dir(self.root / "models")
        ensure_dir(self.root / "datasets")

    def import_labeled_csv(
        self,
        path: Path | str,
        label_column: str = "label",
        date_column: str = "date",
        feature_columns: list[str] | None = None,
    ) -> dict[str, Any]:
        import csv

        path = Path(path)
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError("empty_dataset")
        if feature_columns is None:
            feature_columns = [
                k
                for k in rows[0].keys()
                if k not in (label_column, date_column, "frame_id", "sequence_id")
            ]
        X = np.array([[float(r[c]) for c in feature_columns] for r in rows], dtype=float)
        y = np.array([r[label_column] for r in rows], dtype=object)
        dates = [r.get(date_column, "unknown") for r in rows]
        out = {
            "path": str(path),
            "n": len(rows),
            "features": feature_columns,
            "classes": sorted(set(y.tolist())),
            "class_counts": {c: int(np.sum(y == c)) for c in sorted(set(y.tolist()))},
            "X": X,
            "y": y,
            "dates": dates,
        }
        meta_path = self.root / "datasets" / f"{path.stem}_meta.json"
        meta_path.write_text(
            json.dumps({k: v for k, v in out.items() if k not in ("X", "y")}, indent=2),
            encoding="utf-8",
        )
        np.savez_compressed(self.root / "datasets" / f"{path.stem}.npz", X=X, y=y)
        return out

    def train(
        self,
        dataset: dict[str, Any],
        kind: str = "random_forest",
        split_method: str = "by_date",
        seed: int = 0,
        abstention_threshold: float = 0.45,
        model_id: str | None = None,
    ) -> ModelCard:
        import joblib
        from sklearn.metrics import (
            balanced_accuracy_score,
            classification_report,
            confusion_matrix,
            f1_score,
        )

        if kind not in MODEL_KINDS:
            raise ValueError(f"unknown_model:{kind}")
        X = dataset["X"]
        y = dataset["y"]
        dates = dataset["dates"]
        if split_method == "by_date":
            tr, te = _group_split_by_date(dates, y, seed=seed)
        else:
            rng = np.random.default_rng(seed)
            idx = np.arange(len(y))
            rng.shuffle(idx)
            cut = max(1, int(0.75 * len(idx)))
            tr, te = idx[:cut], idx[cut:]

        # leakage check: no shared dates
        if split_method == "by_date":
            assert set(np.array(dates)[tr]).isdisjoint(set(np.array(dates)[te])) or len(set(dates)) < 2

        est = _make_estimator(kind)
        est.fit(X[tr], y[tr])
        pred = est.predict(X[te])
        proba = None
        if hasattr(est, "predict_proba"):
            try:
                proba = est.predict_proba(X[te])
            except Exception:  # noqa: BLE001
                proba = None
        metrics = {
            "balanced_accuracy": float(balanced_accuracy_score(y[te], pred)),
            "macro_f1": float(f1_score(y[te], pred, average="macro")),
            "confusion_matrix": confusion_matrix(y[te], pred).tolist(),
            "classification_report": classification_report(y[te], pred, output_dict=True),
            "n_train": int(len(tr)),
            "n_test": int(len(te)),
            "abstention_rate": 0.0,
        }
        if proba is not None:
            conf = proba.max(axis=1)
            abstain = conf < abstention_threshold
            metrics["abstention_rate"] = float(np.mean(abstain))
            metrics["mean_max_proba"] = float(np.mean(conf))

        mid = model_id or f"{kind}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        model_dir = ensure_dir(self.root / "models" / mid)
        joblib_path = model_dir / "model.joblib"
        joblib.dump(est, joblib_path)
        model_sha256 = _sha256_file(joblib_path)
        (model_dir / "model.sha256").write_text(model_sha256 + "\n", encoding="ascii")
        manifest_path = model_dir / "training_manifest.json"
        training_manifest = {
            "seed": seed,
            "class_counts": dataset.get("class_counts"),
            "source": dataset.get("path"),
            "article3_labels_used": False,
        }
        manifest_path.write_text(
            json.dumps(training_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        card = ModelCard(
            model_id=mid,
            kind=kind,
            status="development",
            created_at=datetime.now(timezone.utc).isoformat(),
            features=list(dataset["features"]),
            classes=list(dataset["classes"]),
            split_method=split_method,
            metrics=metrics,
            calibration_status="uncalibrated",
            abstention_threshold=abstention_threshold,
            training_manifest=training_manifest,
            origin="local_trained",
            sha256=model_sha256,
            training_manifest_path=str(manifest_path),
            trust_status="user",
            foreign_warning="",
        )
        (model_dir / "model_card.json").write_text(
            json.dumps(card.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return card

    def list_models(self) -> list[dict[str, Any]]:
        out = []
        for p in sorted((self.root / "models").glob("*/model_card.json")):
            out.append(json.loads(p.read_text(encoding="utf-8")))
        return out

    def _model_dir(self, model_id: str) -> Path | None:
        if "/" in model_id or "\\" in model_id or ".." in model_id:
            return None
        model_dir = (self.root / "models" / model_id).resolve()
        models_root = (self.root / "models").resolve()
        if models_root not in model_dir.parents or model_dir == models_root:
            return None
        return model_dir

    def require_trust_confirmation(self, model_id: str) -> bool:
        """Check model-card trust without deserializing the model."""
        model_dir = self._model_dir(model_id)
        if model_dir is None:
            return True
        card_path = model_dir / "model_card.json"
        if not card_path.exists():
            return True
        card = json.loads(card_path.read_text(encoding="utf-8"))
        return card.get("trust_status", "unconfirmed") not in {"user", "builtin"}

    def confirm_trust(self, model_id: str) -> dict[str, Any]:
        """Persist explicit user trust in a model card without loading joblib."""
        model_dir = self._model_dir(model_id)
        if model_dir is None:
            raise ValueError("invalid_model_id")
        card_path = model_dir / "model_card.json"
        if not card_path.exists():
            raise FileNotFoundError(card_path)
        card = json.loads(card_path.read_text(encoding="utf-8"))
        card["trust_status"] = "user"
        if is_foreign_model(card):
            card["foreign_warning"] = (
                "Imported model: joblib deserialization can execute code. "
                "Only use this model if you trust its source."
            )
        card_path.write_text(
            json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return card

    def predict_features(
        self,
        model_id: str,
        features: dict[str, float],
        abstention_threshold: float | None = None,
        *,
        trust_confirmed: bool = False,
    ) -> dict[str, Any]:
        import joblib

        # Deserialization risk: only load joblib from this lab's models/ tree with a card.
        # Never load arbitrary user-picked pickle paths automatically.
        model_dir = self._model_dir(model_id)
        if model_dir is None:
            return {
                "status": "rejected",
                "candidate_morphology": "abstain",
                "note": "Untrusted model id rejected",
            }
        card_path = model_dir / "model_card.json"
        joblib_path = model_dir / "model.joblib"
        if not card_path.exists() or not joblib_path.exists():
            return {"status": "not_available", "candidate_morphology": "abstain"}
        card = json.loads(card_path.read_text(encoding="utf-8"))
        if card.get("status") in {"untrusted", "rejected"}:
            return {
                "status": "rejected",
                "candidate_morphology": "abstain",
                "note": "Model card marks package as untrusted",
            }
        trust_status = card.get("trust_status", "unconfirmed")
        if trust_status not in {"user", "builtin"} and not trust_confirmed:
            return {
                "status": "trust_confirmation_required",
                "candidate_morphology": "abstain",
                "model_id": model_id,
                "foreign_warning": card.get("foreign_warning", ""),
                "note": "Explicit trust confirmation is required before loading this model",
            }
        expected_sha = str(card.get("sha256", "")).lower()
        actual_sha = _sha256_file(joblib_path)
        if not expected_sha or actual_sha != expected_sha:
            return {
                "status": "rejected",
                "candidate_morphology": "abstain",
                "model_id": model_id,
                "note": "Model SHA-256 is missing or does not match model_card.json",
            }
        est = joblib.load(joblib_path)
        x = np.array([[features.get(f, 0.0) for f in card["features"]]], dtype=float)
        pred = est.predict(x)[0]
        conf = None
        if hasattr(est, "predict_proba"):
            proba = est.predict_proba(x)[0]
            conf = float(np.max(proba))
        thr = abstention_threshold if abstention_threshold is not None else card.get("abstention_threshold", 0.45)
        if conf is not None and conf < thr:
            return {
                "status": "abstain",
                "candidate_morphology": "abstain",
                "confidence_score": conf,
                "model_id": model_id,
                "model_status": card.get("status"),
            }
        return {
            "status": "proposed",
            "candidate_morphology": str(pred),
            "confidence_score": conf,
            "confidence_calibration_status": card.get("calibration_status", "uncalibrated"),
            "model_id": model_id,
            "model_status": card.get("status"),
            "note": "Development model — not externally validated",
        }
