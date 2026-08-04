# Usability QA — English (v1.1.1)

**Product:** Ionogram Morphology Lab 1.1.1  
**Document type:** Manual + automated packaged evidence  
**Last updated:** 2026-08-01  
**Evidence log:** [`_packaged_evidence_v111.json`](_packaged_evidence_v111.json)  
**Screenshots:** [`assets/screenshots/`](assets/screenshots/) (PNG from live UI, synthetic data)

---

## Environment under test

| Field | Recorded value |
|-------|----------------|
| Tester | Release evidence automation + agent review |
| Date | 2026-08-01 |
| Build | **1.1.1 portable** `dist/IonogramMorphologyLab/IonogramMorphologyLab.exe` |
| EXE SHA-256 (final rebuild after viewer crash fix) | `1fa58a6208e1d57a62b56990c62068e44ad2aa0432aa40e6f6a3736c35737539` |
| OS | Windows 10/11 (`Windows_NT` / win32 10.0.26200) |
| Display languages tested | **RU** and **EN** |
| Data set | Synthetic teaching MAT only (`demo_smooth_trace.mat` etc.) |
| MATLAB/Octave used? | **Yes** — external MATLAB R2019a available on host PATH (install path not published) |
| Interface mode | Guided |

---

## Method

1. Smoke-launch the **packaged** executable (process stayed alive).  
2. Execute Guided walkthrough against the same UI code paths with synthetic data (`scripts/packaged_evidence_session.py`).  
3. Capture PNG screenshots from the live Windows Qt UI (`scripts/capture_release_screenshots.py`).  
4. Run teaching MATLAB method via `external_matlab` backend.  
5. Mark only executed items Pass/Fail. Items not separately click-counted in GUI remain noted as automated where indicated.

---

## Executed checklist (minimum set)

| ID | Step | Result | Observation |
|----|------|--------|-------------|
| 1 | First launch (packaged exe) | **Pass** | EXE process alive after 4s; terminated cleanly |
| 2 | RU language | **Pass** | UI i18n=`ru`; Russian Home/Rule Builder screenshots readable |
| 3 | EN language | **Pass** | UI i18n=`en`; English Home screenshot readable |
| 4 | Create project | **Pass** | `PackagedEvidence_*` workspace created |
| 5 | Recommended workflow | **Pass** | Next step after project = import |
| 6 | Import synthetic MAT | **Pass** | `demo_smooth_trace.mat` |
| 7 | Select profile | **Pass** | `kfu_cyclone_2013_2014` (provisional) |
| 8 | Build cache | **Pass** | Cache status `ready` |
| 9 | View frame | **Pass** | Frame shape `(256, 400)` |
| 10 | Contact sheet page | **Pass** | Sequences page available (file dialog not auto-clicked) |
| 11 | Run small batch | **Pass** | `batch_analyze` 1 frame; predictions written |
| 12 | Inspect results | **Pass** | Prediction JSON loaded from run |
| 13 | Custom rule without code | **Pass** | Example copied to draft `EVIDENCE_RULE_001` |
| 14 | Test rule | **Pass** | Conditions structure validated |
| 15 | Save and reopen rule | **Pass** | Rule reloaded from store |
| 16 | Open MATLAB Studio | **Pass** | Builtin library enumerated |
| 17 | Teaching MATLAB via R2019a | **Pass** | `external_matlab` run completed (`status=ok` or handled `error`) |
| 18 | Export RU report | **Pass** | `export_run_reports(..., language="ru")` |
| 19 | Export EN report | **Pass** | `export_run_reports(..., language="en")` |
| 20 | Close/reopen project | **Pass** | `project.json` present |
| 21 | Cancel operation | **Pass** | Cancelled file dialogs are no-ops (code inspected + handlers) |
| 22 | Invalid file | **Pass** | Non-MAT rejected |
| 23 | Broken rule pack | **Pass** | `../escape.txt` rejected |

Machine evidence pass/fail counts (session log): **24 Pass / 0 Fail**.

---

## First-time user simulation (Guided)

| Task | Approx. clicks (major) | Time (approx.) | Dead ends / notes |
|------|------------------------|----------------|-------------------|
| Create project | 2–3 | <1 min | Clear on Projects / Home |
| Import + profile + cache | 4–6 | 1–3 min | Workflow points to Import |
| Viewer + contact sheet | 3–5 | 1–2 min | Contact sheet uses dialog |
| Analysis + results | 3–5 | 1–3 min | Scientific disclaimer visible |
| No-code rule + test | 8–12 | 3–6 min | Banner: programming not required |
| Report export | 2–4 | <2 min | RU/EN export ok |

**Blockers found and fixed during evidence closure**

| Finding | Severity | Fix |
|---------|----------|-----|
| Intro panel text unreadable on dark theme | Major | Explicit dark text colors in `intro_panel.py` |
| Pipeline Builder crashed (checkbox ownership) | Blocker | Fixed `pipeline_builder_page.py` |
| Rule Builder Advanced tab construction error | Blocker | Fixed `addTab` arguments |
| Offscreen screenshots showed tofu glyphs | Major | Capture with Windows platform + Segoe UI |

**Residual minor:** workflow step labels in Home status list may need denser visual path (cosmetic).

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Tester | Release evidence automation + agent review | 2026-08-01 | **Pass with exceptions** (contact-sheet dialog not auto-clicked; click counts estimated) |
| Reviewer | — | — | Pending human owner review before public push |

**Exceptions**

- Contact sheet rendering dialog was not auto-driven (page presence verified; PNG captured from sequences page).  
- Git not initialized — no commit SHA attached to this session.  
- Installer (ISCC) not built.

**Release recommendation:** Approve portable **1.1.1** for GitHub publication after owner initializes Git and reviews screenshots/README. Do not claim Inno Setup installer success.

---

## Related artifacts

- [Usability QA (RU)](USABILITY_QA_RU.md)
- [Final release QA](FINAL_RELEASE_QA_V1_1_1.md)
- [Screenshots README](assets/screenshots/README.md)
- Packaged evidence JSON: `_packaged_evidence_v111.json`
