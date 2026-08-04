#!/usr/bin/env python3
"""Validate knowledge_base/SIGNAL_CONTRACTS.yaml structure and Amp_all frame mapping."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.scientific_outputs.signal_contracts import (  # noqa: E402
    extract_frame_consistent,
    frame_row_range,
    load_signal_contracts,
    phase_automatic_rules_enabled,
    validate_contract_schema,
)


def main() -> int:
    data = load_signal_contracts()
    contracts = data.get("contracts") or []
    errors: list[str] = []
    errors.extend(validate_contract_schema(data))
    if not contracts:
        errors.append("no contracts")
    required = {
        "contract_id",
        "profile_id",
        "variable_name",
        "variable_role",
        "verification_status",
        "allowed_scientific_uses",
        "prohibited_scientific_claims",
        "accepted_shapes",
        "shape_constraints",
        "accepted_dtypes",
        "optional_presence",
        "verification_evidence",
    }
    ids = set()
    for c in contracts:
        cid = c.get("contract_id")
        if cid in ids:
            errors.append(f"duplicate contract_id {cid}")
        ids.add(cid)
        missing = required - set(c)
        if missing:
            errors.append(f"{cid}: missing {sorted(missing)}")
    amp = next((c for c in contracts if c.get("variable_name") == "Amp_all"), None)
    if not amp:
        errors.append("Amp_all contract missing")
    else:
        if list(amp.get("expected_shape") or []) != [368640, 400]:
            errors.append("Amp_all expected_shape must be [368640, 400]")
        if [368640, 400] not in (amp.get("accepted_shapes") or []):
            errors.append("Amp_all accepted_shapes must include [368640, 400]")
        sc = amp.get("shape_constraints") or {}
        if sc.get("rows_per_frame") != 256 or sc.get("frames_per_file") != 1440:
            errors.append("Amp_all shape_constraints rows_per_frame/frames_per_file invalid")
        if amp.get("optional_presence") is not False:
            errors.append("Amp_all optional_presence must be false")
    phs = next((c for c in contracts if c.get("variable_name") == "Phs_all"), None)
    if not phs:
        errors.append("Phs_all contract missing")
    elif phs.get("automatic_rules_enabled"):
        errors.append("Phs_all automatic_rules_enabled must be false")
    if phase_automatic_rules_enabled():
        errors.append("phase_automatic_rules_enabled() returned True")

    for idx, r0, r1 in ((1, 0, 256), (421, 420 * 256, 421 * 256), (1440, 1439 * 256, 1440 * 256)):
        rng = frame_row_range(idx)
        if rng.row_start != r0 or rng.row_end_exclusive != r1:
            errors.append(f"frame {idx} row range {rng.row_start}:{rng.row_end_exclusive} != {r0}:{r1}")

    stack = np.zeros((3 * 256, 400), dtype=float)
    stack[0:256, :] = 1.0
    stack[256:512, :] = 2.0
    stack[512:768, :] = 3.0
    for i, expect in ((1, 1.0), (2, 2.0), (3, 3.0)):
        frame, _ = extract_frame_consistent(stack, i)
        if float(frame.mean()) != expect:
            errors.append(f"extract_frame_consistent frame {i} mean mismatch")

    if errors:
        print("validate_signal_contracts FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print("validate_signal_contracts OK", len(contracts), "contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
