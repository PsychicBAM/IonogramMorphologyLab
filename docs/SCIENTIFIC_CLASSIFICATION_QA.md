# Scientific Classification QA — v1.1.1

**Status:** PASS for the documented real-MAT negative-control and frequency-candidate checks on the packaged build revision (2026-08-01).  
**Not a claim of physical Spread-F validation.**

| Field | Value |
|-------|-------|
| Portable EXE SHA-256 | `DC0239B6CAF120CF1E503E0EE3F80D7D050758B94D8A25676B9B271878A6C317` |
| MAT | `Am_all_2014-09-25.mat` (approved non-secret) |
| Profile | `kfu_cyclone_2013_2014` |
| Detailed audit | [MORPHOLOGY_DECISION_AUDIT_V1_1_1.md](MORPHOLOGY_DECISION_AUDIT_V1_1_1.md) |
| Product walkthrough | [PRODUCT_SIMPLIFICATION_QA.md](PRODUCT_SIMPLIFICATION_QA.md) |
| Automated tests | **103 passed** (`python -m pytest`) |
| Git / CI | GitHub repo pushed; Actions Test + Security checks green on latest `main` |

## Canonical non-spread token

- Rule engine: `none`
- Serialized: `clean`
- UI: “No visible spread” / «Явное рассеяние не обнаружено»

## Automated checks

| Check | Result |
|-------|--------|
| Clean visible trace ≠ mixed | Pass |
| Missing/NaN features ≠ positive spread | Pass |
| Mixed requires both absolute axes + colocated | Pass |
| Vertical interference ≠ range | Pass |
| Quality failure ≠ positive morphology | Pass |
| Rule/evidence trace present | Pass |

## Real MAT + packaged revision

| Check | Result | Notes |
|-------|--------|-------|
| Frame 421 not mixed_spread | Pass | `clean`, R004; unbalanced dual-axis → uncertain |
| Frame 800 frequency candidate | Pass | `frequency_spread`, R001, status proposed |
| Evidence / rules / disagreement visible | Pass | see walkthrough log |
| Day survey: no automatic mixed flood | Pass | documented in morphology audit |
| Expert-labelled real range/mixed on this day | Not Tested | no archive labels available; atlas REF003/REF001 definitional only |

## Remaining scientific limitations

- Automatic labels are candidates, not confirmed physical Spread-F.
- Virtual-height axis is nominal.
- No expert-confirmed range/mixed positives asserted for this MAT day.
- Interference heuristics may over-call early frames.
- Confidence `uncertain` on unbalanced dual-axis clean frames correctly reflects calibration limits.
