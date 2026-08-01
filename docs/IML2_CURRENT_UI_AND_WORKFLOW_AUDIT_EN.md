# IML-2 Current UI and Workflow Audit (EN)

**Application:** Ionogram Morphology Lab 0.1.0 (IML-1 MVP)  
**Audit date:** 2026-08-01  
**Scope:** Usability of the desktop shell — no Article 3 blinded data inspected.

## Screen descriptions (textual)

### Home
Short welcome + scientific disclaimer. No guided next-step CTA beyond navigation list.

### New Project
Single name field + Create. Status shows full filesystem path (developer-oriented).

### Import Data
File/folder buttons work. Results append lines like  
`Am_all_….mat: status=valid adapter=scipy_mat_v5 vars=1` — not end-user readable.  
Imported paths are stored in memory (`selected_mats`) but **not wired** to the Viewer.

### Instrument Profile
“Load KFU provisional profile” dumps **raw YAML/JSON**. Wizard advance prints step names. Warnings exist in data but are not badge-styled.

### Data Audit
Runs `audit_mat_path` and appends **raw JSON** per file.

### Ionogram Viewer (critical gap)
Button: “Render synthetic demo frame”. Always calls `generate_synthetic_case(...)`.  
**No connection** to imported MAT, frame index, time, cache, contact sheet, or playback.  
After a successful real import, the Viewer still shows only synthetic teaching data.

### Batch Analysis
Only control: `frame_step` spin box (default 120 in UI; observed user value 121).  
No explanation that frames are `1, 1+step, 1+2·step, …`.  
Progress log is **raw JSON events**. No expected-count preview, no time-range mode, no operation checklist.

### Results
List of `frame_id` strings; detail pane is **entire result JSON**.  
Buttons Accept / Uncertain / Not assessable partially translated; meaning of `confidence_score: null` unexplained.

### Reference Atlas / Scientific Basis
Raw metadata lines / CSV dumps. Not card-based; rights “unavailable” looks like empty content rather than a rights explanation.

### Reports
Export works; log is path JSON.

### Settings
Language combo + telemetry/network labels only. Combo may show `en` while UI was started in Russian if toolbar language and settings diverge.

### Help
One overview sentence. No workflow, categories, cache, abstention, or limitations sections.

## Confirmed root causes

| # | Problem | Cause in IML-1 code |
|---|---|---|
| 1–2 | Viewer ignores imports | `_viewer_demo` only; no `FrameStore` / session binding |
| 3 | Unexplained 12 results | `range(1, 1441, 121)` → 12 indices; no preview text |
| 4–8 | Raw JSON/CSV/YAML | Pages use `QPlainTextEdit` + `json.dumps` / file dumps |
| 9 | Thin Help | Single `help.overview` string |
| 10 | Thin Settings | No persistence store / tabs |
| 11–12 | Language drift | Incomplete i18n keys; toolbar vs settings not synced |
| 13 | Null confidence | Field shown raw; no calibration explanation |
| 14 | Slow / opaque MAT use | Full `loadmat` per batch path; no session cache reuse in Viewer |

## Non-goals retained

Scientific thresholds, rule provenance, blocklist, abstention, and “candidate morphology” wording remain unchanged in IML-2. Synthetic data stays available only as a labeled teaching demo.
