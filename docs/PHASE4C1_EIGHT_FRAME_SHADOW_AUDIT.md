# PHASE4C1 Eight-Frame Shadow Audit (identity-corrected)

**Smoke audit only.** Identities are taken from exact geometry-review JSON files
under `workspaces/IML_Project_65064ddf202b/feature_diagnostics/geometry_reviews`.
Geometry reviews are **not** morphology ground truth. Do **not** write “8/8 correct”.

Geometry-review JSON count: **9**

### Corpus metrics (Phase 4C.1b)

Do **not** treat file count as independent reviewed frames.

| Metric | Value |
|---|---:|
| `review_files_found` | 9 |
| `logical_reviewed_frames` (unique source_sha + frame among current) | 9 |
| `current_reviews` (unique full logical identity) | 9 |
| `superseded_reviews` | 0 |

Notes:
- Frame index **421** appears twice with **different** `source_sha256` values (`873ba472…` vs `a1185a17…`) — two distinct source identities, not one superseded pair.
- When the same logical identity is saved twice, the newest file is `current` and older files are `superseded` history (see `geometry_review_index.load_geometry_review_corpus`).
- Future metrics must report these four counts separately.

| review_file | source_sha (12) | frame | diagnostics_cache_id (12) | audit_status | candidate | assessability | interference | abstention |
|---|---|---:|---|---|---|---|---|---|
| `review_f0001_1a364c60584a.json` | `a1185a173fdb` | 1 | `1a364c60584a` | source_identity_mismatch_with_export | `None` | — | — | — |
| `review_f0002_0a5f546fd611.json` | `a19fd113f611` | 2 | `0a5f546fd611` | source_identity_unresolved_or_export_missing | `None` | — | — | — |
| `review_f0421_9dfb444be8ef.json` | `873ba4729e6f` | 421 | `9dfb444be8ef` | evaluated | `not_assessable` | not_assessable | low | no_valid_ionospheric_trace |
| `review_f0421_9f213d307dd4.json` | `a1185a173fdb` | 421 | `9f213d307dd4` | source_identity_mismatch_with_export | `None` | — | — | — |
| `review_f0720_a6c6918fc5fc.json` | `a1185a173fdb` | 720 | `a6c6918fc5fc` | source_identity_mismatch_with_export | `None` | — | — | — |
| `review_f1201_a620f0bcab81.json` | `a19fd113f611` | 1201 | `a620f0bcab81` | evaluated | `not_assessable` | not_assessable | high | no_valid_ionospheric_trace |
| `review_f1300_d18739eacf6f.json` | `a19fd113f611` | 1300 | `d18739eacf6f` | evaluated | `not_assessable` | not_assessable | low | no_valid_ionospheric_trace |
| `review_f1431_5ddb98b8b937.json` | `a19fd113f611` | 1431 | `5ddb98b8b937` | evaluated | `indeterminate` | indeterminate | low | severe_fragmentation |
| `review_f1440_5d0e7a7a4469.json` | `a1185a173fdb` | 1440 | `5d0e7a7a4469` | source_identity_mismatch_with_export | `None` | — | — | — |

## Notes

- Empty / no-trace / incomplete-legacy frames may be `not_assessable` or unevaluated.
- That is not a contradiction with geometry review acceptance.
- No accuracy / sensitivity / specificity / F1 claimed.

## Machine-readable

```json
[
  {
    "review_file": "review_f0001_1a364c60584a.json",
    "source_sha256": "a1185a173fdb429b4358e1f3d569170652462722ef20adc17bac2e1e4c77e4f6",
    "frame_index": 1,
    "diagnostics_cache_id": "1a364c60584a92e88d06c23629f2722f5fd5e65863bee69ce3a455f9b3b32a73",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "source_identity_mismatch_with_export",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-09-25\\frame_0001\\features.json",
    "candidate": null
  },
  {
    "review_file": "review_f0002_0a5f546fd611.json",
    "source_sha256": "a19fd113f61160a55fd761d89c9dd448932cc4b4b84aaeabd68ff74d680f6473",
    "frame_index": 2,
    "diagnostics_cache_id": "0a5f546fd6119ee6092c5c1336998460f8dc2b6d76658c9f1f2d1f20cc6f78dd",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "source_identity_unresolved_or_export_missing",
    "candidate": null,
    "note": "Corresponding V2 export not located; audit not run for this review."
  },
  {
    "review_file": "review_f0421_9dfb444be8ef.json",
    "source_sha256": "873ba4729e6f1df8d059126efedbfc247c7960d7687e907740c24872c5e541f8",
    "frame_index": 421,
    "diagnostics_cache_id": "9dfb444be8ef664bd777cb5ed8b5a03fd21d36d4d52a7aeba3537ca6da575564",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "evaluated",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-09-25\\frame_0421\\features.json",
    "candidate": "not_assessable",
    "assessability": "not_assessable",
    "evidence_strength": "none",
    "interference": "low",
    "abstained": true,
    "abstention_reasons": [
      "no_valid_ionospheric_trace"
    ],
    "ledger_entries": 2,
    "elapsed_ms": 2.5,
    "result_hash": "14cb6b183bcb6e8e3c6b0cd0d80a62c4f0bd428d12de14b43f11ca6fded30a34"
  },
  {
    "review_file": "review_f0421_9f213d307dd4.json",
    "source_sha256": "a1185a173fdb429b4358e1f3d569170652462722ef20adc17bac2e1e4c77e4f6",
    "frame_index": 421,
    "diagnostics_cache_id": "9f213d307dd4bb806037d1ccb01f18c3ff345ffa83136b39c3043a663b716ca0",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "source_identity_mismatch_with_export",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-09-25\\frame_0421\\features.json",
    "candidate": null
  },
  {
    "review_file": "review_f0720_a6c6918fc5fc.json",
    "source_sha256": "a1185a173fdb429b4358e1f3d569170652462722ef20adc17bac2e1e4c77e4f6",
    "frame_index": 720,
    "diagnostics_cache_id": "a6c6918fc5fc64588baf7251027fa1cd39cd6b03e95a43d7ac0a3bae98d55644",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "source_identity_mismatch_with_export",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-09-25\\frame_0720\\features.json",
    "candidate": null
  },
  {
    "review_file": "review_f1201_a620f0bcab81.json",
    "source_sha256": "a19fd113f61160a55fd761d89c9dd448932cc4b4b84aaeabd68ff74d680f6473",
    "frame_index": 1201,
    "diagnostics_cache_id": "a620f0bcab81db09712989d9e1465a7fdba89d0633b61e06959323b4a35b61c5",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "evaluated",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-10-15\\frame_1201\\features.json",
    "candidate": "not_assessable",
    "assessability": "not_assessable",
    "evidence_strength": "none",
    "interference": "high",
    "abstained": true,
    "abstention_reasons": [
      "no_valid_ionospheric_trace"
    ],
    "ledger_entries": 2,
    "elapsed_ms": 2.91,
    "result_hash": "c55e2c3b290bb7a29c95d35166dbabbccb91862b797e73e3ff63c6cd7bb054ec"
  },
  {
    "review_file": "review_f1300_d18739eacf6f.json",
    "source_sha256": "a19fd113f61160a55fd761d89c9dd448932cc4b4b84aaeabd68ff74d680f6473",
    "frame_index": 1300,
    "diagnostics_cache_id": "d18739eacf6fe2eabdfca561760dbdd822963b0c957f67fd9c2df226a9814811",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "evaluated",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-10-15\\frame_1300\\features.json",
    "candidate": "not_assessable",
    "assessability": "not_assessable",
    "evidence_strength": "none",
    "interference": "low",
    "abstained": true,
    "abstention_reasons": [
      "no_valid_ionospheric_trace"
    ],
    "ledger_entries": 2,
    "elapsed_ms": 3.77,
    "result_hash": "4de912ead3e7bdd705d1ec34ef98643b045033a3bbd475c4916eeddad2a5fd6b"
  },
  {
    "review_file": "review_f1431_5ddb98b8b937.json",
    "source_sha256": "a19fd113f61160a55fd761d89c9dd448932cc4b4b84aaeabd68ff74d680f6473",
    "frame_index": 1431,
    "diagnostics_cache_id": "5ddb98b8b93782eb8f9fdf6a3070b16ceac81ffd98b0f9d39061581da80f8608",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "evaluated",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-10-15\\frame_1431\\features.json",
    "candidate": "indeterminate",
    "assessability": "indeterminate",
    "evidence_strength": "none",
    "interference": "low",
    "abstained": true,
    "abstention_reasons": [
      "severe_fragmentation"
    ],
    "ledger_entries": 3,
    "elapsed_ms": 4.47,
    "result_hash": "707a6a324552ffbec03166ed20527acabceaea89810d6888ed9e9d29e03baf79"
  },
  {
    "review_file": "review_f1440_5d0e7a7a4469.json",
    "source_sha256": "a1185a173fdb429b4358e1f3d569170652462722ef20adc17bac2e1e4c77e4f6",
    "frame_index": 1440,
    "diagnostics_cache_id": "5d0e7a7a4469298b9f8845d2f35e6c314ceb143c1ac9a5b47377b83688e1a5ec",
    "feature_version": "iml2-0.2.0",
    "status": "acceptable",
    "geometry_review_exists": true,
    "geometry_review_is_morphology_gt": false,
    "audit_status": "source_identity_mismatch_with_export",
    "export_path": "docs\\_phase4b3_iml2-0.2.0_diagnostics\\Am_all_2014-09-25\\frame_1440\\features.json",
    "candidate": null
  }
]
```
