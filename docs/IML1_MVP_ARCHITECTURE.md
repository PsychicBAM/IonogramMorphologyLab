# IML-1 MVP Architecture

Desktop: PySide6. Package: `ionogram_morphology_lab` under `src/`.
Layers: security/blocklist → importers/cache → instrument_profiles → rendering → segmentation/features → similarity → rules/disagreement/reference_atlas → projects/database → reports → UI.
Workspaces hold runs; SQLite stores metadata only; MAT sources remain untouched.
Future ML via `classifiers.interfaces`; context via `plugins.context` (disabled for morphology).
