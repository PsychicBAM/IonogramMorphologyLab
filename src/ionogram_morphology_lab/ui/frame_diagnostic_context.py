"""Immutable frame identity for Feature Diagnostics (Phase 4B.2f)."""

from __future__ import annotations

import itertools
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from ionogram_morphology_lab.cache.v2_feature_cache import V2CacheKey, make_cache_key
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION

_GEN = itertools.count(1)


def next_request_generation_id() -> str:
    return f"fd-{next(_GEN)}-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class FrameDiagnosticContext:
    """Single source of truth for frame/source identity of a load or V2 job."""

    source_mat_path: str
    source_sha256: str
    frame_index: int
    interpreted_time: str
    raw_frame_sha256: str
    profile_id: str
    signal_contract_id: str
    feature_version: str
    cache_key_digest: str
    request_generation_id: str
    n_frames: int = 1440

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def matches(self, other: FrameDiagnosticContext | None) -> bool:
        if other is None:
            return False
        return (
            self.request_generation_id == other.request_generation_id
            and self.source_sha256 == other.source_sha256
            and self.frame_index == other.frame_index
            and self.source_mat_path == other.source_mat_path
            and self.profile_id == other.profile_id
            and self.signal_contract_id == other.signal_contract_id
            and self.feature_version == other.feature_version
            and self.raw_frame_sha256 == other.raw_frame_sha256
        )

    def identity_matches_without_generation(self, other: FrameDiagnosticContext | None) -> bool:
        """Compare scientific identity ignoring request generation (for cache reuse)."""
        if other is None:
            return False
        return (
            self.source_sha256 == other.source_sha256
            and self.frame_index == other.frame_index
            and self.source_mat_path == other.source_mat_path
            and self.profile_id == other.profile_id
            and self.signal_contract_id == other.signal_contract_id
            and self.feature_version == other.feature_version
        )


def build_frame_context(
    *,
    mat_path: str,
    source_sha256: str,
    frame_index: int,
    interpreted_time: str,
    raw_frame_sha256: str,
    profile_id: str,
    signal_contract_id: str,
    profile: dict[str, Any] | None = None,
    n_frames: int = 1440,
    request_generation_id: str | None = None,
    feature_version: str = FEATURE_VERSION,
) -> FrameDiagnosticContext:
    key = make_cache_key(
        source_mat_sha256=source_sha256,
        frame_index=int(frame_index),
        profile_id=profile_id,
        signal_contract_id=signal_contract_id,
        profile=profile,
        feature_version=feature_version,
    )
    return FrameDiagnosticContext(
        source_mat_path=str(mat_path),
        source_sha256=source_sha256,
        frame_index=int(frame_index),
        interpreted_time=interpreted_time or "—",
        raw_frame_sha256=raw_frame_sha256 or "",
        profile_id=str(profile_id or ""),
        signal_contract_id=str(signal_contract_id or ""),
        feature_version=feature_version,
        cache_key_digest=key.digest(),
        request_generation_id=request_generation_id or next_request_generation_id(),
        n_frames=int(n_frames),
    )


def cache_key_from_context(ctx: FrameDiagnosticContext, profile: dict[str, Any] | None = None) -> V2CacheKey:
    return make_cache_key(
        source_mat_sha256=ctx.source_sha256,
        frame_index=ctx.frame_index,
        profile_id=ctx.profile_id,
        signal_contract_id=ctx.signal_contract_id,
        profile=profile,
        feature_version=ctx.feature_version,
    )


# Terminal job states required by Phase 4B.2f
JOB_STATES = (
    "idle",
    "loading_frame",
    "checking_cache",
    "loaded_from_cache",
    "computing",
    "rendering",
    "saving_cache",
    "completed",
    "cancelled",
    "failed",
)
TERMINAL_JOB_STATES = frozenset({"completed", "cancelled", "failed"})
