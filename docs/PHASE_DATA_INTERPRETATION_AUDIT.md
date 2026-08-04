# Phase Data Interpretation Audit (Phs_all) — Phase 4A

## Status: unresolved / disabled for automatic science

| Question | Finding |
|----------|---------|
| Present in audited day file `Am_all_2013-01-01.mat`? | **No** — inventory lists only `Amp_all` |
| Profile names `Phs_all`? | Yes (`kfu_cyclone_2013_2014.yaml`) |
| Numeric range / wrapping / units? | **Not verified** |
| Synchronized with Amp_all? | **Unresolved** |
| Raw vs processed phase? | **Unresolved** |
| Phase unwrapping scientifically valid? | **Unknown** |
| Instrument profile documents measurement? | Profile names the variable only — interpretation not confirmed |

## UI

When `Phs_all` is present in a MAT inventory:

- EN: “Phase data are available, but their scientific interpretation is not verified for this profile.”
- RU: «Фазовые данные доступны, но их научная интерпретация для этого профиля не подтверждена.»

## Automatic rules

`automatic_rules_enabled: false` in `SIGNAL_CONTRACTS.yaml`. Phase-derived automatic rules remain disabled by default.
