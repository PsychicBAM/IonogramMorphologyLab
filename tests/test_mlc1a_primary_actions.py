"""ML-C.1a — primary workflow actions and completed-experiment UX."""
from __future__ import annotations

from pathlib import Path

import pytest

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_offline_baselines.constants import (
    BASELINE_MAJORITY,
    OFFLINE_BASELINE_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_offline_baselines.models import ExperimentConfig
from ionogram_morphology_lab.ml_offline_baselines.store import OfflineBaselineStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from ionogram_morphology_lab.ui.ml_offline_baselines_page import MLOfflineBaselinesPage
from tests.mlc1_fixtures import build_mlc1_fixture


class _Sess:
    def __init__(self, root: Path) -> None:
        self.project_path = root
        self.active_project_path = root


@pytest.fixture
def page(qtbot, tmp_path: Path):
    root, mid, _index, _r, manifests = build_mlc1_fixture(tmp_path)
    i18n = I18n()
    i18n.set_language("en")
    p = MLOfflineBaselinesPage(_Sess(root), i18n)
    qtbot.addWidget(p)
    p.on_project_changed()
    p._manifest.setCurrentIndex(p._manifest.findData(mid))
    return p, root, mid, manifests


def test_build_identity_mlc1a():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-C.1b"
    assert info["ml_offline_baseline_protocol_version"] == OFFLINE_BASELINE_PROTOCOL_VERSION


def test_draft_shows_validate_and_disabled_run(page):
    p, root, mid, _ = page
    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "draft_a",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=1,
        )
    )
    p._refresh_experiments(prefer=draft.experiment_id)
    p._load(draft.experiment_id)
    assert not p._btn_validate.isHidden()
    assert not p._btn_run.isHidden()
    assert p._btn_validate.isEnabled()
    assert not p._btn_run.isEnabled()


def test_validated_enables_run(page):
    p, root, mid, manifests = page
    from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
        build_index_from_directory,
    )

    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "draft_b",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=1,
        )
    )
    index = build_index_from_directory(root)
    assert store.validate(draft.experiment_id, manifests, index).state == "validated"
    p._refresh_experiments(prefer=draft.experiment_id)
    p._load(draft.experiment_id)
    assert not p._btn_run.isHidden()
    assert p._btn_run.isEnabled()
    assert not p._btn_validate.isHidden()


def test_completed_shows_new_and_export_not_run(page):
    p, root, mid, manifests = page
    from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
    from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
        build_index_from_directory,
    )

    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "done_a",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=2,
        )
    )
    index = build_index_from_directory(root)
    store.validate(draft.experiment_id, manifests, index)
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    assert completed.state == "completed"
    p._refresh_experiments(prefer=completed.experiment_id)
    p._load(completed.experiment_id)
    assert not p._btn_new.isHidden()
    assert not p._btn_export.isHidden()
    assert p._btn_run.isHidden()
    assert p._btn_validate.isHidden()
    assert not p._immutable.isHidden()
    assert "immutable" in p._immutable.text().lower() or "неизменяем" in p._immutable.text().lower()


def test_new_experiment_selects_draft(page):
    p, root, mid, manifests = page
    from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
    from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
        build_index_from_directory,
    )

    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "done_b",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=3,
        )
    )
    index = build_index_from_directory(root)
    store.validate(draft.experiment_id, manifests, index)
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    p._refresh_experiments(prefer=completed.experiment_id)
    p._load(completed.experiment_id)
    assert p._current_id == completed.experiment_id
    p._create_draft()
    assert p._current_id != completed.experiment_id
    record = store.load_experiment(p._current_id)
    assert record.state == "draft"
    assert not p._btn_validate.isHidden()
    assert not p._btn_run.isHidden()
    assert not p._btn_run.isEnabled()
    from PySide6.QtCore import Qt

    cur = p._experiments.currentItem()
    assert cur is not None
    assert str(cur.data(Qt.ItemDataRole.UserRole)) == p._current_id


def test_duplicate_creates_new_draft(page):
    p, root, mid, manifests = page
    from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
    from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
        build_index_from_directory,
    )

    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "done_c",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=4,
        )
    )
    index = build_index_from_directory(root)
    store.validate(draft.experiment_id, manifests, index)
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    p._refresh_experiments(prefer=completed.experiment_id)
    p._load(completed.experiment_id)
    old_hash = completed.config_hash
    p._duplicate()
    assert p._current_id != completed.experiment_id
    assert store.load_experiment(p._current_id).state == "draft"
    assert store.load_experiment(completed.experiment_id).config_hash == old_hash


def test_header_has_no_absolute_path(page):
    p, root, mid, manifests = page
    from ionogram_morphology_lab.ml_offline_baselines.runner import run_experiment
    from ionogram_morphology_lab.ml_offline_baselines.source_resolve import (
        build_index_from_directory,
    )

    store = OfflineBaselineStore(root)
    draft = store.create_draft(
        ExperimentConfig(
            "done_d",
            "tester",
            mid,
            "spread_f_morphology_classification",
            BASELINE_MAJORITY,
            seed=5,
        )
    )
    index = build_index_from_directory(root)
    store.validate(draft.experiment_id, manifests, index)
    completed = run_experiment(store, manifests, draft.experiment_id, index)
    p._refresh_experiments(prefer=completed.experiment_id)
    p._load(completed.experiment_id)
    status = p._status.text()
    assert "model_lab" not in status
    assert ":\\" not in status
    assert "experiment_summary.json" not in status
    tech = p._tech_body.toPlainText()
    assert "artifact_dir=" in tech or "summary_path=" in tech
