"""Optional physical-context plugins — DISABLED for morphology MVP (IML-1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ContextPlugin(ABC):
    """Future: solar zenith, sunrise/sunset, F10.7, Kp, Dst, AE, station metadata."""

    name: str = "context"
    enabled_for_morphology: bool = False

    @abstractmethod
    def compute(self, frame_meta: dict[str, Any]) -> dict[str, Any]:
        ...


class DisabledContextPlugin(ContextPlugin):
    name = "disabled_context"
    enabled_for_morphology = False

    def compute(self, frame_meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "disabled_in_morphology_mvp",
            "solar_zenith_angle": None,
            "sunrise_sunset": None,
            "high_altitude_illumination": None,
            "F10_7": None,
            "Kp": None,
            "Dst": None,
            "AE": None,
            "note": (
                "Context variables must not classify morphology in IML-1. "
                "Morphology and physical context remain separate."
            ),
        }
