"""Filesystem-backed owner-review label store."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.security import ForbiddenPathError, default_blocklist
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir, resolve_under

from .schema import ReviewLabel, ReviewLabelValidationError, new_label_id, validate_review_label

# Article 3 blinded study paths are always refused for review labels.
ARTICLE3_PATH_FRAGMENTS: tuple[str, ...] = (
    "04_article_3_dawn_dusk_solar_terminator",
    "09_blinded_review_package",
    "11_rendered_frames",
    "12_rendered_contact_sheets",
    "21_review_progress",
    "20_blinded_review_app",
)

WORKSPACE_README = """# Owner-review dataset

This workspace stores **owner-review** morphology labels for approved, non-blinded
ionogram sources. Labels are recorded with separate taxonomy axes (morphology, layer,
interference, ambiguity, quality) and remain **owner-review** until an expert marks
them `expert-confirmed`.

## Governance

- Do **not** import or label Article 3 blinded study materials here.
- Use approved synthetic data, teaching examples, or explicitly permitted MAT sources.
- Exports are for local research workflow only until external validation is complete.

## Layout

- `index.json` — dataset index and label id list
- `labels/` — one JSON file per label
"""

INDEX_VERSION = "1.0"


class ReviewDatasetSourceError(PermissionError):
    """Raised when a label references a forbidden or Article 3 source."""


def review_dataset_root(root: Path | str | None = None) -> Path:
    return ensure_dir(root or (app_root() / "review_dataset"))


def _is_article3_path(path: Path | str) -> bool:
    try:
        resolved = str(Path(path).resolve()).replace("/", "\\").lower()
    except OSError:
        resolved = str(path).replace("/", "\\").lower()
    return any(fragment.replace("/", "\\").lower() in resolved for fragment in ARTICLE3_PATH_FRAGMENTS)


def assert_allowed_review_source(path: Path | str, file_sha256: str | None = None) -> Path:
    """Reject Article 3 blinded paths and honor optional project protection."""
    p = Path(path)
    if _is_article3_path(p):
        raise ReviewDatasetSourceError(
            "Article 3 blinded study paths cannot be used in the owner-review dataset."
        )
    try:
        default_blocklist().assert_allowed(p, file_sha256=file_sha256)
    except ForbiddenPathError as exc:
        raise ReviewDatasetSourceError(str(exc)) from exc
    return p


class ReviewDatasetStore:
    """JSON-per-label store rooted at `app_root()/review_dataset/` by default."""

    def __init__(self, root: Path | str | None = None):
        self.root = review_dataset_root(root)
        self.labels_dir = ensure_dir(self.root / "labels")
        self.index_path = self.root / "index.json"

    def ensure_layout(self, *, write_readme: bool = True) -> Path:
        ensure_dir(self.labels_dir)
        if not self.index_path.exists():
            self._write_index({"schema_version": INDEX_VERSION, "label_ids": []})
        if write_readme:
            readme = self.root / "README.md"
            if not readme.exists():
                readme.write_text(WORKSPACE_README, encoding="utf-8")
        return self.root

    def add_label(self, label: ReviewLabel) -> Path:
        validate_review_label(label)
        assert_allowed_review_source(label.source_file, file_sha256=label.source_sha256)
        if not label.label_id:
            label.label_id = new_label_id(label.source_sha256, label.source_frame_id)
        path = resolve_under(self.labels_dir, f"{label.label_id}.json")
        path.write_text(
            json.dumps(label.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        index = self._read_index()
        ids = list(index.get("label_ids", []))
        if label.label_id not in ids:
            ids.append(label.label_id)
        index["label_ids"] = ids
        self._write_index(index)
        return path

    def list_labels(
        self,
        *,
        source_sha256: str | None = None,
        source_frame_id: str | None = None,
        review_state: str | None = None,
    ) -> list[ReviewLabel]:
        labels: list[ReviewLabel] = []
        for path in sorted(self.labels_dir.glob("*.json")):
            try:
                label = ReviewLabel.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ReviewLabelValidationError, TypeError, ValueError):
                continue
            if source_sha256 and label.source_sha256.lower() != source_sha256.lower():
                continue
            if source_frame_id and label.source_frame_id != source_frame_id:
                continue
            if review_state and label.review_state != review_state:
                continue
            labels.append(label)
        return labels

    def load_by_source(self, source_sha256: str, source_frame_id: str) -> list[ReviewLabel]:
        return self.list_labels(source_sha256=source_sha256, source_frame_id=source_frame_id)

    def export_json(self, path: Path | str) -> Path:
        out = Path(path)
        ensure_dir(out.parent)
        payload = [label.to_dict() for label in self.list_labels()]
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def export_csv(self, path: Path | str) -> Path:
        out = Path(path)
        ensure_dir(out.parent)
        rows = self.list_labels()
        fieldnames = [
            "label_id",
            "morphology",
            "layer",
            "interference",
            "ambiguity",
            "quality",
            "reviewer",
            "date",
            "source_frame_id",
            "source_file",
            "source_sha256",
            "review_state",
            "explanation",
            "uncertainty",
            "alternatives",
        ]
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for label in rows:
                row = label.to_dict()
                row["alternatives"] = "|".join(label.alternatives)
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        return out

    def _read_index(self) -> dict[str, Any]:
        self.ensure_layout(write_readme=False)
        if not self.index_path.exists():
            return {"schema_version": INDEX_VERSION, "label_ids": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _write_index(self, index: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        index.setdefault("schema_version", INDEX_VERSION)
        if "created_at" not in index:
            index["created_at"] = now
        index["updated_at"] = now
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
