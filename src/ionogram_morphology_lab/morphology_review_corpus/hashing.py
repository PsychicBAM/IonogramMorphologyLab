"""Deterministic hashing and portable path helpers for review corpora."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_ABS_WIN = re.compile(r"^[A-Za-z]:[\\/]")
_ABS_UNIX = re.compile(r"^/")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest().lower()


def validate_sha256(value: str) -> str:
    if not value or not _SHA_RE.match(value):
        raise ValueError(f"Invalid SHA-256: {value!r}")
    return value.lower()


def is_absolute_local_path(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    if _ABS_WIN.match(value) or (value.startswith("/") and not value.startswith("//")):
        return True
    if value.startswith("\\\\") or value.startswith("//"):
        return True
    try:
        return Path(value).is_absolute()
    except (OSError, ValueError):
        return False


def assert_no_absolute_paths(payload: Any, *, path: str = "root") -> None:
    if isinstance(payload, dict):
        for k, v in payload.items():
            assert_no_absolute_paths(v, path=f"{path}.{k}")
    elif isinstance(payload, list):
        for i, v in enumerate(payload):
            assert_no_absolute_paths(v, path=f"{path}[{i}]")
    elif isinstance(payload, str) and is_absolute_local_path(payload):
        # Allow only non-path-looking strings; reject drive/UNC paths
        if any(sep in payload for sep in ("\\", "/")) and (
            _ABS_WIN.match(payload) or payload.startswith("\\\\") or payload.startswith("//")
        ):
            raise ValueError(f"Absolute local path forbidden at {path}: {payload!r}")
