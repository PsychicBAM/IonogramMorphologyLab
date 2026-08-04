"""Multi-frame temporal context — kept separate from single-frame morphology."""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.features.extract import extract_temporal_features


def temporal_conclusion(
    masks: list[np.ndarray],
    *,
    single_frame_morphology: str,
) -> dict[str, Any]:
    """Derive persistence/onset-style notes without overwriting single-frame morphology.

    Returns a separate conclusion block. Does not claim physical continuity of Spread-F.
    """
    feats = extract_temporal_features(masks)
    persistence = feats.get("temporal_persistence")
    agreement = feats.get("neighboring_frame_agreement")
    note = "insufficient_neighbors"
    if len(masks) >= 3 and persistence == persistence:  # not NaN
        if persistence >= 0.55:
            note = "continuation_candidate"
        elif persistence <= 0.15:
            note = "sudden_change_or_artifact_candidate"
        elif 0.15 < persistence < 0.35:
            note = "onset_or_termination_candidate"
        else:
            note = "partial_persistence"
    return {
        "single_frame_morphology": single_frame_morphology,
        "temporal_features": feats,
        "temporal_note": note,
        "n_masks": len(masks),
        "limitations": [
            "Temporal notes are development heuristics on mask overlap only.",
            "They do not confirm physical Spread-F onset/termination.",
            "Single-frame morphology remains the primary candidate.",
        ],
        "persistence": None if persistence != persistence else float(persistence),
        "neighboring_frame_agreement": None if agreement != agreement else float(agreement),
    }
