"""Append-only development exposure ledger."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .constants import EXPERIMENT_DIRNAME
from .errors import ProtocolViolation
from .holdout_firewall import assert_role_allowed_for_mlc


def append_exposure(
    project_root: Path | str,
    experiment_id: str,
    role: str,
    item_ids: list[str],
    timestamp: str | None = None,
) -> Path:
    """Append development exposure metadata. Holdout items cannot be recorded."""
    assert_role_allowed_for_mlc(role)
    if role == "untouched_holdout":
        raise ProtocolViolation("Holdout exposure cannot be recorded by ML-C.1")
    path = Path(project_root) / EXPERIMENT_DIRNAME / "exposure_ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experiment_id": experiment_id,
        "role": role,
        "item_ids": sorted(str(item_id) for item_id in item_ids),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path
