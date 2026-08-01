from __future__ import annotations

import csv

import numpy as np

from ionogram_morphology_lab.classifiers.model_lab import ModelLab, _group_split_by_date


def test_grouped_split_by_date_prevents_neighbor_leakage():
    dates = ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]
    train, test = _group_split_by_date(dates, np.array(["a", "a", "b", "b"], dtype=object), seed=1)
    train_dates = {dates[i] for i in train}
    test_dates = {dates[i] for i in test}
    assert train_dates.isdisjoint(test_dates)


def test_model_lab_trains_tiny_csv_and_marks_research_only(tmp_path):
    csv_path = tmp_path / "features.csv"
    rows = [
        {"date": "2024-01-01", "frame_id": "1", "f1": "0.0", "f2": "0.1", "label": "a"},
        {"date": "2024-01-01", "frame_id": "2", "f1": "0.1", "f2": "0.0", "label": "a"},
        {"date": "2024-01-02", "frame_id": "1", "f1": "1.0", "f2": "1.1", "label": "b"},
        {"date": "2024-01-02", "frame_id": "2", "f1": "1.1", "f2": "1.0", "label": "b"},
        {"date": "2024-01-03", "frame_id": "1", "f1": "0.2", "f2": "0.2", "label": "a"},
        {"date": "2024-01-03", "frame_id": "2", "f1": "1.2", "f2": "1.2", "label": "b"},
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    lab = ModelLab(tmp_path / "lab")
    dataset = lab.import_labeled_csv(csv_path)
    card = lab.train(dataset, kind="logistic_regression", model_id="tiny")
    assert card.status == "development"
    assert any("research use only" in note.lower() for note in card.limitations)
