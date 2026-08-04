"""Provisional axis conversions — require verified axis metadata."""

from __future__ import annotations

import math

from ionogram_morphology_lab.scientific_outputs.quantity import ScientificQuantity


def _require_int_bin_index(bin_index_0based: object) -> tuple[int | None, str]:
    """Reject bool / float / non-integral values — never silently truncate 3.8 → 3."""
    if isinstance(bin_index_0based, bool):
        return None, "boolean_bin_index"
    if isinstance(bin_index_0based, int):
        return int(bin_index_0based), ""
    # Allow numpy integer scalars only
    try:
        import numpy as np

        if isinstance(bin_index_0based, np.integer):
            return int(bin_index_0based), ""
    except Exception:  # noqa: BLE001
        pass
    if isinstance(bin_index_0based, float):
        return None, "fractional_or_float_bin_index"
    return None, "non_integer_bin_index"


def bin_to_mhz(
    bin_index_0based: int,
    *,
    start_mhz: float,
    step_mhz: float,
    frequency_bins: int,
    profile_id: str = "kfu_cyclone_2013_2014",
    axis_verified: bool = True,
) -> ScientificQuantity:
    if not axis_verified:
        return ScientificQuantity.invalid(
            name="frequency",
            symbol="f",
            unit="MHz",
            reason="frequency_axis_not_verified",
            formula_id="HEUR_BIN_TO_MHZ",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    bin_i, bin_reason = _require_int_bin_index(bin_index_0based)
    if bin_i is None:
        return ScientificQuantity.invalid(
            name="frequency",
            symbol="f",
            unit="MHz",
            reason=bin_reason,
            formula_id="HEUR_BIN_TO_MHZ",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    if not (math.isfinite(start_mhz) and math.isfinite(step_mhz)):
        return ScientificQuantity.invalid(
            name="frequency",
            symbol="f",
            unit="MHz",
            reason="non_finite_axis_parameters",
            formula_id="HEUR_BIN_TO_MHZ",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    if step_mhz <= 0 or frequency_bins <= 0:
        return ScientificQuantity.invalid(
            name="frequency",
            symbol="f",
            unit="MHz",
            reason="invalid_axis_parameters",
            formula_id="HEUR_BIN_TO_MHZ",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    if not (0 <= bin_i < int(frequency_bins)):
        return ScientificQuantity.invalid(
            name="frequency",
            symbol="f",
            unit="MHz",
            reason="bin_out_of_range",
            formula_id="HEUR_BIN_TO_MHZ",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    value = float(start_mhz) + float(bin_i) * float(step_mhz)
    return ScientificQuantity(
        name="frequency",
        symbol="f",
        value=value,
        unit="MHz",
        formula_id="HEUR_BIN_TO_MHZ",
        source_id="CALSTAT",
        profile_id=profile_id,
        calibration_status="provisionally_verified",
        metadata={"bin_index_0based": bin_i},
    )


def bin_to_nominal_height_km(
    bin_index_0based: int,
    *,
    km_per_bin: float,
    height_bins: int,
    profile_id: str = "kfu_cyclone_2013_2014",
    axis_verified: bool = True,
) -> ScientificQuantity:
    if not axis_verified:
        return ScientificQuantity.invalid(
            name="nominal_virtual_height",
            symbol="h'_nom",
            unit="km",
            reason="range_axis_not_verified",
            formula_id="HEUR_BIN_TO_NOMINAL_HEIGHT",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    bin_i, bin_reason = _require_int_bin_index(bin_index_0based)
    if bin_i is None:
        return ScientificQuantity.invalid(
            name="nominal_virtual_height",
            symbol="h'_nom",
            unit="km",
            reason=bin_reason,
            formula_id="HEUR_BIN_TO_NOMINAL_HEIGHT",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    if not math.isfinite(km_per_bin) or km_per_bin <= 0 or height_bins <= 0:
        return ScientificQuantity.invalid(
            name="nominal_virtual_height",
            symbol="h'_nom",
            unit="km",
            reason="invalid_axis_parameters",
            formula_id="HEUR_BIN_TO_NOMINAL_HEIGHT",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    if not (0 <= bin_i < int(height_bins)):
        return ScientificQuantity.invalid(
            name="nominal_virtual_height",
            symbol="h'_nom",
            unit="km",
            reason="bin_out_of_range",
            formula_id="HEUR_BIN_TO_NOMINAL_HEIGHT",
            source_id="CALSTAT",
            profile_id=profile_id,
        )
    value = float(bin_i) * float(km_per_bin)
    return ScientificQuantity(
        name="nominal_virtual_height",
        symbol="h'_nom",
        value=value,
        unit="km",
        formula_id="HEUR_BIN_TO_NOMINAL_HEIGHT",
        source_id="CALSTAT",
        profile_id=profile_id,
        calibration_status="provisionally_verified",
        metadata={
            "bin_index_0based": bin_i,
            "not_true_height": True,
            "guard": "F002",
        },
    )
