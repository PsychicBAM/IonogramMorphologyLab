"""Fail-closed ML-C.1 preflight checks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.ml_dataset_manifests.models import HoldoutLockRecord
from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

from .constants import FEATURE_EXTRACTOR_VERSION
from .errors import PreflightError
from .holdout_firewall import assert_no_holdout_items, assert_role_allowed_for_mlc, safe_open_text
from .tasks import task_supported


@dataclass
class PreflightResult:
    ok: bool
    blockers: list[str] = field(default_factory=list)
    train_items: list[dict[str, Any]] = field(default_factory=list)
    development_items: list[dict[str, Any]] = field(default_factory=list)
    manifest_hash: str = ""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with safe_open_text(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_preflight(
    project_root: Path | str, manifest_set_id: str, config: Any, source_index: Any
) -> PreflightResult:
    """Validate frozen manifests and source availability without reading holdout rows."""
    root = Path(project_root)
    store = MLDatasetManifestStore(root)
    blockers: list[str] = []
    try:
        manifest = store.load_manifest_set(manifest_set_id)
    except Exception as exc:
        raise PreflightError([f"manifest_load_failed:{exc}"]) from exc
    directory = store.path_for(manifest_set_id)
    if manifest.lifecycle_state != "frozen":
        blockers.append("manifest_not_frozen")
    if not manifest.holdout_sealed:
        blockers.append("holdout_not_sealed")
    if config.manifest_set_id != manifest_set_id:
        blockers.append("config_manifest_set_mismatch")
    if not task_supported(config.task_contract) or config.task_contract != manifest.task_contract:
        blockers.append("unsupported_or_mismatched_task_contract")
    if config.feature_extractor_version != FEATURE_EXTRACTOR_VERSION:
        blockers.append("unsupported_feature_extractor")
    lock_path = directory / "holdout_lock.json"
    if not lock_path.exists():
        blockers.append("missing_holdout_lock")
    else:
        try:
            lock = HoldoutLockRecord.from_dict(json.loads(lock_path.read_text(encoding="utf-8")))
            if lock.compute_lock_hash() != lock.lock_hash or lock.lock_hash != manifest.holdout_lock_hash:
                blockers.append("holdout_lock_hash_mismatch")
        except Exception:
            blockers.append("invalid_holdout_lock")
    train_path, dev_path = directory / "train_manifest.jsonl", directory / "development_manifest.jsonl"
    if not train_path.exists():
        blockers.append("missing_train_manifest")
    if not dev_path.exists():
        blockers.append("missing_development_manifest")
    train = _read_jsonl(train_path) if train_path.exists() else []
    dev = _read_jsonl(dev_path) if dev_path.exists() else []
    try:
        assert_no_holdout_items(train + dev)
        for row in train:
            assert_role_allowed_for_mlc(row.get("role", ""))
        for row in dev:
            assert_role_allowed_for_mlc(row.get("role", ""))
    except Exception as exc:
        blockers.append(f"role_violation:{exc}")
    if not train:
        blockers.append("empty_train_manifest")
    if not dev:
        blockers.append("empty_development_manifest")
    if len({row.get("target_label") or row.get("morphology") for row in train if row.get("target_label") or row.get("morphology")}) < 2:
        blockers.append("fewer_than_two_train_classes")
    train_ids = {row.get("item_id") for row in train}
    dev_ids = {row.get("item_id") for row in dev}
    if train_ids & dev_ids:
        blockers.append("train_development_item_overlap")
    train_groups = {row.get("atomic_group_id") for row in train if row.get("atomic_group_id")}
    dev_groups = {row.get("atomic_group_id") for row in dev if row.get("atomic_group_id")}
    if train_groups & dev_groups:
        blockers.append("train_development_atomic_group_overlap")
    train_seqs = {row.get("sequence_id") for row in train if row.get("sequence_id")}
    dev_seqs = {row.get("sequence_id") for row in dev if row.get("sequence_id")}
    if train_seqs & dev_seqs:
        blockers.append("train_development_sequence_overlap")
    # Holdout reference labels must remain sealed — never open that file here.
    if (directory / "holdout_reference_labels.jsonl").exists():
        # Presence is required for frozen ML-B, but ML-C must not read it.
        pass
    for row in train + dev:
        try:
            source_index.resolve(row["source_sha256"])
        except Exception:
            blockers.append(f"unresolvable_source_sha:{row.get('source_sha256', '')}")
    # Deduplicate blockers while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    blockers = uniq
    result = PreflightResult(not blockers, blockers, train, dev, manifest.manifest_set_hash)
    if blockers:
        raise PreflightError(blockers)
    return result
