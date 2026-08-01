"""Instrument / data profile schema and loaders."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir


ALLOWED_VERIFICATION = ("verified", "provisional", "user-defined-unverified")


@dataclass
class InstrumentProfile:
    profile_id: str
    profile_name: str
    institution: str = ""
    instrument: str = ""
    station_name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    mat_version: str = "v5_or_v7"
    amplitude_variable_name: str = "Amp_all"
    phase_variable_name: str | None = None
    frequency_variable_name: str | None = "ff"
    time_variable_name: str | None = None
    matrix_layout: str = "frames_stacked_rows"
    row_major: bool = True
    frames_per_file: int = 1440
    height_bins: int = 256
    frequency_bins: int = 400
    frequency_values: list[float] = field(default_factory=list)
    frequency_start_mhz: float | None = None
    frequency_step_mhz: float | None = None
    frequency_end_mhz: float | None = None
    nominal_range_km_per_bin: float | None = 2.5
    range_axis_label_en: str = "Nominal virtual height"
    range_axis_label_ru: str = "Номинальная виртуальная высота"
    time_mapping: str = "matlab_index_minus_1_minute"
    timezone: str = "Europe/Moscow"
    missing_data_representation: str = "NaN_or_zero"
    amplitude_units: str = "unknown"
    scaling: str = "raw"
    source_documentation: list[str] = field(default_factory=list)
    profile_verification_status: str = "provisional"
    expected_amplitude_shape: list[int] = field(default_factory=lambda: [368640, 400])
    warnings: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate_status(self) -> None:
        if self.profile_verification_status not in ALLOWED_VERIFICATION:
            raise ValueError(f"invalid_verification_status:{self.profile_verification_status}")
        if self.profile_verification_status == "user-defined-unverified":
            # never present as instrument-verified
            pass


def profiles_dir() -> Path:
    return app_root() / "config" / "instrument_profiles"


def load_profile(path: Path | str) -> InstrumentProfile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return InstrumentProfile(**{k: v for k, v in data.items() if k in InstrumentProfile.__dataclass_fields__})


def save_profile(profile: InstrumentProfile, path: Path | str | None = None) -> Path:
    profile.validate_status()
    if path is None:
        path = profiles_dir() / f"{profile.profile_id}.yaml"
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(
        yaml.safe_dump(profile.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def list_profiles() -> list[Path]:
    d = profiles_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.yaml"))


def frequency_axis_from_profile(profile: InstrumentProfile) -> list[float]:
    if profile.frequency_values:
        return list(profile.frequency_values)
    if (
        profile.frequency_start_mhz is not None
        and profile.frequency_step_mhz is not None
        and profile.frequency_bins
    ):
        start = profile.frequency_start_mhz
        step = profile.frequency_step_mhz
        return [start + i * step for i in range(profile.frequency_bins)]
    return list(range(profile.frequency_bins))


def range_axis_from_profile(profile: InstrumentProfile) -> list[float]:
    scale = profile.nominal_range_km_per_bin or 1.0
    return [i * scale for i in range(profile.height_bins)]
