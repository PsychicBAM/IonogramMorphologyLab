# Ionogram Morphology Lab 1.0.0

Released as the first v1.0 product documentation and validation baseline.

## Highlights
- Bilingual first-launch experience and persistent interface language in **Settings → General → Interface language**; no top EN/RU toolbar actions.
- Project workflow for MAT import, audit, derived read-only cache, frame work, features/rules, expert decisions, and reproducible reports.
- Analysis modes: `fast_preview`, `standard`, `scientific_strict` (recommended default), and `custom`.
- Optional MATLAB Studio with script library, manifests, plugin registry, isolated runner, and MATLAB/Octave/no-backend handling.
- Model Lab for research/development training with model cards, grouped splitting, abstention, and explicit development labels.
- Optional Protected Scientific Study mode, disabled by default.

## Compatibility and packaging
Portable release target: `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe`. Installer target, when Inno Setup is available: `installer\IonogramMorphologyLab_Setup_1.0.0.exe`.

## Scientific notes
Automatic outputs remain candidate results. Models are development/research use only unless externally validated. Source MAT files remain read-only by default. A missing backend or null confidence is reported honestly and is never converted into success or calibrated certainty.

## Known limits
MATLAB execution requires a separately available backend. Instrument-profile and method validity depend on documented evidence. Protected Study mode is a configurable safeguard, not a replacement for secure storage or governance.
