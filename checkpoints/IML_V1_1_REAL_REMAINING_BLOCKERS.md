# IML v1.1 — Real Remaining External Blockers

Only genuine external dependencies. Application code for v1.1 hardening is complete.

| # | Blocker | Impact | Resolution |
|---|---|---|---|
| 1 | Inno Setup (ISCC) not installed | Cannot build `installer\IonogramMorphologyLab_Setup_1.1.0.exe` | Install Inno Setup; run `packaging\build_installer.ps1` |
| 2 | MATLAB Engine for Python not installed | `matlab_engine` backend unavailable | Optional; external MATLAB `-batch` works (verified R2019a) |
| 3 | GNU Octave not installed | Octave fallback unavailable | Optional |
| 4 | Copyrighted reference figures | Atlas may remain metadata-only | Obtain redistribution rights |

## Verified without these blockers

- Portable `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` rebuilt for 1.1.0
- Real MATLAB R2019a `-batch`: 11/11 smoke methods OK on approved MAT
- Rule Builder e2e, validators, and 48 pytest tests OK
