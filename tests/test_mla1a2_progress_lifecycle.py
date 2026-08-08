"""Phase ML-B.1 — readiness worker progress completion lifecycle."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QMessageBox

from ionogram_morphology_lab.i18n.loader import I18n
from ionogram_morphology_lab.ml_dataset_readiness.store import (
    MLDatasetReadinessStore,
    ReadinessStoreError,
)
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from ionogram_morphology_lab.ui.ml_data_readiness_page import (
    FreezeReadinessWorker,
    MLDataReadinessPage,
)
from tests.test_mla1a1_acquisition_date import _am_all_13_corpus


class _FakeProject:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root


class _FakeSession:
    def __init__(self, root: Path) -> None:
        self.project = _FakeProject(root)
        self.current_project = self.project
        self.events = SimpleNamespace(project_changed=None)
        self.project_changed = None


@pytest.fixture
def no_msgbox(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)


def _page(qtbot, tmp_path: Path, lang: str = "en") -> MLDataReadinessPage:
    page = MLDataReadinessPage(_FakeSession(tmp_path), I18n(lang))
    qtbot.addWidget(page)
    page.show()
    QApplication.processEvents()
    return page


def test_build_identity_mla1a2():
    assert collect_build_identity(compute_sha=False)["release_phase"] == "ML-C.1b"


def test_freeze_store_emits_100(tmp_path: Path):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="P",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    seen: list[int] = []
    store.freeze_audit(
        draft.audit_id,
        corpus,
        progress_cb=lambda pct, msg: seen.append(int(pct)),
    )
    assert seen
    assert seen[-1] == 100
    assert max(seen) == 100


def test_success_ends_at_100_and_status(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="FreezeUI",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    page = _page(qtbot, tmp_path, "ru")
    page._begin_background_op()
    page.progress.setValue(66)
    page._last_progress_pct = 66
    page.status.setText("mid")
    # Simulate worker success path
    manifest = store.freeze_audit(draft.audit_id, corpus)
    page._on_frozen(manifest)
    assert page.progress.value() == 100
    assert page.status.text() == page.t("readiness.frozen_ok")
    assert "заморожен" in page.status.text().lower()
    assert page.btn_cancel.isEnabled() is False
    # Success cannot coexist with progress < 100
    assert not (
        page.status.text() == page.t("readiness.frozen_ok") and page.progress.value() < 100
    )


def test_duplicate_finished_ok_ignored(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="Dup",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    page = _page(qtbot, tmp_path, "en")
    manifest = store.freeze_audit(draft.audit_id, corpus)
    page._on_frozen(manifest)
    page.progress.setValue(100)
    page._on_frozen(manifest)  # duplicate
    assert page._op_terminal == "success"
    assert page.progress.value() == 100


def test_cancellation_not_success(qtbot, tmp_path: Path, no_msgbox):
    page = _page(qtbot, tmp_path, "ru")
    page._begin_background_op()
    page.progress.setValue(66)
    page._last_progress_pct = 66
    page._on_cancelled("cancelled")
    assert page._op_terminal == "cancelled"
    assert page.progress.value() < 100
    assert page.status.text() == page.t("readiness.cancel_requested")
    assert page.status.text() != page.t("readiness.frozen_ok")
    page.i18n.set_language("en")
    page.retranslate()
    page._op_terminal = ""
    page._on_cancelled("cancelled")
    assert "cancel" in page.status.text().lower()


def test_failure_not_success(qtbot, tmp_path: Path, no_msgbox):
    page = _page(qtbot, tmp_path, "en")
    page._begin_background_op()
    page.progress.setValue(40)
    page._last_progress_pct = 40
    page._on_fail("boom")
    assert page._op_terminal == "failed"
    assert page.progress.value() == 40
    assert page.status.text() == page.t("readiness.freeze_failed")
    assert page.status.text() != page.t("readiness.frozen_ok")
    page.i18n.set_language("ru")
    page._op_terminal = ""
    page._on_fail("boom")
    assert "заморозить" in page.status.text().lower() or "Не удалось" in page.status.text()


def test_fail_after_success_ignored(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="X",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    page = _page(qtbot, tmp_path, "en")
    manifest = store.freeze_audit(draft.audit_id, corpus)
    page._on_frozen(manifest)
    page._on_fail("late")
    assert page._op_terminal == "success"
    assert page.progress.value() == 100
    assert page.status.text() == page.t("readiness.frozen_ok")


def test_worker_emits_100_before_finished_ok(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="W",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    worker = FreezeReadinessWorker(
        store, corpus, mode=FreezeReadinessWorker.MODE_FREEZE, audit_id=draft.audit_id
    )
    progress_vals: list[int] = []
    results: list[object] = []

    class _Sink(QObject):
        def on_prog(self, pct: int, _msg: str) -> None:
            progress_vals.append(int(pct))

        def on_ok(self, manifest) -> None:
            results.append(manifest)

    sink = _Sink()
    worker.progress.connect(sink.on_prog)
    worker.finished_ok.connect(sink.on_ok)
    worker.start()
    assert worker.wait(60000)
    QApplication.processEvents()
    assert results
    assert 100 in progress_vals
    assert progress_vals[-1] == 100
    worker.deleteLater()


def test_export_success_at_100(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="E",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    frozen = store.freeze_audit(draft.audit_id, corpus)
    page = _page(qtbot, tmp_path, "en")
    page._audit_id = frozen.audit_id
    page._on_export()
    assert page.progress.value() == 100
    assert page.status.text() == page.t("readiness.export_ok")


def test_no_lingering_worker_after_finish(qtbot, tmp_path: Path, no_msgbox):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="T",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )
    page = _page(qtbot, tmp_path, "en")
    page._begin_background_op()
    page._worker = FreezeReadinessWorker(
        store, corpus, mode=FreezeReadinessWorker.MODE_FREEZE, audit_id=draft.audit_id
    )
    page._worker.progress.connect(page._on_progress)
    page._worker.finished_ok.connect(page._on_frozen)
    page._worker.failed.connect(page._on_fail)
    page._worker.cancelled.connect(page._on_cancelled)
    page._worker.finished.connect(page._on_worker_finished)
    page._worker.start()
    assert page._worker.wait(60000)
    QApplication.processEvents()
    assert page._worker is None
    assert page.progress.value() == 100
    page.close()
    QApplication.processEvents()
    assert page._worker is None


def test_cancelled_worker_does_not_succeed(qtbot, tmp_path: Path, no_msgbox, monkeypatch):
    corpus = _am_all_13_corpus(tmp_path)
    store = MLDatasetReadinessStore(tmp_path)
    draft = store.create_draft(
        title="C",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["am_all_13"],
    )

    def _cancel_freeze(*_a, **_k):
        raise ReadinessStoreError("cancelled")

    monkeypatch.setattr(store, "freeze_audit", _cancel_freeze)
    page = _page(qtbot, tmp_path, "en")
    page._begin_background_op()
    page.progress.setValue(50)
    page._last_progress_pct = 50
    worker = FreezeReadinessWorker(
        store, corpus, mode=FreezeReadinessWorker.MODE_FREEZE, audit_id=draft.audit_id
    )
    page._worker = worker
    worker.progress.connect(page._on_progress)
    worker.finished_ok.connect(page._on_frozen)
    worker.failed.connect(page._on_fail)
    worker.cancelled.connect(page._on_cancelled)
    worker.finished.connect(page._on_worker_finished)
    worker.start()
    assert worker.wait(30000)
    QApplication.processEvents()
    assert page._op_terminal == "cancelled"
    assert page.progress.value() < 100
    assert page.status.text() != page.t("readiness.frozen_ok")
