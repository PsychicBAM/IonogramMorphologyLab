# Feature Pipeline V2 Performance

## Full-file evidence (Phase 4B.1)

Source: `docs/_phase4b1_fullfile_perf/fullfile_performance_report.json`  
Archive: `Am_all_2013-01-01.mat` (1440 frames) — **not extrapolated from 15 frames**.

| Metric | Value |
| --- | --- |
| Frames completed | 1440 |
| Total elapsed | 1934.1 s |
| Median / p95 per frame | 1.450 / 2.238 s |
| Peak traced memory | 15.6 MB |
| Source SHA unchanged | yes |
| Resume | supported (`--resume`) |
| Cancellation flag | recorded in state |

## Other tooling

- Resumable diagnostic export: `scripts/export_feature_diagnostics_v2.py`
- Resumable shadow audit: `scripts/run_feature_pipeline_v2_shadow_audit.py --resume`
- Full-file perf: `scripts/run_feature_pipeline_v2_fullfile_perf.py`
