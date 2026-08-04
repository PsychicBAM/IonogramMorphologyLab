# Signal Contract Guide (Phase 4A / 4A.1)

Automatic analysis must not be based only on a rendered PNG. The primary scientific input is the numeric MAT content from which the ionogram is rendered.

## Registry

Machine-readable file: `knowledge_base/SIGNAL_CONTRACTS.yaml`

Each contract records variable role, expected shape, axes, units, calibration/verification status, allowed uses, and prohibited claims.

### Phase 4A.1 shape schema

Do not mix notes and numeric shapes in one list. Use:

- `accepted_shapes` — list of numeric shape lists only
- `shape_constraints` — ndim / multiples / frames_per_file / rows_per_frame / axis lengths
- `accepted_dtypes`
- `optional_presence`
- `verification_evidence`

## KFU Cyclone — verified vs unresolved

| Variable | Status | Notes |
|----------|--------|-------|
| `Amp_all` | provisionally_verified | Shape `(368640, 400)` confirmed on approved day file (`uint16`); stacked 1440×256×400; frames 1/421/1440 slice-verified |
| `ff` | provisionally_verified | May be absent; profile start/step used as fallback |
| `Phs_all` | unresolved | Automatic phase rules **disabled** |
| `Date_Time1` | unresolved | File-dependent; navigation uses `matlab_index_minus_1_minute` |
| `AmEsP`, `A_map_F`, `H_map_F` | unresolved | See `docs/ARCHIVE_VARIABLE_AUDIT_4A1.md` for occurrences in archive products; automatic use disabled |

## Frame mapping (Amp_all)

1-based frame index `i`:

- Python rows `[ (i-1)*256 , i*256 )`
- MATLAB-style inclusive rows `(i-1)*256+1` through `i*256`
- Frame 1 → rows 0–255 (Python) / 1–256 (MATLAB)
- Frame 421 → minute 420 → `07:00` provisional
- Frame 1440 → final 256 rows of the 368640-row stack

Viewer cache, batch pipeline, and MATLAB bridge all call the same `extract_frame_kfu` / `extract_frame_consistent` mapping.

## Status vocabulary

`verified` · `provisionally_verified` · `source_supported` · `project_heuristic` · `unavailable` · `unresolved` · `disabled`
