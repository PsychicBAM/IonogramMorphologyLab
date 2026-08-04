"""Structured scientific quantities — never unexplained floats for key values."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ScientificQuantity:
    name: str
    symbol: str
    value: float | int | None
    unit: str
    uncertainty: float | None = None
    valid: bool = True
    reason_invalid: str = ""
    formula_id: str = ""
    source_id: str = ""
    profile_id: str = ""
    calibration_status: str = "unavailable"
    processing_version: str = "1.1.1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def invalid(
        cls,
        *,
        name: str,
        symbol: str,
        unit: str,
        reason: str,
        formula_id: str = "",
        source_id: str = "",
        profile_id: str = "",
    ) -> "ScientificQuantity":
        return cls(
            name=name,
            symbol=symbol,
            value=None,
            unit=unit,
            valid=False,
            reason_invalid=reason,
            formula_id=formula_id,
            source_id=source_id,
            profile_id=profile_id,
        )
