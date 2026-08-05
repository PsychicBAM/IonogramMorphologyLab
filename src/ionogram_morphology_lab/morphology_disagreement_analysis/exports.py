"""Export helpers for disagreement analysis bundles."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
    MorphologyDisagreementAnalysisStore,
)


def export_analysis(
    store: MorphologyDisagreementAnalysisStore,
    analysis_id: str,
    dest: Path | str,
) -> Path:
    return store.export_bundle(analysis_id, Path(dest))
