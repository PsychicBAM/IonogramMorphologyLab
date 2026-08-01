# IML v1.0 — Real Remaining External Blockers

Only genuine external dependencies. Unfinished application code is **not** listed here.

| # | Blocker | Impact | Resolution |
|---|---|---|---|
| 1 | **Inno Setup (ISCC) not installed** on this machine | Cannot produce `installer\IonogramMorphologyLab_Setup_1.0.0.exe` | Install Inno Setup, then run `packaging\build_installer.ps1` (or `iscc packaging\IonogramMorphologyLab.iss`) after the portable dist exists |
| 2 | **MATLAB Engine for Python not installed** | Backend `matlab_engine` unavailable (editor/library/packaging still work; execution falls back to external MATLAB / none) | From the MATLAB install: `cd "matlabroot\extern\engines\python"` then `python -m pip install .` for a compatible Python |
| 3 | **GNU Octave not installed** (optional) | Octave fallback backend unavailable | Install Octave and set path in Settings → MATLAB |
| 4 | **Copyrighted reference-pack figures** may lack redistribution permission | Atlas may show metadata-only / rights-restricted placeholders | Obtain rights or keep metadata-only packs |

## Not blockers (working without the above)

- Portable `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe` is built and smoke-tested.
- External MATLAB process backend was detected on this host (`D:\MATLAB\R2019a\...`) for `-batch` execution when configured.
- Editor, manifests, plugins, Model Lab, analysis pipeline, RU/EN UI, Help, Settings, validators, and tests operate without Inno Setup / MATLAB Engine / Octave.

## Explicit non-claims

- No unfinished GUI page is listed as an “external” blocker.
- Development ML models are intentionally **not** called externally validated.
