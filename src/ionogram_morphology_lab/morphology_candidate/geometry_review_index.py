"""Geometry-review logical identity, supersession, and corpus counts (Phase 4C.1b).

Does not modify scientific content of existing review records. Groups duplicate
saves of the same logical identity and marks the newest as current.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

MappingLike = dict[str, Any]


def geometry_reviews_dir(project_root: Path | str) -> Path:
    return Path(project_root) / "feature_diagnostics" / "geometry_reviews"


def logical_identity(review: MappingLike) -> tuple[str, str, int, str, str]:
    """(review_kind, source_sha256, frame_index, feature_version, diagnostics_cache_id)."""
    return (
        str(review.get("review_kind") or "geometry_only"),
        str(review.get("source_sha256") or ""),
        int(review.get("frame_index") or 0),
        str(review.get("feature_version") or ""),
        str(review.get("diagnostics_cache_id") or ""),
    )


def _parse_ts(review: MappingLike, path: Path | None = None) -> float:
    for key in ("updated_at", "created_at", "reviewed_at", "timestamp"):
        raw = review.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
    if path is not None and path.is_file():
        return path.stat().st_mtime
    return 0.0


@dataclass
class GeometryReviewRecord:
    path: Path
    data: dict[str, Any]
    identity: tuple[str, str, int, str, str]
    mtime: float
    is_current: bool = False
    supersedes: str | None = None
    revision: int = 1


@dataclass
class GeometryReviewCorpus:
    files_found: int = 0
    logical_reviewed_frames: int = 0  # unique (source_sha, frame_index) among current
    current_reviews: int = 0  # unique full logical identities currently active
    superseded_reviews: int = 0
    records: list[GeometryReviewRecord] = field(default_factory=list)
    current_by_identity: dict[tuple, GeometryReviewRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_files_found": self.files_found,
            "logical_reviewed_frames": self.logical_reviewed_frames,
            "current_reviews": self.current_reviews,
            "superseded_reviews": self.superseded_reviews,
            "note": (
                "logical_reviewed_frames counts unique (source_sha256, frame_index) among current "
                "reviews; superseded files are history for the same full identity "
                "(kind, sha, frame, feature_version, diagnostics_cache_id)."
            ),
            "current": [
                {
                    "file": r.path.name,
                    "source_sha256": r.identity[1],
                    "frame_index": r.identity[2],
                    "diagnostics_cache_id": r.identity[4],
                    "feature_version": r.identity[3],
                    "status": r.data.get("status"),
                    "revision": r.revision,
                    "is_current": True,
                }
                for r in self.current_by_identity.values()
            ],
            "superseded": [
                {
                    "file": r.path.name,
                    "source_sha256": r.identity[1],
                    "frame_index": r.identity[2],
                    "diagnostics_cache_id": r.identity[4],
                    "is_current": False,
                    "superseded_by": r.supersedes,
                    "revision": r.revision,
                }
                for r in self.records
                if not r.is_current
            ],
        }


def load_geometry_review_corpus(project_root: Path | str) -> GeometryReviewCorpus:
    """Group review files by logical identity; newest is current, older are history."""
    d = geometry_reviews_dir(project_root)
    corpus = GeometryReviewCorpus()
    if not d.is_dir():
        return corpus

    loaded: list[GeometryReviewRecord] = []
    for p in sorted(d.glob("review_f*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        ident = logical_identity(data)
        loaded.append(
            GeometryReviewRecord(
                path=p,
                data=data,
                identity=ident,
                mtime=_parse_ts(data, p),
            )
        )
    corpus.files_found = len(loaded)

    by_id: dict[tuple, list[GeometryReviewRecord]] = {}
    for rec in loaded:
        by_id.setdefault(rec.identity, []).append(rec)

    for ident, group in by_id.items():
        group.sort(key=lambda r: r.mtime)
        for i, rec in enumerate(group, start=1):
            rec.revision = i
            rec.is_current = i == len(group)
            if not rec.is_current:
                rec.supersedes = group[-1].path.name
        corpus.current_by_identity[ident] = group[-1]
        corpus.records.extend(group)

    # Logical frames: unique (source_sha, frame_index) among current reviews
    frames = {(r.identity[1], r.identity[2]) for r in corpus.current_by_identity.values()}
    corpus.logical_reviewed_frames = len(frames)
    corpus.current_reviews = len(corpus.current_by_identity)
    corpus.superseded_reviews = sum(1 for r in corpus.records if not r.is_current)
    return corpus


def save_geometry_review_update_in_place(
    project_root: Path | str,
    review: dict[str, Any],
) -> Path:
    """Update-in-place: one current file per logical identity; keep older files as history.

    Writes/overwrites the canonical current filename for the identity. Does not delete
    prior files (they remain as superseded history when corpus is loaded).
    """
    from datetime import timezone

    out = geometry_reviews_dir(project_root)
    out.mkdir(parents=True, exist_ok=True)
    data = dict(review)
    data.setdefault("review_kind", "geometry_only")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "created_at" not in data:
        data["created_at"] = data["updated_at"]
    data["is_current"] = True
    frame = int(data.get("frame_index") or 0)
    digest = str(data.get("diagnostics_cache_id") or "na")[:12]
    path = out / f"review_f{frame:04d}_{digest}.json"

    # If an older distinct file exists for same identity with different name, leave it.
    corpus = load_geometry_review_corpus(project_root)
    ident = logical_identity(data)
    prev = corpus.current_by_identity.get(ident)
    if prev is not None and prev.path.resolve() != path.resolve():
        data["supersedes_review_file"] = prev.path.name
        data["revision"] = int(prev.revision) + 1
    else:
        data["revision"] = int(data.get("revision") or 1)

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
