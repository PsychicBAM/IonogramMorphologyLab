"""Classify MAT inventory entries for primary-source activation (Phase 4B.2d)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.importers.mat_inventory import inventory_mat
from ionogram_morphology_lab.scientific_outputs.signal_contracts import (
    extract_frame_consistent,
    get_contract_by_variable,
    match_inventory_to_contracts,
)


class SourceRole(str, Enum):
    PRIMARY_IONOGRAM_SOURCE = "primary_ionogram_source"
    AUXILIARY_ARCHIVE_PRODUCT = "auxiliary_archive_product"
    UNSUPPORTED = "unsupported"
    UNRESOLVED = "unresolved"
    MISSING = "missing"


@dataclass
class SourceClassification:
    path: Path
    role: SourceRole
    can_activate: bool
    primary_variable: str = "Amp_all"
    variable_present: bool = False
    contract_id: str = ""
    contract_ok: bool = False
    shape: str = ""
    dtype: str = ""
    variables: list[str] = field(default_factory=list)
    product_type: str = ""
    reason_code: str = ""
    reason_detail: str = ""
    frame_extract_ok: bool = False
    audit_status: str = ""

    def badge_key(self, *, is_active: bool, file_missing: bool = False) -> str:
        if file_missing or self.role == SourceRole.MISSING:
            return "unavailable"
        if is_active:
            return "active"
        if self.role == SourceRole.PRIMARY_IONOGRAM_SOURCE:
            return "inactive"
        if self.role == SourceRole.AUXILIARY_ARCHIVE_PRODUCT:
            return "auxiliary"
        return "incompatible"


def localize_badge(key: str, language: str) -> str:
    ru = language == "ru"
    mapping = {
        "active": ("Активный источник", "Active source"),
        "inactive": ("Неактивный файл", "Inactive file"),
        "auxiliary": ("Вспомогательный файл", "Auxiliary file"),
        "incompatible": ("Несовместимый файл", "Incompatible file"),
        "unavailable": ("Файл недоступен", "File unavailable"),
    }
    pair = mapping.get(key, mapping["inactive"])
    return pair[0] if ru else pair[1]


def localize_role_message(code: str, language: str, *, variable: str = "Amp_all") -> str:
    ru = language == "ru"
    if code == "missing_amp_all":
        return (
            f"Этот файл не содержит поддерживаемую переменную {variable} и не может "
            "использоваться как основной источник ионограммы."
            if ru
            else f"This file does not contain the supported variable {variable} and cannot "
            "be used as the primary ionogram source."
        )
    if code == "imported_auxiliary":
        return (
            f"Файл добавлен в проект как вспомогательный, но не выбран как активный: "
            f"переменная {variable} отсутствует."
            if ru
            else f"File added to the project as auxiliary, but not selected as active: "
            f"variable {variable} is missing."
        )
    if code == "viewer_missing_variable":
        return (
            f"В выбранном MAT-файле нет переменной {variable}, необходимой для "
            "просмотра и диагностики ионограмм."
            if ru
            else f"The selected MAT file does not contain variable {variable}, which is "
            "required for ionogram viewing and diagnostics."
        )
    if code == "choose_compatible":
        return "Выбрать подходящий Am_all-файл" if ru else "Choose a suitable Am_all file"
    if code == "no_active_selected":
        return "Активный источник не выбран." if ru else "No active source is selected."
    if code == "pick_from_project":
        return (
            "Выбрать активный файл из проекта"
            if ru
            else "Choose active file from project"
        )
    if code == "activated":
        return "Файл выбран как активный источник:" if ru else "File selected as the active source:"
    if code == "frame_extract_failed":
        return (
            "Не удалось извлечь кадр из MAT-файла."
            if ru
            else "Failed to extract a frame from the MAT file."
        )
    if code == "file_unreadable":
        return "MAT-файл недоступен или нечитаем." if ru else "MAT file is missing or unreadable."
    if code == "contract_mismatch":
        return "Контракт сигнала несовместим." if ru else "Signal contract is incompatible."
    return code


def classify_mat_source(
    path: Path | str,
    profile: dict[str, Any] | None = None,
    *,
    try_frame: bool = True,
) -> SourceClassification:
    """Classify whether a MAT may become the primary active ionogram source."""
    p = Path(path)
    profile = profile or {}
    amp = str(profile.get("amplitude_variable_name") or "Amp_all")
    height = int(profile.get("height_bins") or 256)
    width = int(profile.get("frequency_bins") or 400)

    if not p.is_file():
        return SourceClassification(
            path=p,
            role=SourceRole.MISSING,
            can_activate=False,
            primary_variable=amp,
            reason_code="file_unreadable",
            audit_status="missing",
        )

    inv = inventory_mat(p)
    var_names = [v.name for v in inv.variables]
    shape = ""
    dtype = ""
    amp_info = next((v for v in inv.variables if v.name == amp), None)
    if amp_info is not None:
        shape = "×".join(str(int(x)) for x in amp_info.shape) if amp_info.shape else ""
        dtype = str(amp_info.dtype or "")

    product = _guess_product_type(p.name, var_names)
    matches = match_inventory_to_contracts(inv.variables)
    amp_match = next((m for m in matches if m.get("variable_name") == amp), None)
    contract = get_contract_by_variable(amp) or {}
    contract_id = str(contract.get("contract_id") or "")
    contract_ok = bool(amp_match and amp_match.get("present") and amp_match.get("shape_ok"))

    if not inv.readable:
        return SourceClassification(
            path=p,
            role=SourceRole.UNSUPPORTED,
            can_activate=False,
            primary_variable=amp,
            variables=var_names,
            product_type=product,
            reason_code="file_unreadable",
            reason_detail=str(inv.error or ""),
            audit_status=inv.status,
        )

    if amp not in var_names:
        # ALL_data / maps without Amp_all → auxiliary, not primary
        role = (
            SourceRole.AUXILIARY_ARCHIVE_PRODUCT
            if any(n in var_names for n in ("A_map_F", "H_map_F", "Phs_all"))
            or product.startswith("ALL_data")
            else SourceRole.UNSUPPORTED
        )
        return SourceClassification(
            path=p,
            role=role,
            can_activate=False,
            primary_variable=amp,
            variable_present=False,
            contract_id=contract_id,
            contract_ok=False,
            shape=shape,
            dtype=dtype,
            variables=var_names,
            product_type=product,
            reason_code="missing_amp_all",
            audit_status="insufficient_metadata",
        )

    frame_ok = False
    detail = ""
    if try_frame:
        try:
            from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix

            loaded = load_amplitude_matrix(p, variable=amp)
            extract_frame_consistent(loaded.data, 1, height_bins=height, frequency_bins=width)
            frame_ok = True
            if not shape:
                shape = "×".join(str(int(x)) for x in loaded.data.shape)
            dtype = str(getattr(loaded.data, "dtype", dtype) or dtype)
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
            return SourceClassification(
                path=p,
                role=SourceRole.UNSUPPORTED,
                can_activate=False,
                primary_variable=amp,
                variable_present=True,
                contract_id=contract_id,
                contract_ok=contract_ok,
                shape=shape,
                dtype=dtype,
                variables=var_names,
                product_type=product,
                reason_code="frame_extract_failed",
                reason_detail=detail,
                frame_extract_ok=False,
                audit_status="unreadable",
            )

    if not contract_ok:
        # Variable present but shape/contract mismatch — still allow cautious activation
        # only when frame extraction succeeded (readable primary ionogram stack).
        if frame_ok:
            return SourceClassification(
                path=p,
                role=SourceRole.PRIMARY_IONOGRAM_SOURCE,
                can_activate=True,
                primary_variable=amp,
                variable_present=True,
                contract_id=contract_id or "kfu_amp_all_v1",
                contract_ok=False,
                shape=shape,
                dtype=dtype,
                variables=var_names,
                product_type=product or "Am_all",
                reason_code="",
                frame_extract_ok=True,
                audit_status="valid_with_warning",
            )
        return SourceClassification(
            path=p,
            role=SourceRole.UNSUPPORTED,
            can_activate=False,
            primary_variable=amp,
            variable_present=True,
            contract_id=contract_id,
            contract_ok=False,
            shape=shape,
            dtype=dtype,
            variables=var_names,
            product_type=product,
            reason_code="contract_mismatch",
            frame_extract_ok=False,
            audit_status="unexpected_shape",
        )

    return SourceClassification(
        path=p,
        role=SourceRole.PRIMARY_IONOGRAM_SOURCE,
        can_activate=True,
        primary_variable=amp,
        variable_present=True,
        contract_id=contract_id or "kfu_amp_all_v1",
        contract_ok=True,
        shape=shape,
        dtype=dtype,
        variables=var_names,
        product_type=product or "Am_all",
        reason_code="",
        frame_extract_ok=frame_ok,
        audit_status="valid",
    )


def _guess_product_type(filename: str, variables: list[str]) -> str:
    name = filename.lower()
    if "am_all" in name or "amp_all" in name:
        return "Am_all"
    if "all_data" in name:
        return "ALL_data"
    if "a_map" in name:
        return "A_map_F"
    if "h_map" in name:
        return "H_map_F"
    if "Amp_all" in variables:
        return "Am_all"
    if "A_map_F" in variables or "H_map_F" in variables:
        return "ALL_data"
    return "unresolved"


def format_missing_variable_user_message(exc: BaseException | str, language: str) -> tuple[str, str]:
    """Return (user_facing, technical_detail) for missing_variable errors."""
    text = str(exc)
    variable = "Amp_all"
    if "missing_variable:" in text:
        variable = text.split("missing_variable:", 1)[-1].strip() or variable
    user = localize_role_message("viewer_missing_variable", language, variable=variable)
    return user, text
