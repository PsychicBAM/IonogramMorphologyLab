# Phase 4C.1e.1 — Owner Verification Commands

**Project root:** `<PROJECT_ROOT>` (owner workspace)
**Purpose:** Manual source verification and packaging readiness after Phase 4C.1e.1 repairs.
**Do not treat the 4C.1d EXE as proof about this source tree.**

## Why the old EXE cannot verify 4C.1e

| Item | Value |
|---|---|
| Old packaged EXE SHA-256 | `CE301D426F71605DEEAA91B4E8B0AB30E8C4EAD6759B1FA0DB6AB7F00675D674` |
| That binary’s phase | **4C.1d** (accepted layout/detach baseline) |
| Phase 4C.1e packaging | **No new EXE was built**; no new SHA was calculated |

Screenshots or interactive QA against `CE301D…` show the **previous** Layers collapse defaults, Features toolbar, missing More menu, missing shortcut Help wiring, and older sequence/candidate messages. Those observations are **not** evidence that the 4C.1e / 4C.1e.1 **source** failed.

After source verification passes, the owner must **build a new executable**. Only that new EXE (with Build Identity phase `4C.1e.1` and a new SHA) can be used for packaged UI QA of this phase.

---

## Prerequisites (PowerShell)

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
$env:QT_QPA_PLATFORM = "offscreen"   # recommended for headless pytest
```

---

## 1. Full pytest

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests -q
```

Focused 4C.1e suite (optional):

```powershell
python -m pytest tests/test_phase4c1e_layout_sequence_state.py -q
```

---

## 2. Feature Registry validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_feature_registry_v2.py
```

---

## 3. Synthetic Geometry validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_synthetic_geometry_v2.py
```

---

## 4. V2 shadow validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_feature_shadow_mode.py
```

---

## 5. Morphology shadow validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_morphology_candidate_shadow.py
```

---

## 6. i18n validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_i18n.py
```

---

## 7. docs validator

```powershell
Set-Location "<PROJECT_ROOT>"
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python scripts/validate_docs.py
```

---

## 8. Portable packaging (existing project command)

Run **only after** pytest and validators succeed:

```powershell
Set-Location "<PROJECT_ROOT>"
powershell -ExecutionPolicy Bypass -File packaging\build_portable.ps1
```

Expected output path:

`dist\IonogramMorphologyLab\IonogramMorphologyLab.exe`

---

## 9. EXE SHA-256 calculation

```powershell
Get-FileHash `
  "dist\IonogramMorphologyLab\IonogramMorphologyLab.exe" `
  -Algorithm SHA256 | Format-List
```

Record the new hash in your packaging notes. It **must differ** from `CE301D426F71605DEEAA91B4E8B0AB30E8C4EAD6759B1FA0DB6AB7F00675D674`.

Confirm Build Identity (Help / Technical Details / Build Identity) shows:

- Phase: `4C.1e.1`
- Candidate engine: `iml-morph-candidate-0.1.1`
- Candidate cache schema: `2`
- Evidence ledger schema: `2`
- Diagnostics layout schema: `2`
- Sequence-state contract: `1`

---

## Packaged QA reminder (new EXE only)

1. Default layout: Layers left / canvas center / inspector right
2. Ctrl+0 restores ~15/55/30 with Layers open
3. Features More… menu; no mid-word truncated primary labels
4. Help / ⌨ shows Быстрые команды / Keyboard shortcuts
5. Ctrl+Shift+F / Ctrl+Shift+R / Escape
6. Sequence current-frame state messages (not bare “not calculated” while running)
7. Candidate controls follow current-frame readiness
8. Show results table / sequence splitter reachability
9. Cancel remains safe; no Not Responding
