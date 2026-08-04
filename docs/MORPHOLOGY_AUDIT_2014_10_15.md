# Morphology audit — Am_all_2014-10-15 (20:00–23:59, 10 min)

**Status:** automatic candidate · visual owner review pending · expert confirmed only when actually confirmed.

- Source MAT: `ion2014/maps201410oct/data/Am_all_2014-10-15.mat` (workspace sibling dataset; not packaged in the app tree)
- Profile: `kfu_cyclone_2013_2014`
- Frames audited: 24
- Canonical morphology counts: `{"interference_dominated": 20, "diffuse_unspecified": 4}`
- Frames classified `diffuse_unspecified`: 4

## Decision notes

- Classifications are **automatic candidates** from the RuleEngine + feature vector.
- No frame IDs were hardcoded.
- `clean` / «Явное рассеяние не обнаружено» means assessable with no supported spread and no residual diffuseness above the uncertainty floor — not a proof of physical absence.
- `diffuse_unspecified` is used when broadening/diffuseness is visible but evidence is insufficient for frequency / range / mixed.

### Owner-review disagreements (automatic vs visual expectation)

- Early evening frames (~20:00–20:30) have high `interference_dominance` and many branches → automatic `interference_dominated` is plausible.
- Mid/late frames with **H≈20 / V≈9** but still `interference_dominated` (R005) may be **over-suppressed**: visual F-region broadening could justify `diffuse_unspecified`, `frequency_spread`, or `mixed_spread` after expert review. Marked **visual owner review pending** — not expert-confirmed.
- Frame **1311 (21:50)** → automatic `diffuse_unspecified` (not `clean`). This matches the requirement that visible diffuseness must not display as “No visible spread”.
- Zero frames in this window were automatic `clean`. Frames changed from a previous broad “clean/no visible spread” fallback: at least the four `diffuse_unspecified` cases (1291, 1301, 1311, 1351).

## Audit table

| Frame | Time | Trace | Diffuseness | H width | V width | Interf. | Branches | Rules fired | Canonical | Display (RU) | Expert note | Review |
|------:|:----:|:-----:|------------:|--------:|--------:|--------:|---------:|:------------|:----------|:-------------|:------------|:-------|
| 1201 | 20:00 | yes | 0.8 | 0.8 | 0.8 | 0.818 | 7.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1211 | 20:10 | yes | 0.8 | 0.8 | 0.8 | 0.858 | 9.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1221 | 20:20 | yes | 0.8 | 0.8 | 0.8 | 0.844 | 6.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1231 | 20:30 | yes | 0.8 | 0.8 | 0.8 | 0.824 | 5.5 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1241 | 20:40 | yes | 20.0 | 20.0 | 9.0 | 0.263 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1251 | 20:50 | yes | 18.439 | 18.439 | 7.801 | 0.273 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1261 | 21:00 | yes | 20.0 | 20.0 | 9.0 | 0.32 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1271 | 21:10 | yes | 20.0 | 20.0 | 9.0 | 0.255 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1281 | 21:20 | yes | 19.698 | 19.698 | 8.864 | 0.279 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1291 | 21:30 | yes | 20.0 | 20.0 | 9.0 | 0.213 | 1.0 | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип рассеяния не определён | automatic candidate: diffuse structure undetermined | automatic candidate; visual owner review pending |
| 1301 | 21:40 | yes | 20.0 | 20.0 | 9.0 | 0.247 | 1.0 | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип рассеяния не определён | automatic candidate: diffuse structure undetermined | automatic candidate; visual owner review pending |
| 1311 | 21:50 | yes | 20.0 | 20.0 | 9.0 | 0.196 | 1.0 | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип рассеяния не определён | automatic candidate: diffuse structure undetermined | automatic candidate; visual owner review pending |
| 1321 | 22:00 | yes | 14.0 | 14.0 | 6.037 | 0.324 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1331 | 22:10 | yes | 20.0 | 20.0 | 9.0 | 0.272 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1341 | 22:20 | yes | 18.654 | 18.654 | 8.864 | 0.299 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1351 | 22:30 | yes | 20.0 | 20.0 | 9.0 | 0.222 | 1.0 | `—` | `diffuse_unspecified` | Наблюдается диффузная структура, тип рассеяния не определён | automatic candidate: diffuse structure undetermined | automatic candidate; visual owner review pending |
| 1361 | 22:40 | yes | 20.0 | 20.0 | 9.0 | 0.309 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1371 | 22:50 | yes | 20.0 | 20.0 | 9.0 | 0.254 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1381 | 23:00 | yes | 20.0 | 20.0 | 9.0 | 0.276 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1391 | 23:10 | yes | 20.0 | 20.0 | 9.0 | 0.272 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1401 | 23:20 | yes | 20.0 | 20.0 | 9.0 | 0.346 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1411 | 23:30 | yes | 20.0 | 20.0 | 9.0 | 0.3 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1421 | 23:40 | yes | 20.0 | 20.0 | 9.0 | 0.262 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |
| 1431 | 23:50 | yes | 20.0 | 20.0 | 9.0 | 0.369 | 1.0 | `R005` | `interference_dominated` | Оценка морфологии ограничена доминирующими помехами | visual owner review pending | automatic candidate; visual owner review pending |

## Frames with elevated width (visual focus)

- **f1201 20:00** → `interference_dominated` (H=0.8, V=0.8, persist H/V=0.0/0.0, interf=0.818) — visual owner review pending
- **f1211 20:10** → `interference_dominated` (H=0.8, V=0.8, persist H/V=0.0/0.0, interf=0.858) — visual owner review pending
- **f1221 20:20** → `interference_dominated` (H=0.8, V=0.8, persist H/V=0.0/0.0, interf=0.844) — visual owner review pending
- **f1231 20:30** → `interference_dominated` (H=0.8, V=0.8, persist H/V=0.0/0.0, interf=0.824) — visual owner review pending
- **f1241 20:40** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.978/0.81, interf=0.263) — visual owner review pending
- **f1251 20:50** → `interference_dominated` (H=18.439, V=7.801, persist H/V=0.957/0.665, interf=0.273) — visual owner review pending
- **f1261 21:00** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.963/0.855, interf=0.32) — visual owner review pending
- **f1271 21:10** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.971/0.934, interf=0.255) — visual owner review pending
- **f1281 21:20** → `interference_dominated` (H=19.698, V=8.864, persist H/V=0.961/0.778, interf=0.279) — visual owner review pending
- **f1291 21:30** → `diffuse_unspecified` (H=20.0, V=9.0, persist H/V=0.984/0.935, interf=0.213) — automatic candidate: diffuse structure undetermined
- **f1301 21:40** → `diffuse_unspecified` (H=20.0, V=9.0, persist H/V=0.994/0.945, interf=0.247) — automatic candidate: diffuse structure undetermined
- **f1311 21:50** → `diffuse_unspecified` (H=20.0, V=9.0, persist H/V=0.739/0.703, interf=0.196) — automatic candidate: diffuse structure undetermined
- **f1321 22:00** → `interference_dominated` (H=14.0, V=6.037, persist H/V=0.915/0.504, interf=0.324) — visual owner review pending
- **f1331 22:10** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.992/0.929, interf=0.272) — visual owner review pending
- **f1341 22:20** → `interference_dominated` (H=18.654, V=8.864, persist H/V=0.981/0.695, interf=0.299) — visual owner review pending
- **f1351 22:30** → `diffuse_unspecified` (H=20.0, V=9.0, persist H/V=0.958/0.885, interf=0.222) — automatic candidate: diffuse structure undetermined
- **f1361 22:40** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.992/0.942, interf=0.309) — visual owner review pending
- **f1371 22:50** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.956/0.941, interf=0.254) — visual owner review pending
- **f1381 23:00** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.919/0.82, interf=0.276) — visual owner review pending
- **f1391 23:10** → `interference_dominated` (H=20.0, V=9.0, persist H/V=1.0/1.0, interf=0.272) — visual owner review pending
- **f1401 23:20** → `interference_dominated` (H=20.0, V=9.0, persist H/V=1.0/0.989, interf=0.346) — visual owner review pending
- **f1411 23:30** → `interference_dominated` (H=20.0, V=9.0, persist H/V=1.0/1.0, interf=0.3) — visual owner review pending
- **f1421 23:40** → `interference_dominated` (H=20.0, V=9.0, persist H/V=0.99/0.939, interf=0.262) — visual owner review pending
- **f1431 23:50** → `interference_dominated` (H=20.0, V=9.0, persist H/V=1.0/1.0, interf=0.369) — visual owner review pending

## Machine-readable dump

See `workspaces/_morph_audit_2014_10_15/audit_rows.json`.

