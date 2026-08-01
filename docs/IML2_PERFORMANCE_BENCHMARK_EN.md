# IML-2 Performance Benchmark (EN)

**Date:** 2026-08-01  
**Script:** `scripts/benchmark_real_frame_access.py`  
**Data:** Synthetic fallback `demo_mixed_diffuse.mat` (0.774 MB, shape 768×400, 3 frames).  
**Article 3 blinded data:** not used.

> Re-run with `--mat <approved_non_blinded_Am_all.mat>` for full-day KFU timings. Do not claim acceleration beyond measured values.

## Measured timings (this host run)

| Operation | Time (s) |
|---|---|
| Metadata inventory (`whosmat`) | 0.005 |
| File audit + load sample | 0.019 |
| First Zarr cache build | 0.524 |
| Frame retrieval (LRU cleared) | 0.005 |
| Frame retrieval (LRU hit) | ~0.000 |
| First PNG render | 1.092 |
| Repeat render | 0.346 |
| Contact sheet (available frames) | 0.428 |

Cache format: `iml2-zarr-frame-v1`, frame chunks 256×400.  
Cache hits/misses in script walk: 11 / 1.

## Bottlenecks / improvements

- First scientific PNG render dominates small-file demos (Matplotlib).
- Full-day Amp_all (~1 GB arrays) will be dominated by first MAT load + cache write; subsequent frame IO should stay near chunk read cost.
- LRU + prefetch reduce repeat Viewer navigation cost.

## Remaining limitations

- Benchmark without a user-supplied full-day MAT cannot report 1440-frame wall times.
- GUI responsiveness is architectural (background `QThread` cache build); not separately timed here.
