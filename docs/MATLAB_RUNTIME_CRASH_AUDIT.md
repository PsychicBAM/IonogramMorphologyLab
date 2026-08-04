# MATLAB Runtime Crash Audit

**Status:** root cause confirmed from source + lifecycle design  
**Phase:** Runtime Stability  
**App version:** 1.1.1

## Observed failure

Console:

```text
QThread: Destroyed while thread '' is still running
```

Symptom: running a user MATLAB script can close the entire application.

## Reproduction context (packaged EXE / UI)

| Item | Value |
|------|--------|
| Entry | MATLAB Studio → Run |
| Worker type (legacy) | `_RunWorker(QThread)` in `ui/matlab_studio_page.py` |
| Execution body | `run_matlab_job` → `subprocess.run` (external MATLAB/Octave) or MATLAB Engine |
| Parent ownership | **None** — `QThread()` constructed without parent |
| Storage | `MatlabStudioPage._worker` overwritten on each Run |
| Navigation | Page kept in `QStackedWidget` (not destroyed on leave) |
| App close | No `closeEvent` wait for MATLAB worker |

Typical sequence:

1. User imports/opens a script and clicks **Run**.
2. UI creates `_RunWorker`, connects signals, calls `start()`.
3. Worker blocks inside `subprocess.run` / Engine while MATLAB executes.
4. Trigger: second **Run**, page teardown, or application exit → previous `QThread` Python reference dropped / QObject destroyed.
5. Qt reports *Destroyed while thread is still running*; process may abort.

## Root cause (exact)

**Primary:** `MatlabStudioPage._run` reassigned `self._worker = _RunWorker(req)` with:

- no `isRunning()` guard;
- no `quit()` / `wait()` / cancel of the previous job;
- no QObject parent tying the thread to the page/manager lifetime.

When a still-running unparented `QThread` is garbage-collected or destroyed, Qt emits the fatal lifetime error.

**Secondary:** application close without draining active MATLAB jobs (no close dialog, no terminate/kill sequence).

**Not primary:** navigation away alone (page remains in the stack). Backend timeout alone does not destroy the QThread; timeout raises inside `run()` and emits `failed`/`finished_ok` if the worker object still exists.

## Checks performed

| Check | Result |
|-------|--------|
| Local-only QThread variables | Worker stored on `self._worker`, but prior instance becomes unreferenced on re-run |
| Python GC | Unparented prior worker eligible for destruction while OS thread still in `run()` |
| Page recreation | Not required; reassignment sufficient |
| Navigation away | Unlikely alone |
| `closeEvent` | Missing on `MainWindow` / MATLAB page |
| Multiple Run clicks | **Confirmed destroy path** |
| Worker exceptions | Should emit `failed`; must not tear down QThread early |
| Backend timeout | Handled inside `run_matlab_job`; unsafe if UI replaces worker mid-timeout |
| Lost parent ownership | No parent was set |
| Premature `deleteLater` | Not used; GC/destruction equivalent |
| Thread replacement without shutdown | **Confirmed** |

## Remediation (this phase)

1. Central `MatlabJobManager` owns all jobs for their full lifetime.
2. External MATLAB/Octave: managed `QProcess` (argument list, timeout, terminate/kill).
3. MATLAB Engine: controlled `QThread` **parented by the manager**, never overwritten while running.
4. Safe close dialog + ordered shutdown.
5. User-visible failure card; never treat script failure as app success / crash.

## Signal / ownership target sequence

```text
UI Run → JobManager.submit
       → status: queued → starting → running
       → QProcess/Engine worker owned by manager
       → stdout/stderr streamed via Qt signals
       → completed | failed | timed_out | cancelled
       → UI result card (never process exit)
Close → active? → Cancel / Stop&Close / Wait
       → cancel → wait → terminate → kill → release → close GUI
```
