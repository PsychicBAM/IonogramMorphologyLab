"""Project-heuristic trace metrics — labelled as heuristics, not literature equations."""

from __future__ import annotations

import numpy as np

from ionogram_morphology_lab.scientific_outputs.quantity import ScientificQuantity


def local_width_bins(mask_1d: np.ndarray, *, profile_id: str = "") -> ScientificQuantity:
    """Count contiguous True bins in a 1-D trace mask (project heuristic).

    Requires a one-dimensional input. Does not silently ravel() higher-rank arrays.
    """
    arr = np.asarray(mask_1d)
    if arr.ndim != 1:
        q = ScientificQuantity.invalid(
            name="local_trace_width",
            symbol="w_bins",
            unit="bins",
            reason="wrong_dimensionality_requires_1d",
            formula_id="HEUR_IML_TRACE_WIDTH_BINS",
            source_id="A2_PROTOCOL",
            profile_id=profile_id,
        )
        q.metadata = {"ndim": int(arr.ndim), "shape": list(arr.shape)}
        return q
    if arr.size == 0:
        return ScientificQuantity.invalid(
            name="local_trace_width",
            symbol="w_bins",
            unit="bins",
            reason="empty_input",
            formula_id="HEUR_IML_TRACE_WIDTH_BINS",
            source_id="A2_PROTOCOL",
            profile_id=profile_id,
        )
    if not np.issubdtype(arr.dtype, np.bool_) and not np.issubdtype(arr.dtype, np.number):
        return ScientificQuantity.invalid(
            name="local_trace_width",
            symbol="w_bins",
            unit="bins",
            reason="wrong_dtype",
            formula_id="HEUR_IML_TRACE_WIDTH_BINS",
            source_id="A2_PROTOCOL",
            profile_id=profile_id,
        )
    if np.issubdtype(arr.dtype, np.floating) and (np.isnan(arr).any() or np.isinf(arr).any()):
        return ScientificQuantity.invalid(
            name="local_trace_width",
            symbol="w_bins",
            unit="bins",
            reason="nan_or_inf_in_mask",
            formula_id="HEUR_IML_TRACE_WIDTH_BINS",
            source_id="A2_PROTOCOL",
            profile_id=profile_id,
        )
    bits = np.asarray(arr, dtype=bool)
    if not bits.any():
        width = 0
    else:
        # Longest contiguous True run
        padded = np.concatenate([[False], bits, [False]])
        edges = np.diff(padded.astype(np.int8))
        starts = np.where(edges == 1)[0]
        ends = np.where(edges == -1)[0]
        width = int(np.max(ends - starts)) if len(starts) else 0
    return ScientificQuantity(
        name="local_trace_width",
        symbol="w_bins",
        value=width,
        unit="bins",
        formula_id="HEUR_IML_TRACE_WIDTH_BINS",
        source_id="A2_PROTOCOL",
        profile_id=profile_id,
        calibration_status="project_heuristic",
        metadata={"classification": "project_engineering_heuristic"},
    )
