"""Fail-closed controls that prevent ML-C.1 from accessing holdout labels."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .constants import HOLDOUT_REFERENCE_FILENAME
from .errors import ProtocolViolation

_LOG = logging.getLogger(__name__)


class HoldoutAccessGuard:
    """Tracks attempted holdout-reference access; ML-C.1 never permits it."""

    def __init__(self) -> None:
        self.holdout_reference_opened = False
        self.blocked_paths: list[str] = []

    def record_blocked(self, path: Path | str) -> None:
        self.holdout_reference_opened = True
        self.blocked_paths.append(str(path))

    def assert_clean(self) -> None:
        if self.holdout_reference_opened:
            raise ProtocolViolation("Holdout reference access was attempted")


def forbid_holdout_reference_path(path: Path | str, guard: HoldoutAccessGuard | None = None) -> None:
    """Reject the sealed reference-label file by basename, before opening it."""
    if Path(path).name == HOLDOUT_REFERENCE_FILENAME:
        if guard:
            guard.record_blocked(path)
        _LOG.error("Blocked ML-C.1 holdout reference access: %s", path)
        raise ProtocolViolation("Holdout reference labels are sealed for ML-C.1")


@contextmanager
def safe_open_text(path: Path | str, *, guard: HoldoutAccessGuard | None = None) -> Iterator[Any]:
    """Open UTF-8 text only after enforcing the sealed-label firewall."""
    forbid_holdout_reference_path(path, guard)
    with Path(path).open("r", encoding="utf-8") as handle:
        yield handle


def assert_role_allowed_for_mlc(role: str) -> None:
    if role not in {"train", "development"}:
        raise ProtocolViolation(f"ML-C.1 role is forbidden: {role!r}")


def assert_no_holdout_items(items: list[Any]) -> None:
    for item in items:
        role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
        if role == "untouched_holdout":
            raise ProtocolViolation("Untouched holdout item supplied to ML-C.1")


def aggregate_holdout_metadata(
    manifest_set: Any, public_count: int, group_count: int
) -> dict[str, Any]:
    """Return holdout aggregates only; labels and item identities are excluded."""
    get = lambda key, default="": (
        manifest_set.get(key, default) if isinstance(manifest_set, dict)
        else getattr(manifest_set, key, default)
    )
    return {
        "public_item_count": int(public_count),
        "group_count": int(group_count),
        "public_manifest_hash": get("holdout_public_manifest_hash"),
        "reference_labels_hash": get("holdout_reference_labels_hash"),
        "lock_hash": get("holdout_lock_hash"),
        "sealed": bool(get("holdout_sealed", False)),
        "lock_state": "sealed" if get("holdout_sealed", False) else "unsealed",
    }
