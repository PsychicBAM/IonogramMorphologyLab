# Installation — Ionogram Morphology Lab 1.1.1

This guide covers portable release deployment and development setup. MATLAB and Octave are **optional**; core import, viewing, analysis, expert review, and reporting work without them.

## System requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| OS (primary) | Windows 10/11 x64 | Portable `.exe` and PySide6 GUI |
| OS (development) | Windows, Linux, macOS | Python 3.10+ from source |
| RAM | 8 GB recommended | More for large MAT batches and cache |
| Disk | Free space for workspace | Derived Zarr cache and exports grow with projects |
| MATLAB / Octave | Optional | Only for MATLAB Studio script execution |
| Network | Not required | Local-first application |

## Portable package

1. Unpack the supplied release directory to a location where you have read/execute permission.
2. Keep bundled files adjacent — do not move `_internal/` away from the executable.
3. Create or choose a **writable workspace folder outside** the install directory for projects, cache, and exports.
4. Launch `IonogramMorphologyLab.exe` (or the platform entry point documented in the release notes).
5. On first launch, select **English** or **Русский**; change later in **Settings → General → Interface language**.

The portable build includes bundled documentation, rule packs, synthetic teaching data, and optional MATLAB Studio assets. It does **not** install a MATLAB runtime.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -e ".[dev]"
python -m ionogram_morphology_lab.app.main
```

Verify before contributing:

```bash
python -m pytest
python scripts/validate_version_consistency.py
python scripts/check_repository_hygiene.py
python scripts/validate_readme.py
python scripts/validate_docs.py
```

Build scripts under `packaging/` are for release maintainers; generated binaries under `dist/` are not source-controlled.

## First run checklist

1. Choose interface language.
2. On **Home**, create **New Project** in your writable workspace.
3. Import a teaching file from [`synthetic_data/`](../synthetic_data/) before research MAT.
4. Open **Data Audit** and confirm array shape and warnings.
5. Complete or select an **Instrument Profile** with honest verification status.
6. Run **Viewer → Build cache** when prompted for derived Zarr storage.
7. Execute a small **Batch Analysis** and review **Results** as candidate proposals only.

## Optional MATLAB Studio backends

Configure in **Settings → MATLAB**:

| Backend ID | When to use |
|------------|-------------|
| `none` | Library and manifests only; execution disabled |
| `matlab_engine` | Local licensed MATLAB with Engine API |
| `external_matlab` | External `matlab -batch` invocation |
| `octave` | GNU Octave when installed and on PATH |

Detection may report `none` on machines without MATLAB — this is valid. Core workflows continue without script execution.

## Removal and data retention

To remove a portable deployment, delete the release directory **after** archiving required projects, exports, and provenance records from your workspace. Source MAT files imported into projects are not modified by normal analysis; deleting the install folder does not delete your workspace unless you stored projects inside it.

## Troubleshooting installation

| Symptom | Action |
|---------|--------|
| Application will not start | Confirm VC++ runtime / bundled deps intact; run from source with `pip install -e ".[dev]"` |
| Cannot create project | Point workspace to a writable folder outside Program Files |
| Import fails immediately | See [Troubleshooting](TROUBLESHOOTING_EN.md) and [Data formats](DATA_FORMATS.md) |
| MATLAB backend unavailable | Use built-in methods; see [MATLAB Studio guide](MATLAB_STUDIO_GUIDE_EN.md) |

## Related documentation

- [User Guide](USER_GUIDE_EN.md)
- [Scientific Guide](SCIENTIFIC_GUIDE_EN.md)
- [FAQ](FAQ_EN.md)
- [Security reporting](../SECURITY.md)
