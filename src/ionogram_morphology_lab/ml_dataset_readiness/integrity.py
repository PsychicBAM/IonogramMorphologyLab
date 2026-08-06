"""Integrity checks for frozen readiness audits."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    PROHIBITED_METRICS,
    READINESS_PROTOCOL_VERSION,
    TASK_CONTRACTS,
)
from ionogram_morphology_lab.ml_dataset_readiness.models import (
    InventoryItemRecord,
    ReadinessManifest,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    is_absolute_local_path,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES

_CANDIDATE_SUFFIX = re.compile(r"_candidate\b", re.I)


def validate_audit_dir(audit_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    audit_dir = Path(audit_dir)
    mp = audit_dir / "readiness_manifest.json"
    if not mp.exists():
        return {"ok": False, "errors": ["missing_readiness_manifest"], "warnings": []}

    manifest = ReadinessManifest.from_dict(json.loads(mp.read_text(encoding="utf-8")))
    expected = manifest.compute_manifest_hash()
    if manifest.manifest_hash and manifest.manifest_hash != expected:
        errors.append("manifest_hash_mismatch")
    if manifest.task_contract not in TASK_CONTRACTS:
        errors.append("invalid_task_contract")
    if manifest.audit_protocol_version != READINESS_PROTOCOL_VERSION:
        warnings.append(
            f"protocol_version:{manifest.audit_protocol_version}"
            f"!={READINESS_PROTOCOL_VERSION}"
        )

    inv_path = audit_dir / "label_inventory.jsonl"
    rows: list[InventoryItemRecord] = []
    if inv_path.exists():
        for line in inv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(InventoryItemRecord.from_dict(json.loads(line)))
    else:
        if manifest.lifecycle_state in ("frozen", "reviewed", "gate_recorded"):
            errors.append("missing_label_inventory")

    # Unique current-state keys
    seen: set[str] = set()
    for r in rows:
        k = r.identity_key()
        if k in seen:
            errors.append(f"duplicate_current_identity:{k}")
        seen.add(k)
        if r.morphology and r.morphology not in HUMAN_MORPHOLOGY_CODES:
            # empty morphology allowed for missing locked review
            if r.locked_first_review_id:
                errors.append(f"invalid_morphology:{r.item_id}:{r.morphology}")
        # Candidate leakage into expert target fields
        for field in (r.morphology, r.assessability):
            if field and _CANDIDATE_SUFFIX.search(field):
                errors.append(f"candidate_label_leakage:{r.item_id}:{field}")
        for flag in r.interference or []:
            if _CANDIDATE_SUFFIX.search(flag):
                errors.append(f"candidate_interference_leakage:{r.item_id}:{flag}")

    if manifest.inventory_hash and rows:
        payload = [r.to_dict() for r in rows]
        ih = deterministic_hash(payload)
        if ih != manifest.inventory_hash:
            errors.append("inventory_hash_mismatch")

    # Scan exports / markdown for prohibited claim phrases and absolute paths
    claim_re = re.compile(
        r"\b(accuracy|f1[_ ]?score|sensitivity|specificity)\s*[:=]\s*[0-9]",
        re.I,
    )
    for path in audit_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".md", ".csv", ".jsonl", ".txt"}:
            continue
        if path.name == "integrity_report.json":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if claim_re.search(text):
            errors.append(f"forbidden_performance_claim:{path.name}")
        for line in text.splitlines():
            s = line.strip().strip('"').strip("'")
            if s and is_absolute_local_path(s) and ("\\" in s or s.startswith("/Users")):
                errors.append(f"absolute_local_path:{path.name}")
                break
        # JSON structured values
        if path.suffix.lower() in {".json", ".jsonl"}:
            try:
                if path.suffix.lower() == ".json":
                    from ionogram_morphology_lab.morphology_review_corpus.hashing import (
                        assert_no_absolute_paths,
                    )

                    assert_no_absolute_paths(json.loads(text))
                else:
                    from ionogram_morphology_lab.morphology_review_corpus.hashing import (
                        assert_no_absolute_paths,
                    )

                    for line in text.splitlines():
                        if line.strip():
                            assert_no_absolute_paths(json.loads(line))
            except ValueError:
                errors.append(f"absolute_local_path:{path.name}")
            except Exception:
                pass

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "audit_id": manifest.audit_id,
        "manifest_hash": manifest.manifest_hash,
        "inventory_rows": len(rows),
        "task_contract": manifest.task_contract,
        "lifecycle_state": manifest.lifecycle_state,
    }
