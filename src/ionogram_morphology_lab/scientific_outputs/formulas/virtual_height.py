"""F001 / F002 — virtual height from group delay; true-height guard."""

from __future__ import annotations

import math

import numpy as np

from ionogram_morphology_lab.scientific_outputs.quantity import ScientificQuantity

C_KM_PER_S = 299792.458


def virtual_height_from_group_delay(
    tau_g_s: float | np.ndarray,
    *,
    profile_id: str = "",
) -> ScientificQuantity | list[ScientificQuantity]:
    """h' = c * tau_g / 2. Rejects NaN/Inf/negative delays."""

    def _one(tau: float) -> ScientificQuantity:
        if tau is None or not math.isfinite(float(tau)):
            return ScientificQuantity.invalid(
                name="virtual_height",
                symbol="h'",
                unit="km",
                reason="non_finite_group_delay",
                formula_id="F001",
                source_id="A3L007",
                profile_id=profile_id,
            )
        if float(tau) < 0:
            return ScientificQuantity.invalid(
                name="virtual_height",
                symbol="h'",
                unit="km",
                reason="negative_group_delay",
                formula_id="F001",
                source_id="A3L007",
                profile_id=profile_id,
            )
        value = C_KM_PER_S * float(tau) / 2.0
        return ScientificQuantity(
            name="virtual_height",
            symbol="h'",
            value=value,
            unit="km",
            formula_id="F001",
            source_id="A3L007",
            profile_id=profile_id,
            calibration_status="source_supported",
            metadata={"tau_g_s": float(tau), "c_km_per_s": C_KM_PER_S},
        )

    if isinstance(tau_g_s, np.ndarray):
        return [_one(float(x)) for x in np.asarray(tau_g_s).ravel()]
    return _one(float(tau_g_s))


def assert_nominal_not_true_height(label: str) -> None:
    """F002 guard — raise if a caller tries to label nominal height as true height."""
    lowered = (label or "").lower()
    if "true height" in lowered or "истинн" in lowered:
        raise ValueError("F002: nominal virtual height must not be labelled as true height")
