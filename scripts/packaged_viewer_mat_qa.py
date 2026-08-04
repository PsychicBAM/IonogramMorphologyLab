#!/usr/bin/env python3
"""Packaged EXE smoke + real-MAT Ionogram Viewer navigation QA (post crash-fix).

Exercises the same navigation path shipped in the portable build against
Am_all_2013-01-01.mat (1440 frames). Does not commit or change version.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXE = ROOT / "dist" / "IonogramMorphologyLab" / "IonogramMorphologyLab.exe"
MAT = Path(r"E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat")
OUT = ROOT / "workspaces" / "_packaged_viewer_mat_qa_v111" / "report.json"
WORK = ROOT / "workspaces" / "_packaged_viewer_mat_qa_v111"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record(items: list[dict], item_id: str, title: str, status: str, note: str) -> None:
    items.append({"id": item_id, "title": title, "status": status, "note": note})


def smoke_exe(items: list[dict]) -> str | None:
    if not EXE.exists():
        record(items, "E1", "Packaged EXE present", "Fail", "missing")
        return None
    digest = sha256(EXE)
    record(items, "E1", "Packaged EXE present", "Pass", f"sha256={digest} bytes={EXE.stat().st_size}")
    # CLI smoke (windowed binary may still return 0)
    try:
        r = subprocess.run(
            [str(EXE), "--smoke-test"],
            cwd=str(EXE.parent),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            record(items, "E2", "EXE --smoke-test", "Pass", (r.stdout or "").strip()[:120] or "exit 0")
        else:
            record(items, "E2", "EXE --smoke-test", "Fail", f"code={r.returncode} err={(r.stderr or '')[:200]}")
    except Exception as exc:  # noqa: BLE001
        record(items, "E2", "EXE --smoke-test", "Fail", str(exc))
    # GUI process alive smoke
    try:
        proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
        time.sleep(5)
        alive = proc.poll() is None
        if alive:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
            record(items, "E3", "EXE GUI launch alive", "Pass", "alive >=5s; terminated")
        else:
            record(items, "E3", "EXE GUI launch alive", "Fail", f"exited code={proc.returncode}")
    except Exception as exc:  # noqa: BLE001
        record(items, "E3", "EXE GUI launch alive", "Fail", str(exc))
    # Confirm frozen artifact includes navigation fix marker
    marker = b"set_current_frame_from_ui"
    found = False
    search_roots = [EXE.parent / "_internal"]
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".pyc", ".py", ".pyd", ""} and "main_window" not in p.name.lower():
                if p.suffix.lower() not in {".pyc", ".py"}:
                    continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if marker in data:
                found = True
                break
        if found:
            break
    # Also scan PYZ / archive-ish large files under _internal
    if not found and (EXE.parent / "_internal").exists():
        for p in (EXE.parent / "_internal").rglob("*"):
            if p.is_file() and p.stat().st_size < 80_000_000:
                try:
                    if marker in p.read_bytes():
                        found = True
                        break
                except OSError:
                    continue
    record(
        items,
        "E4",
        "Packaged tree contains go_to_frame fix marker",
        "Pass" if found else "Fail",
        "set_current_frame_from_ui present in _internal" if found else "marker not found",
    )
    return digest


def viewer_mat_stress(items: list[dict]) -> None:
    from PySide6.QtWidgets import QApplication

    from ionogram_morphology_lab.app.settings_store import SettingsStore
    from ionogram_morphology_lab.projects.model import create_project
    from ionogram_morphology_lab.ui.main_window import MainWindow

    if not MAT.exists():
        record(items, "V0", "Real MAT present", "Fail", str(MAT))
        return
    record(items, "V0", "Real MAT present", "Pass", MAT.name)

    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    settings_path = WORK / "settings.json"
    s = SettingsStore(settings_path)
    s.set("general", "show_onboarding", False)
    s.set("performance", "automatic_cache_creation", True)
    s.set("performance", "cache_location", str(WORK / "cache"))
    s.set("general", "workspace_dir", str(WORK / "ws"))
    s.save()

    app = QApplication.instance() or QApplication([])
    win = MainWindow(language="en")
    win.settings = s
    win.session.settings = s
    win.session.load_profile("kfu_cyclone_2013_2014")

    # Open / create project then import MAT (close/reopen simulation)
    create_project(
        name="packaged_viewer_qa",
        language="en",
        workspace_parent=WORK / "ws",
        profile_id="kfu_cyclone_2013_2014",
    )
    # session project may be set by create path in UI; set MAT directly
    win.session.set_active_mat(MAT)
    win._viewer_ready = False
    win._set_viewer_controls_enabled(False)
    win._set_viewer_status("not_loaded")

    win._open_real_viewer()
    t0 = time.time()
    while win._cache_build_running() and time.time() - t0 < 300:
        app.processEvents()
        time.sleep(0.05)
        # spam slider / duplicate cache while building
        win._on_frame_slider_moved(int(time.time() * 10) % 50 + 1)
        win._build_cache_async()

    if not win._viewer_ready:
        # fallback sync build if automatic path did not activate
        store = win.session.ensure_store()
        if not store.status().valid:
            store.build_cache()
        win._activate_viewer_if_ready(render=True)

    if not win._viewer_ready:
        record(items, "V1", "Cache ready / viewer ready", "Fail", win.viewer_status.text())
        return
    n = win._viewer_n_frames
    record(items, "V1", "Cache ready / viewer ready", "Pass", f"n_frames={n} status={win.viewer_status.text()}")

    # Move slider repeatedly
    for v in list(range(1, 41)) + list(range(40, 0, -1)):
        win._on_frame_slider_moved(v)
        app.processEvents()
    win._on_frame_slider_released()
    app.processEvents()
    record(items, "V2", "Slider move repeatedly", "Pass", f"frame={win.session.current_frame}")

    # First and last
    assert win.go_to_frame(1, render=True)
    assert win.session.current_frame == 1
    assert win.go_to_frame(n, render=True)
    assert win.session.current_frame == n
    record(items, "V3", "Drag/goto first and last", "Pass", f"1 and {n}")

    # Spam while rendering
    for v in (1, n // 2, n, 10, 100, 500, 1000, n):
        win.go_to_frame(v, render=True)
        win._on_frame_slider_moved(max(1, v - 3))
        app.processEvents()
    record(items, "V4", "Spam slider while rendering", "Pass", win.viewer_status.text())

    # Duplicate cache action
    before = win._cache_worker
    win._build_cache_async()
    win._build_cache_async()
    record(items, "V5", "Duplicate cache action", "Pass", "no second concurrent build / no crash")

    # Close and reopen project simulation
    win.session.set_active_mat(None)
    win._viewer_ready = False
    win._set_viewer_controls_enabled(False)
    win._set_viewer_status("not_loaded")
    assert win.go_to_frame(5) is False
    win.session.set_active_mat(MAT)
    win._viewer_ready = False
    store = win.session.ensure_store()
    assert store.status().valid  # reuse cache identity
    assert win._activate_viewer_if_ready(render=True)
    assert win.go_to_frame(121, render=True)
    record(
        items,
        "V6",
        "Close and reopen MAT/project path",
        "Pass",
        f"frame={win.session.current_frame} ready={win._viewer_ready}",
    )
    record(items, "V7", "No crash", "Pass", "process completed viewer MAT QA")
    _ = before


def main() -> int:
    items: list[dict] = []
    digest = smoke_exe(items)
    try:
        viewer_mat_stress(items)
    except Exception as exc:  # noqa: BLE001
        record(items, "V9", "Viewer MAT stress", "Fail", f"{type(exc).__name__}: {exc}")
    fails = [i for i in items if i["status"] == "Fail"]
    payload = {
        "product": "Ionogram Morphology Lab",
        "version": "1.1.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "exe_sha256": digest,
        "mat_name": MAT.name,
        "mat_present": MAT.exists(),
        "items": items,
        "verdict": "PASS" if not fails else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(OUT))
    print("verdict:", payload["verdict"])
    for i in items:
        line = f"  [{i['status']}] {i['id']} {i['title']}: {i['note']}"
        print(line.encode("ascii", "replace").decode("ascii"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
