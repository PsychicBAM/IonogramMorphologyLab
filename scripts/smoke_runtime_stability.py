"""Headless smoke for MATLAB job manager + Model Lab missing-value handling."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("IML_DISABLE_ONBOARDING", "1")
os.environ.setdefault("IML_HEADLESS", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.classifiers.model_lab import ModelLab, ModelLabValidationError
    from ionogram_morphology_lab.matlab_studio.job_manager import MatlabJobManager
    from ionogram_morphology_lab.matlab_studio.runner import MatlabRunRequest
    from ionogram_morphology_lab.ui.main_window import MainWindow

    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="iml_runtime_smoke_"))
    script_ok = tmp / "ok.m"
    script_bad = tmp / "bad.m"
    script_ok.write_text("x = 1;\n", encoding="utf-8")
    script_bad.write_text("this is not valid matlab !!!\n", encoding="utf-8")

    mgr = MatlabJobManager()
    job = mgr.submit(
        MatlabRunRequest(
            script_path=script_bad,
            entrypoint="bad.m",
            backend="none",
            work_dir=tmp / "w_bad",
            timeout_s=5,
        ),
        script_id="bad",
    )
    assert job.status == "failed"
    assert not mgr.has_active_jobs()

    win = MainWindow(language="ru")
    assert win.matlab_page is not None
    assert win.matlab_page.job_manager is win.matlab_jobs
    assert not hasattr(win.matlab_page, "_worker") or win.matlab_page._current_job_id is None

    # Model Lab NaN → controlled error
    lab = ModelLab(tmp / "models")
    import csv

    csv_path = tmp / "nan.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "label", "f1", "f2"])
        w.writeheader()
        for i in range(8):
            w.writerow(
                {
                    "date": f"d{i % 4}",
                    "label": "a" if i % 2 == 0 else "b",
                    "f1": str(1.0 + i),
                    "f2": "nan" if i in (0, 3) else str(2.0 + i),
                }
            )
    ds = lab.import_labeled_csv(csv_path)
    blocked = False
    try:
        lab.train(ds, kind="logistic_regression", allow_imputation=False, split_method="random")
    except ModelLabValidationError as exc:
        blocked = True
        assert "missing" in exc.message_en.lower() or "пропущ" in exc.message_ru.lower()
    assert blocked
    card = lab.train(
        ds, kind="logistic_regression", allow_imputation=True, split_method="random", seed=0
    )
    assert "imputation" in str(card.training_manifest).lower() or "preproc" in str(card.to_dict()).lower()

    win.close()
    app.quit()
    print("smoke_runtime_stability OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
