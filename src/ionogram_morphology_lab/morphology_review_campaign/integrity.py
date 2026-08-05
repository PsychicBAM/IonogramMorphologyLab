"""Campaign integrity validation (Phase 4C.3)."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.constants import (
    CAMPAIGN_INTEGRITY_CONTRACT_VERSION,
    CAMPAIGN_PROTOCOL_SCHEMA_VERSION,
    CAMPAIGN_SCHEMA_VERSION,
    PROHIBITED_METRICS,
)
from ionogram_morphology_lab.morphology_review_campaign.models import CampaignManifest
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    assert_no_absolute_paths,
    deterministic_hash,
)
from ionogram_morphology_lab.morphology_review_corpus.integrity import (
    validate_no_production_ruleengine_wiring,
)


def validate_campaign(
    store: MorphologyReviewCampaignStore, campaign_id: str
) -> dict[str, Any]:
    issues: list[str] = []
    info: list[str] = []

    try:
        manifest = store.load_manifest(campaign_id)
        protocol = store.load_protocol(campaign_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "campaign_id": campaign_id,
            "issues": [f"load_failed:{exc}"],
            "info": [],
            "contract_version": CAMPAIGN_INTEGRITY_CONTRACT_VERSION,
        }

    # Schema
    if manifest.schema_version != CAMPAIGN_SCHEMA_VERSION:
        issues.append(f"schema_version:{manifest.schema_version}")
    if protocol.protocol_version != CAMPAIGN_PROTOCOL_SCHEMA_VERSION:
        issues.append(f"protocol_version:{protocol.protocol_version}")

    # Hashes — recompute from stored dicts without mutating on-disk identity fields
    proto_payload = protocol.to_dict()
    stored_ph = proto_payload.pop("protocol_hash", "")
    expected_ph = deterministic_hash(proto_payload)
    if stored_ph != expected_ph:
        issues.append("protocol_hash_mismatch")

    m_payload = manifest.to_dict()
    stored_ch = m_payload.pop("campaign_hash", "")
    expected_ch = deterministic_hash(m_payload)
    if stored_ch != expected_ch:
        issues.append("campaign_hash_mismatch")

    # Absolute paths
    try:
        assert_no_absolute_paths(manifest.to_dict())
        assert_no_absolute_paths(protocol.to_dict())
    except ValueError as exc:
        issues.append(f"absolute_path:{exc}")

    # Cohort links
    role_fps: dict[str, set[str]] = {}
    for link in store.list_cohort_links(campaign_id):
        if link.cohort_id not in store.corpus.list_cohorts():
            issues.append(f"missing_cohort:{link.cohort_id}")
            continue
        cm = store.corpus.load_manifest(link.cohort_id)
        if cm.manifest_hash != link.manifest_hash:
            info.append(
                f"manifest_hash_drift:{link.cohort_id}"
            )
        fps = role_fps.setdefault(link.cohort_role, set())
        for it in store.corpus.load_items(link.cohort_id):
            fp = f"{it.source_sha256}:{it.frame_index}"
            if fp in fps:
                issues.append(
                    f"duplicate_item_role:{link.cohort_role}:{fp}"
                )
            fps.add(fp)

    # Reviewer assignments
    assignments = store.list_assignments(campaign_id)
    plan = manifest.reviewer_plan or {}
    if plan.get("first_reviewer_id") and not any(
        a.role == "first_reviewer" for a in assignments
    ):
        info.append("first_reviewer_plan_without_assignment_row")

    # Current-state invariants
    prog = campaign_progress(store, campaign_id)
    if not prog["invariants"]["comparisons_le_unique"]:
        issues.append("comparisons_exceed_unique_items")
    if not prog["invariants"]["round1_le_unique"]:
        issues.append("round1_exceed_unique_items")
    if not prog["integrity_ok"]:
        issues.extend(prog["integrity_messages"])

    # Raw-history overcount must not drive progress
    for row in prog.get("per_cohort") or []:
        if int(row.get("comparisons_history") or 0) > int(
            row.get("comparisons_current") or 0
        ):
            info.append(
                f"history_gt_current:{row.get('cohort_id')} "
                f"(progress uses current={row.get('comparisons_current')})"
            )

    # Blind export / candidate leakage in campaign manifest
    for key in ("candidate_state", "candidate_label", "ordinal_strength"):
        blob = json_dumps_safe(manifest.to_dict())
        if key in blob:
            issues.append(f"candidate_leakage_in_manifest:{key}")

    # Prohibited metrics as JSON keys only (SHA hex may contain "f1" substrings)
    def _prohibited_keys(payload: Any) -> list[str]:
        found: list[str] = []
        if isinstance(payload, dict):
            for k, v in payload.items():
                if str(k).lower() in PROHIBITED_METRICS:
                    found.append(str(k))
                found.extend(_prohibited_keys(v))
        elif isinstance(payload, list):
            for v in payload:
                found.extend(_prohibited_keys(v))
        return found

    for key in _prohibited_keys(manifest.to_dict()):
        issues.append(f"prohibited_metric:{key}")

    # Production RuleEngine — check repo layout when available
    from pathlib import Path

    pkg_root = Path(__file__).resolve().parents[3]  # .../IonogramMorphologyLab
    engine = pkg_root / "src" / "ionogram_morphology_lab" / "rules" / "engine.py"
    if engine.is_file():
        re_issues = validate_no_production_ruleengine_wiring(pkg_root)
        if re_issues:
            issues.extend(f"ruleengine:{x}" for x in re_issues)
        engine_text = engine.read_text(encoding="utf-8")
        if "morphology_review_campaign" in engine_text:
            issues.append("ruleengine:imports_morphology_review_campaign")

    if protocol.scientifically_validated:
        issues.append("scientifically_validated_must_be_false")
    if not protocol.candidate_shadow_only:
        issues.append("candidate_must_remain_shadow_only")
    if not protocol.second_reviewer_optional and not plan.get("second_reviewer_id"):
        info.append("second_reviewer_marked_required_but_unassigned")

    return {
        "ok": not issues,
        "campaign_id": campaign_id,
        "issues": issues,
        "info": info,
        "contract_version": CAMPAIGN_INTEGRITY_CONTRACT_VERSION,
        "progress": {
            "unique": prog["unique_real_items"],
            "comparisons": prog["comparison_progress"]["completed"],
            "round1": prog["first_blind_progress"]["completed"],
        },
    }


def json_dumps_safe(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)
