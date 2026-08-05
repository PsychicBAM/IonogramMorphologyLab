"""Owner-review label schema with independent taxonomy axes."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

MorphologyToken = Literal[
    "clean",
    "diffuse_unspecified",
    "frequency_spread",
    "range_spread",
    "mixed_spread",
    "interference_limited",
    "not_assessable",
    "indeterminate",
]

ReviewState = Literal["unverified", "owner-reviewed", "expert-confirmed"]

MORPHOLOGY_VALUES: tuple[str, ...] = (
    "clean",
    "diffuse_unspecified",
    "frequency_spread",
    "range_spread",
    "mixed_spread",
    "interference_limited",
    "not_assessable",
    "indeterminate",
)

REVIEW_STATE_VALUES: tuple[str, ...] = (
    "unverified",
    "owner-reviewed",
    "expert-confirmed",
)

_ISO_DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")


class ReviewLabelValidationError(ValueError):
    """Raised when a review label fails schema validation."""


@dataclass
class ReviewLabel:
    """Human review label for a single ionogram frame (owner-review by default)."""

    morphology: MorphologyToken
    layer: str
    interference: str
    ambiguity: str
    quality: str
    reviewer: str
    date: str
    source_frame_id: str
    source_file: str
    source_sha256: str
    review_state: ReviewState = "owner-reviewed"
    label_id: str = ""
    explanation: str = ""
    uncertainty: str = ""
    alternatives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewLabel":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = {k: v for k, v in data.items() if k in known}
        label = cls(**payload)
        validate_review_label(label)
        return label


def validate_review_label(label: ReviewLabel) -> None:
    """Validate morphology, review_state, ISO date, and source hash."""
    if label.morphology not in MORPHOLOGY_VALUES:
        raise ReviewLabelValidationError(f"Invalid morphology token: {label.morphology!r}")
    if label.review_state not in REVIEW_STATE_VALUES:
        raise ReviewLabelValidationError(f"Invalid review_state: {label.review_state!r}")
    if not _ISO_DATE_RE.match(label.date.strip()):
        raise ReviewLabelValidationError(f"date must be ISO-8601: {label.date!r}")
    if not _SHA256_RE.match(label.source_sha256.strip()):
        raise ReviewLabelValidationError("source_sha256 must be a 64-char hex digest")
    for axis in ("layer", "interference", "ambiguity", "quality"):
        value = getattr(label, axis)
        if not isinstance(value, str) or not value.strip():
            raise ReviewLabelValidationError(f"{axis} must be a non-empty string token")
    if not label.source_frame_id.strip():
        raise ReviewLabelValidationError("source_frame_id must be non-empty")
    if not label.source_file.strip():
        raise ReviewLabelValidationError("source_file must be non-empty")
    if not label.reviewer.strip():
        raise ReviewLabelValidationError("reviewer must be non-empty")
    if not isinstance(label.alternatives, list) or not all(
        isinstance(item, str) for item in label.alternatives
    ):
        raise ReviewLabelValidationError("alternatives must be a list of strings")


def new_label_id(source_sha256: str, source_frame_id: str) -> str:
    """Generate a filesystem-safe label id."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha_short = source_sha256.lower()[:12]
    frame_safe = re.sub(r"[^\w.-]+", "_", source_frame_id.strip())[:48]
    return f"{sha_short}_{frame_safe}_{ts}"
