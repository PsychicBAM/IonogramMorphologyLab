"""Explicit audit task contracts for ML-A.1."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    PARAMETER_SCALING_UNSUPPORTED_EN,
    PARAMETER_SCALING_UNSUPPORTED_RU,
    TASK_CONTRACTS,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    ASSESSABILITY_CODES,
    HUMAN_MORPHOLOGY_CODES,
    INTERFERENCE_CODES,
)

# Governance states tracked separately from morphology taxonomy
GOVERNANCE_LABEL_STATES = frozenset(
    {
        "indeterminate",
        "not_assessable",
        "abstained",
        "unlocked_draft",
        "missing_locked_review",
    }
)

REQUIRED_FIELDS_BY_CONTRACT: dict[str, tuple[str, ...]] = {
    "spread_f_morphology_classification": (
        "expert_morphology",
        "assessability",
        "interference",
        "locked_first_review_id",
        "source_sha256",
        "frame_index",
    ),
    "assessability_quality_classification": (
        "assessability",
        "ambiguity",
        "interference",
        "source_sha256",
        "frame_index",
    ),
    "interference_classification": (
        "interference",
        "source_sha256",
        "frame_index",
    ),
    "ionogram_parameter_scaling": (
        "parameter_scaling_labels",
        "source_sha256",
        "frame_index",
    ),
}

CONTRACT_LABELS: dict[str, dict[str, str]] = {
    "spread_f_morphology_classification": {
        "en": "Spread-F morphology classification",
        "ru": "Классификация морфологии Spread-F",
    },
    "assessability_quality_classification": {
        "en": "Assessability and quality classification",
        "ru": "Классификация оценимости и качества",
    },
    "interference_classification": {
        "en": "Interference classification",
        "ru": "Классификация помех",
    },
    "ionogram_parameter_scaling": {
        "en": "Ionogram parameter scaling readiness",
        "ru": "Готовность к масштабированию параметров ионограмм",
    },
}


def validate_task_contract(contract_id: str) -> None:
    if contract_id not in TASK_CONTRACTS:
        raise ValueError(f"Unsupported task contract: {contract_id!r}")


def contract_display(contract_id: str, lang: str = "en") -> str:
    validate_task_contract(contract_id)
    row = CONTRACT_LABELS[contract_id]
    return row.get(lang) or row["en"]


def contract_descriptor(contract_id: str) -> dict[str, Any]:
    validate_task_contract(contract_id)
    desc: dict[str, Any] = {
        "task_contract": contract_id,
        "label_en": CONTRACT_LABELS[contract_id]["en"],
        "label_ru": CONTRACT_LABELS[contract_id]["ru"],
        "required_target_fields": list(REQUIRED_FIELDS_BY_CONTRACT[contract_id]),
        "supports_parameter_scaling": False,
        "parameter_scaling_status_en": "",
        "parameter_scaling_status_ru": "",
    }
    if contract_id == "spread_f_morphology_classification":
        desc["morphology_taxonomy"] = sorted(HUMAN_MORPHOLOGY_CODES)
        desc["governance_states"] = sorted(GOVERNANCE_LABEL_STATES)
        desc["assessability_codes"] = sorted(ASSESSABILITY_CODES)
        desc["interference_codes"] = sorted(INTERFERENCE_CODES)
    elif contract_id == "assessability_quality_classification":
        desc["assessability_codes"] = sorted(ASSESSABILITY_CODES)
        desc["interference_codes"] = sorted(INTERFERENCE_CODES)
    elif contract_id == "interference_classification":
        desc["interference_codes"] = sorted(INTERFERENCE_CODES)
    elif contract_id == "ionogram_parameter_scaling":
        desc["supports_parameter_scaling"] = False
        desc["parameter_scaling_status_en"] = PARAMETER_SCALING_UNSUPPORTED_EN
        desc["parameter_scaling_status_ru"] = PARAMETER_SCALING_UNSUPPORTED_RU
        desc["example_parameters"] = [
            "foF2",
            "foF1",
            "foE",
            "foEs",
            "fmin",
            "fbEs",
            "h'F",
            "h'E",
            "h'Es",
            "hmF2",
            "frequency_profile",
        ]
        desc["note_en"] = (
            "Do not infer numeric ionospheric-parameter ground truth from morphology labels."
        )
    return desc
