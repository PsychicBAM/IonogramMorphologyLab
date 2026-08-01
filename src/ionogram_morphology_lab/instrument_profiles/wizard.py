"""Instrument Profile Wizard state machine (14 steps)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.instrument_profiles.schema import InstrumentProfile, save_profile


WIZARD_STEPS = [
    "select_sample_mat",
    "show_variables_shapes",
    "select_amplitude_variable",
    "identify_frame_dimension",
    "identify_frequency_dimension",
    "identify_range_dimension",
    "preview_one_frame",
    "verify_orientation",
    "assign_frequency_axis",
    "assign_range_axis",
    "define_time_mapping",
    "save_profile",
    "run_validation",
    "mark_verification_status",
]


@dataclass
class ProfileWizardState:
    step_index: int = 0
    sample_mat: str | None = None
    inventory: dict[str, Any] | None = None
    amplitude_variable: str = "Amp_all"
    frames_per_file: int = 1440
    height_bins: int = 256
    frequency_bins: int = 400
    frequency_start_mhz: float | None = None
    frequency_step_mhz: float | None = None
    nominal_range_km_per_bin: float = 2.5
    time_mapping: str = "matlab_index_minus_1_minute"
    orientation_ok: bool = False
    profile_id: str = "user_profile"
    profile_name: str = "User-defined profile"
    verification_status: str = "user-defined-unverified"
    validation_messages: list[str] = field(default_factory=list)
    preview_frame_index: int = 1

    def current_step(self) -> str:
        return WIZARD_STEPS[min(self.step_index, len(WIZARD_STEPS) - 1)]

    def next_step(self) -> str:
        self.step_index = min(self.step_index + 1, len(WIZARD_STEPS) - 1)
        return self.current_step()

    def load_sample(self, path: Path | str) -> dict[str, Any]:
        inv = inventory_mat(path)
        self.sample_mat = str(path)
        self.inventory = inv.to_dict()
        self.step_index = 1
        return self.inventory

    def build_profile(self) -> InstrumentProfile:
        status = self.verification_status
        if status not in ("verified", "provisional", "user-defined-unverified"):
            status = "user-defined-unverified"
        # User-defined must never be presented as instrument-verified
        if status == "verified" and self.profile_id.startswith("user"):
            status = "user-defined-unverified"
        return InstrumentProfile(
            profile_id=self.profile_id,
            profile_name=self.profile_name,
            amplitude_variable_name=self.amplitude_variable,
            frames_per_file=self.frames_per_file,
            height_bins=self.height_bins,
            frequency_bins=self.frequency_bins,
            frequency_start_mhz=self.frequency_start_mhz,
            frequency_step_mhz=self.frequency_step_mhz,
            nominal_range_km_per_bin=self.nominal_range_km_per_bin,
            time_mapping=self.time_mapping,
            profile_verification_status=status,
            expected_amplitude_shape=[
                self.frames_per_file * self.height_bins,
                self.frequency_bins,
            ],
            warnings=[
                "nominal virtual-height axis",
                "not true physical height",
                "archive time interpretation may be provisional",
                "user-defined profile — not instrument-verified"
                if status == "user-defined-unverified"
                else "profile verification status: " + status,
            ],
        )

    def save(self) -> Path:
        profile = self.build_profile()
        path = save_profile(profile)
        self.step_index = max(self.step_index, 11)
        return path

    def validate(self) -> list[str]:
        msgs: list[str] = []
        if not self.sample_mat:
            msgs.append("no_sample_mat")
        else:
            try:
                loaded = load_amplitude_matrix(self.sample_mat, self.amplitude_variable)
                expected = self.frames_per_file * self.height_bins
                if loaded.data.shape[0] != expected or loaded.data.shape[1] != self.frequency_bins:
                    msgs.append(f"shape_mismatch:{loaded.data.shape}")
                else:
                    msgs.append("shape_ok")
            except Exception as exc:  # noqa: BLE001
                msgs.append(f"load_failed:{exc}")
        if self.verification_status == "verified":
            msgs.append("WARNING: verified status requires documented instrument evidence")
        self.validation_messages = msgs
        self.step_index = max(self.step_index, 12)
        return msgs


def preview_frame_from_wizard(state: ProfileWizardState) -> np.ndarray:
    if not state.sample_mat:
        raise ValueError("no_sample_mat")
    loaded = load_amplitude_matrix(state.sample_mat, state.amplitude_variable)
    amp = loaded.data
    if amp.ndim == 2 and amp.shape[0] == state.frames_per_file * state.height_bins:
        i = state.preview_frame_index
        r0 = (i - 1) * state.height_bins
        r1 = i * state.height_bins
        return np.array(amp[r0:r1, :], copy=True)
    if amp.ndim == 2:
        return np.array(amp, copy=True)
    raise ValueError("unsupported_preview_layout")
