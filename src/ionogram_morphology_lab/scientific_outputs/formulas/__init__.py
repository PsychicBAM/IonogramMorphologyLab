"""Executable scientific formula helpers (Phase 4A). Not wired into RuleEngine."""

from ionogram_morphology_lab.scientific_outputs.formulas.axes import bin_to_mhz, bin_to_nominal_height_km
from ionogram_morphology_lab.scientific_outputs.formulas.trace_metrics import local_width_bins
from ionogram_morphology_lab.scientific_outputs.formulas.virtual_height import (
    assert_nominal_not_true_height,
    virtual_height_from_group_delay,
)

__all__ = [
    "bin_to_mhz",
    "bin_to_nominal_height_km",
    "local_width_bins",
    "virtual_height_from_group_delay",
    "assert_nominal_not_true_height",
]
