# Feature Diagnostics Real Archive Performance (Phase 4B.2g)

**Primary archive:** `E:\ionog\conference_presentation\ion2014\maps201410oct\data\Am_all_2014-10-15.mat`
**Size:** `192041636` bytes (~192.0 MB)
**Shape:** `[368640, 400]`

## Measured wall times (Python worker path)

| Operation | Seconds |
|-----------|--------:|
| Source SHA-256 (once) | 0.784 |
| Full MAT load | 2.995 |
| FrameStore init (SHA supplied) | 0.001 |
| Zarr cache build | 16.812 |
| Frame extract from loaded MAT (median) | 0.0001 |
| Frame extract from Zarr (median) | 0.0089 |
| Frame extract from Zarr (p95) | 0.0147 |
| Uncached V2 compute (median) | 1.316 |
| Uncached V2 compute (max) | 1.429 |
| V2 cache serialize (median) | 0.049 |
| V2 summary load (median) | 0.0405 |
| One heavy layer load (median) | 0.0274 |
| All heavy layers load (median) | 0.445 |
| Nav: Zarr frame + summary (median) | 0.0762 |
| Nav: Zarr frame + summary (max) | 0.0859 |
| SHA recalcs after 20 navigation peeks | 0 |

## Interpretation vs packaged-EXE freezes

- Full MAT load (~seconds) and full SHA (~seconds) must **not** run on every slider tick.
- After Zarr is ready, frame navigation is milliseconds; UI freezes of 90–120 s indicate MAT reopen/hash on the UI thread.
- Loading **all** V2 masks can exceed a single V2 compute; frame change must use **summary-only** load.
- Uncached V2 science time on this workstation is ~1–2 s/frame in-process; 40–60 s EXE freezes imply UI-thread MAT I/O, full-cache deserialize, or GIL-blocking work in callbacks — addressed by FrameStore-first load, SHA reuse, lazy cache, and release-only slider submit.

## Manual packaged-EXE still required

Record separately: slider drag responsiveness, Cancel click-to-ack, page switch during V2, Windows “Not responding”.

Raw JSON: `_fd_real_perf_raw.json`

## Secondary archive

`E:\ionog\conference_presentation\ion2013\maps201301jan\data\Am_all_2013-01-01.mat` — MAT load `2.615s`, uncached V2 median `0.732s`
