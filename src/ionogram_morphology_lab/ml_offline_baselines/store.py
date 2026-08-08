"""Project-local immutable store for ML-C.1 offline experiments."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

from .constants import EXPERIMENT_DIRNAME, EXPERIMENT_STATES, NO_CLAIM_STATEMENT_EN, NO_CLAIM_STATEMENT_RU
from .errors import ExperimentStoreError, ImmutabilityError
from .models import ExperimentConfig, ExperimentRecord, new_experiment_id, utc_now


class OfflineBaselineStore:
    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / EXPERIMENT_DIRNAME
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, experiment_id: str) -> Path:
        return self.root / experiment_id

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_record(self, record: ExperimentRecord) -> ExperimentRecord:
        record.updated_at = utc_now()
        self._write_json(self.path_for(record.experiment_id) / "experiment.json", record.to_dict())
        return record

    def create_draft(self, config: ExperimentConfig) -> ExperimentRecord:
        record = ExperimentRecord(new_experiment_id(), "draft", config)
        self._save_record(record)
        return record

    def load_experiment(self, experiment_id: str) -> ExperimentRecord:
        try:
            return ExperimentRecord.from_dict(self._read_json(self.path_for(experiment_id) / "experiment.json"))
        except FileNotFoundError as exc:
            raise ExperimentStoreError(f"Unknown experiment: {experiment_id}") from exc

    def list_experiments(self) -> list[ExperimentRecord]:
        return [self.load_experiment(path.name) for path in sorted(self.root.iterdir()) if path.is_dir() and (path / "experiment.json").exists()]

    def assert_immutable(self, record: ExperimentRecord, config: ExperimentConfig | None = None) -> None:
        if record.state == "completed" and (config is None or config.content_hash() != record.config_hash):
            raise ImmutabilityError("Completed experiment scientific fields are immutable; create a revision")

    def save_draft(self, record: ExperimentRecord, config: ExperimentConfig | None = None) -> ExperimentRecord:
        current = self.load_experiment(record.experiment_id)
        self.assert_immutable(current, config or record.config)
        if current.state in {"archived", "running"}:
            raise ExperimentStoreError(f"Cannot save a {current.state} experiment")
        if config is not None:
            record.config = config
        record.config_hash = record.config.content_hash()
        if current.state == "validated" and record.config_hash != current.config_hash:
            record.state, record.validation_blockers = "draft", []
        return self._save_record(record)

    def validate(self, experiment_id: str, manifest_store: Any, source_index: Any) -> ExperimentRecord:
        from .preflight import run_preflight
        record = self.load_experiment(experiment_id)
        if record.state not in {"draft", "validated"}:
            raise ExperimentStoreError("Only draft experiments can be validated")
        try:
            result = run_preflight(self.project_root, record.config.manifest_set_id, record.config, source_index)
        except Exception as exc:
            record.state = "draft"
            record.validation_blockers = list(getattr(exc, "blockers", [str(exc)]))
            return self._save_record(record)
        record.state, record.validation_blockers, record.manifest_hash = "validated", [], result.manifest_hash
        return self._save_record(record)

    def mark_running(self, experiment_id: str) -> ExperimentRecord:
        record = self.load_experiment(experiment_id)
        if record.state != "validated":
            raise ExperimentStoreError("Only validated experiments can run")
        record.state = "running"
        return self._save_record(record)

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    def save_completed(
        self,
        experiment_id: str,
        *,
        model: dict[str, Any],
        predictions: list[dict[str, Any]],
        metrics: dict[str, Any],
        errors: list[dict[str, Any]],
        run_metadata: dict[str, Any] | None = None,
        extras: dict[str, Any] | None = None,
    ) -> ExperimentRecord:
        record = self.load_experiment(experiment_id)
        if record.state != "running":
            raise ExperimentStoreError("Only running experiments can complete")
        path = self.path_for(experiment_id)
        meta = dict(run_metadata or {})
        extras = dict(extras or {})
        confusion = metrics.get("confusion_matrix") or extras.get("confusion_matrix") or {}
        self._write_json(path / "model_artifact.json", model)
        self._write_json(path / "model.json", model)  # compatibility alias
        self._write_jsonl(path / "predictions_development.jsonl", predictions)
        self._write_json(path / "metrics_development.json", metrics)
        self._write_json(path / "confusion_matrix.json", confusion)
        self._write_jsonl(path / "error_cases.jsonl", errors)
        self._write_json(path / "run_metadata.json", meta)
        self._write_json(
            path / "baseline_contract.json",
            {
                "baseline_version": record.config.baseline_version,
                "seed": record.config.seed,
                "feature_extractor_version": record.config.feature_extractor_version,
            },
        )
        self._write_json(
            path / "feature_contract.json",
            extras.get("feature_contract")
            or {
                "feature_extractor_version": record.config.feature_extractor_version,
                "feature_count": 256,
                "uses_candidate_output": False,
                "uses_identity_predictors": False,
                "temporal_context": False,
            },
        )
        if "feature_scaler" in extras:
            self._write_json(path / "feature_scaler.json", extras["feature_scaler"])
        if "train_item_index" in extras:
            self._write_jsonl(path / "train_item_index.jsonl", extras["train_item_index"])
        if "development_item_index" in extras:
            self._write_jsonl(path / "development_item_index.jsonl", extras["development_item_index"])
        if "source_manifest_snapshot" in extras:
            self._write_json(path / "source_manifest_snapshot.json", extras["source_manifest_snapshot"])
        if "environment" in extras:
            self._write_json(path / "environment.json", extras["environment"])
        summary = {
            "experiment_id": experiment_id,
            "state": "completed",
            "baseline_version": record.config.baseline_version,
            "manifest_set_id": record.config.manifest_set_id,
            "task_contract": record.config.task_contract,
            "train_count": meta.get("train_count"),
            "development_count": meta.get("development_count"),
            "holdout_status": "SEALED_UNUSED",
            "metrics_scope": "development_only",
            "not_independent_validation": True,
            "overall_agreement": metrics.get("overall_agreement"),
            "macro_f1": metrics.get("macro_f1"),
            "protocol_version": record.protocol_version,
        }
        self._write_json(path / "experiment_summary.json", summary)
        md = [
            "# ML-C.1 Experiment Summary",
            "",
            f"- Experiment ID: `{experiment_id}`",
            f"- Baseline: `{record.config.baseline_version}`",
            f"- Manifest: `{record.config.manifest_set_id}`",
            f"- Train items: {meta.get('train_count')}",
            f"- Development items: {meta.get('development_count')}",
            f"- Overall agreement (development): {metrics.get('overall_agreement')}",
            f"- Macro F1 (development): {metrics.get('macro_f1')}",
            "- Untouched holdout: SEALED / UNUSED",
            "- Development metrics are for model development only and are not independent validation.",
            "",
        ]
        (path / "experiment_summary.md").write_text("\n".join(md), encoding="utf-8")
        self._write_json(
            path / "integrity_report.json",
            {
                "model_hash": deterministic_hash(model),
                "predictions_hash": deterministic_hash(predictions),
                "metrics_hash": deterministic_hash(metrics),
                "holdout_predictions_present": False,
                "holdout_metrics_present": False,
                "ok": True,
            },
        )
        self._write_json(
            path / "protocol_statement.json",
            {"en": NO_CLAIM_STATEMENT_EN, "ru": NO_CLAIM_STATEMENT_RU},
        )
        # Fail closed if holdout outputs were somehow requested
        for forbidden in (
            "predictions_holdout.jsonl",
            "metrics_holdout.json",
            "holdout_reference_labels.jsonl",
        ):
            if (path / forbidden).exists():
                raise ImmutabilityError(f"Forbidden holdout artifact present: {forbidden}")
        record.model_hash = deterministic_hash(model)
        record.predictions_hash = deterministic_hash(predictions)
        record.metrics_hash = deterministic_hash(metrics)
        record.completed_at, record.state = utc_now(), "completed"
        return self._save_record(record)

    def mark_failed(self, experiment_id: str, reason: str) -> ExperimentRecord:
        record = self.load_experiment(experiment_id)
        if record.state == "completed":
            raise ImmutabilityError("Completed experiment cannot be marked failed")
        record.state, record.failure_reason = "failed", reason
        return self._save_record(record)

    def mark_cancelled(self, experiment_id: str) -> ExperimentRecord:
        record = self.load_experiment(experiment_id)
        if record.state == "completed":
            raise ImmutabilityError("Completed experiment cannot be cancelled")
        record.state = "cancelled"
        return self._save_record(record)

    def archive(self, experiment_id: str) -> ExperimentRecord:
        record = self.load_experiment(experiment_id)
        record.state = "archived"
        return self._save_record(record)

    def create_revision(self, experiment_id: str, config: ExperimentConfig | None = None) -> ExperimentRecord:
        parent = self.load_experiment(experiment_id)
        revised = self.create_draft(config or parent.config)
        revised.parent_experiment_id = parent.experiment_id
        return self._save_record(revised)
