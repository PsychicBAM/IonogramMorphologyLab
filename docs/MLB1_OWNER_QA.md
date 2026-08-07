# ML-B.1d Owner Visual QA Checklist

**Expected Build Identity:** `ML-B.1d`
**Manifest protocol:** `iml-ml-dataset-manifests-0.1.0`
**Readiness protocol:** `iml-ml-dataset-readiness-0.1.0`
**Packaged EXE:** `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe`
**Prior ML-B.1c SHA (must differ):** `8969243F66D5D966C2B98772ACBE6636C802DC2C3A2BA2C9F1D1198EBD3B9D9C`

## Owner QA status entering ML-B.1d

ML-B.1c confirmed: collapsible panels, larger workspace, readable Atomic Groups, Frozen immutability, Export, Integrity PASS, role counts (train 4/4, development 2/2, holdout 3/2), sealed holdout.

Two final presentation fixes in this build:

1. Frozen freeze-status consistency (Input Audit).
2. Human-readable Coverage UI.

---

## Scenario B — frozen presentation (primary)

**Project:** `workspaces/MLB1A_ScenarioB_GateF_QA`

1. Launch packaged EXE (`ML-B.1d`).
2. Open Scenario B → ML Dataset Manifests.
3. Compact context remains collapsed; Technical Details collapsed.
4. State Frozen; Integrity PASS.
5. Holdout reserved: **Items 3 / Atomic groups 2**; reference labels sealed; unlock unavailable.
6. **Input Audit** does **not** say “run Validate” / “выполните Проверку”.
7. Input Audit says the manifest is **already frozen**.
8. **Coverage** is human-readable (role sections + counts + compact tables).
9. No raw `unique_items` / `atomic_groups` / `acquisition_dates` / `target_distribution` labels in Coverage.
10. Full hashes only via Technical Details (expand briefly).
11. RU↔EN live switch updates freeze status + Coverage labels.
12. Frozen controls remain immutable; Export available.
13. Scientific counts unchanged (9 items / 8 groups; roles as above).
14. No Not Responding / QThread leak.

---

## Scenario A — brief

- Gate-A (Gate ≠ F) blockers still appear correctly.
- Draft / freeze-blocked behavior unchanged scientifically.
- Input Audit shows blockers (not “already frozen”).

---

## Sign-off

| Item | Pass? |
| --- | --- |
| Build Identity ML-B.1d | |
| EXE SHA ≠ prior 1c | |
| Frozen Input Audit status correct | |
| Coverage human-readable + localized | |
| Scenario A blockers unchanged | |
| No ML-C / no training / no commit | |

Owner: _______________ Date: _______________
