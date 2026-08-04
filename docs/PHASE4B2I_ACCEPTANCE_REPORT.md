# Phase 4B.2i Acceptance Report

**Phase:** Crash-Free Persistent V2 Worker, Non-Blocking Navigation, Essential Controls Restoration  
**Feature Pipeline V2:** `iml2-0.2.0` (geometry unchanged; shadow-only)  
**Date:** 2026-08-03  
**Scientific validation:** not claimed  
**Phase 4C:** not started  
**Git:** no commit / no push

---

## 0. Manual packaged-EXE verdict (4B.2h) — FAIL

Owner timings that forced this phase:

| Action | Observed |
|---|---|
| Startup | ~7 s |
| Diagnostics first appearance | ~27 s |
| Leave Diagnostics | ~20 s |
| Language switch | ~30 s |
| First V2 | ~11 s |
| Repeated V2 | ~8 s |
| **Cancel during V2** | **application closed** |

**Performance PASS = FAIL** · **Cancellation stability = FAIL** · **Layout PASS = FAIL**

---

## 1. Cancel crash — root cause

Primary cause: **Cancel called `QProcess.kill()` / `waitForFinished` from a QThread while the same `QProcess` was blocked in `waitForReadyRead` on another thread.** Qt `QProcess` is not thread-safe; tearing it down under cross-thread wait can abort the UI process.

Contributing factors:

- Worker `QThread` was parented to the Diagnostics page (navigation/teardown risk).
- Cancel invalidated generation but still allowed late signals to touch UI.
- Full EXE SHA-256 hashing on Technical Details / language-adjacent refresh inflated freezes (not the crash, but the 27–30 s stalls).

### Fix

- Replaced `QProcess` with **`subprocess.Popen`** behind a thread-safe `PersistentV2Worker` + explicit state machine.
- Cancel: immediate UI ack → disconnect slots → `disarm()` → kill child from worker lock → **async restart** (never blocks navigation).
- Job threads are **not parented** to page widgets.
- Audit trail: `workspaces/_cancel_crash_audit/` (`session.json`, `parent.log`, `child.log`, `qt_messages.log`, `exceptions.log`, `process_lifecycle.jsonl`) + faulthandler / Qt message hook.

**Crash reproduction after fix:** must be confirmed on the new packaged EXE (owner). Automated tests cover cancel + page switch without process exit; they cannot fully prove Windows GUI abort.

---

## 2. Persistent warm worker

| Property | Behaviour |
|---|---|
| Lifecycle | One `PersistentV2Worker` per app session (`shared_pool()`) |
| Start | Background after UI idle (~1.5 s) and on first compute |
| IPC | Frame-level `.npy` only — never full MAT |
| Cache hit | **Does not start or touch** the worker |
| After Cancel | Child killed → state `cancelled` → background `restarting` → `ready` |
| Shutdown | Only `MainWindow.closeEvent` |

Record separately in profiler/audit: cold start, warm IPC, compute, cache save, UI ack.

---

## 3. Navigation / language / first paint

| Issue | Fix |
|---|---|
| Leave Diagnostics ~20 s | No wait/join/terminate-and-wait on deactivate; page instance preserved |
| First appearance ~27 s | Deferred help/splitter/seq; activate reuses canvas; **EXE SHA cached / async** |
| Language ~30 s | `retranslate_ui` labels only; no refresh / no EXE re-hash / no worker I/O |
| Page activation | Does not run V2 or load all masks |

---

## 4. Quick layers + layout

- Always-visible quick strip: Source / Trace / Interference / Centerline / Branches (RU/EN).
- Full Layers drawer retained for expert layers; synced with quick strip.
- Help overlays from the right (not a permanent splitter sibling).
- Narrow width: splitter orientation adapts; primary Run/Cancel/frame/quick layers remain.

---

## 5. Automated verification

| Check | Result |
|---|---|
| `pytest tests/` | **343 passed** |
| Shadow / registry / geometry / i18n / docs | OK (re-run with suite) |

New tests: `tests/test_phase4b2i_cancel_and_nav.py`.

---

## 6. Packaged EXE

| Field | Value |
|---|---|
| Previous (4B.2h) | `E48C69CEECAFE0EEE16B1C4A84AADF58D2ED3F3DBE9193562213DE9BD92F1B78` |
| New (4B.2i) | `3153F1E2865D2790DD271ACAD902A7113B09B3FD60A9308017C0180C877FD071` |
| Path | `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |

Enable profiler for owner scenario: `IML_PACKAGED_PERF=1` (or Settings → packaged EXE profiler).  
Cancel audit: always written under `workspaces/_cancel_crash_audit/` in frozen builds.

---

## 7. Owner acceptance required (do not claim PASS without this)

On **new** SHA + `Am_all_2014-10-15.mat`:

1. Diagnostics first visible &lt; 0.3 s  
2. Warm page switch &lt; 0.3 s  
3. Language switch &lt; 0.5 s  
4. Cancel ack immediate; **Cancel never closes app** (repeat ≥3)  
5. Cached V2 &lt; 1 s  
6. Quick layers visible; readable at 1280×720 / 1366×768  
7. No Windows “Not responding” during V2 + page switch  

If any fail → report **FAIL** honestly.

---

## 8. Remaining blockers

- Owner packaged-EXE re-test not yet done → **performance / cancel PASS not claimed**.
- First cold worker spawn still costs roughly one packaged startup (~7 s) once per session; subsequent frames should reuse the warm process.
- Child cannot preempt mid-NumPy; Cancel kills the process (UI stays up).

---

## 9. Non-goals confirmed

- V2 scientific geometry unchanged  
- RuleEngine not wired to V2  
- Phase 4C not started  
- No scientific validation claim  
- No git commit / push  
