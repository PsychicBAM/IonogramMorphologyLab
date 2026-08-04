from __future__ import annotations

import csv
import json

import pytest

from ionogram_morphology_lab.review_dataset import (
    ReviewDatasetSourceError,
    ReviewDatasetStore,
    ReviewLabel,
    ReviewLabelValidationError,
    validate_review_label,
)

_SHA = "a" * 64
_APPROVED_SOURCE = r"E:\ionog\conference_presentation\IonogramMorphologyLab\synthetic_data\demo.mat"
_ARTICLE3_SOURCE = (
    r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator"
    r"\11_rendered_frames\frame.png"
)


def _sample_label(**overrides) -> ReviewLabel:
    payload = {
        "morphology": "clean",
        "layer": "F2",
        "interference": "none",
        "ambiguity": "no_visible_ambiguity",
        "quality": "valid",
        "reviewer": "owner",
        "date": "2026-08-01T12:00:00Z",
        "source_frame_id": "f0042",
        "source_file": _APPROVED_SOURCE,
        "source_sha256": _SHA,
        "review_state": "owner-reviewed",
        "explanation": "Clear F2 trace without spread.",
        "uncertainty": "low",
        "alternatives": ["frequency_spread"],
    }
    payload.update(overrides)
    return ReviewLabel(**payload)


def test_validate_review_label_rejects_invalid_morphology():
    label = _sample_label(morphology="not_a_token")  # type: ignore[arg-type]
    with pytest.raises(ReviewLabelValidationError, match="morphology"):
        validate_review_label(label)


def test_validate_review_label_rejects_bad_date():
    label = _sample_label(date="02/08/2026")
    with pytest.raises(ReviewLabelValidationError, match="ISO"):
        validate_review_label(label)


def test_add_list_export_roundtrip(tmp_path):
    store = ReviewDatasetStore(tmp_path / "review_dataset")
    store.ensure_layout(write_readme=True)
    label = _sample_label()
    saved = store.add_label(label)
    assert saved.exists()

    listed = store.list_labels()
    assert len(listed) == 1
    assert listed[0].morphology == "clean"
    assert listed[0].label_id

    by_source = store.load_by_source(_SHA, "f0042")
    assert len(by_source) == 1
    assert by_source[0].source_frame_id == "f0042"

    json_path = tmp_path / "export.json"
    store.export_json(json_path)
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(exported) == 1
    assert exported[0]["morphology"] == "clean"

    csv_path = tmp_path / "export.csv"
    store.export_csv(csv_path)
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["alternatives"] == "frequency_spread"
    assert rows[0]["review_state"] == "owner-reviewed"


def test_article3_source_is_refused(tmp_path):
    store = ReviewDatasetStore(tmp_path / "review_dataset")
    label = _sample_label(source_file=_ARTICLE3_SOURCE)
    with pytest.raises(ReviewDatasetSourceError, match="Article 3"):
        store.add_label(label)


def test_init_layout_creates_index_and_readme(tmp_path):
    store = ReviewDatasetStore(tmp_path / "review_dataset")
    store.ensure_layout()
    assert store.index_path.exists()
    index = json.loads(store.index_path.read_text(encoding="utf-8"))
    assert index["label_ids"] == []
    readme = store.root / "README.md"
    assert readme.exists()
    assert "owner-review" in readme.read_text(encoding="utf-8").lower()
