"""Persistable ML-C.1 experiment records."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

from .constants import FEATURE_EXTRACTOR_VERSION, OFFLINE_BASELINE_PROTOCOL_VERSION


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_experiment_id() -> str:
    return f"mlc_{uuid4().hex[:12]}"


def _from_dict(cls: type, data: dict[str, Any]) -> Any:
    known = {item.name for item in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in known})


@dataclass
class ExperimentConfig:
    title: str
    analyst: str
    manifest_set_id: str
    task_contract: str
    baseline_version: str
    feature_extractor_version: str = FEATURE_EXTRACTOR_VERSION
    seed: int = 0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentConfig":
        return _from_dict(cls, data)

    def content_hash(self) -> str:
        return deterministic_hash(self.to_dict())


@dataclass
class ExperimentRecord:
    experiment_id: str
    state: str
    config: ExperimentConfig
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    parent_experiment_id: str = ""
    validation_blockers: list[str] = field(default_factory=list)
    config_hash: str = ""
    manifest_hash: str = ""
    model_hash: str = ""
    predictions_hash: str = ""
    metrics_hash: str = ""
    completed_at: str = ""
    failure_reason: str = ""
    protocol_version: str = OFFLINE_BASELINE_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if not self.config_hash:
            self.config_hash = self.config.content_hash()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["config"] = self.config.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRecord":
        payload = dict(data)
        payload["config"] = ExperimentConfig.from_dict(payload["config"])
        return _from_dict(cls, payload)
