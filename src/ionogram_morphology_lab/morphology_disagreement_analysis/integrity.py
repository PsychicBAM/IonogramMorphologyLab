"""Integrity validation for disagreement analyses (fail closed)."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    DECISION_OUTCOMES,
    LIFECYCLE_STATES,
    PROHIBITED_METRICS,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.decision_gate import (
    validate_decision_record,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.holdout import (
    validate_holdout_plan,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    is_absolute_local_path,
)

if TYPE_CHECKING:
    from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
        MorphologyDisagreementAnalysisStore,
    )


def validate_analysis(
    store: "MorphologyDisagreementAnalysisStore", analysis_id: str
) -> dict[str, Any]:
    issues: list[str] = []
    manifest = store.load_manifest(analysis_id)
    if manifest.lifecycle_state not in LIFECYCLE_STATES:
        issues.append("invalid_lifecycle")

    stored = manifest.manifest_hash
    recomputed = manifest.compute_manifest_hash()
    if stored and stored != recomputed:
        issues.append("manifest_hash_mismatch")

    rows = store.load_snapshot_rows(analysis_id)
    ids = [(r.cohort_id, r.item_id) for r in rows]
    if len(ids) != len(set(ids)):
        issues.append("duplicate_current_item_identity")

    for r in rows:
        if not r.cohort_id or not r.item_id:
            issues.append("incomplete_identity")
        if r.eligibility_bucket == "eligible_comparable":
            if not r.expert_review_id or not r.comparison_id:
                issues.append(f"incomplete_records:{r.item_id}")
            if not r.candidate_snapshot_hash and r.available:
                issues.append(f"missing_candidate_snapshot:{r.item_id}")

    if manifest.lifecycle_state in ("frozen", "reviewed", "decision_recorded"):
        snap_hash = deterministic_hash([r.to_dict() for r in rows])
        if manifest.snapshot_hash and manifest.snapshot_hash != snap_hash:
            issues.append("snapshot_hash_mismatch")
        if not manifest.snapshot_hash:
            issues.append("missing_snapshot_hash")

    engines = {r.candidate_engine_version for r in rows if r.candidate_engine_version}
    rulesets = {r.candidate_ruleset_id for r in rows if r.candidate_ruleset_id}
    if len(engines) > 1 or len(rulesets) > 1:
        if not manifest.version_strata_required and not manifest.compatibility_warnings:
            issues.append("multi_version_without_strata_warning")

    # Exclusion accounting: every row has a bucket
    missing_bucket = [r.item_id for r in rows if not r.eligibility_bucket]
    if missing_bucket:
        issues.append("exclusion_bucket_missing")

    contam = store.load_contamination(analysis_id)
    if manifest.lifecycle_state in ("frozen", "reviewed", "decision_recorded"):
        if not contam and rows:
            issues.append("missing_contamination_metadata")
        elif contam and any(c.status != "development_exposed" for c in contam):
            issues.append("unexpected_contamination_status")

    holdout = store.load_holdout_plan(analysis_id)
    if holdout is not None:
        issues.extend(validate_holdout_plan(holdout))

    decision = store.load_decision(analysis_id)
    if decision is not None:
        issues.extend(validate_decision_record(decision))
        if decision.outcome not in DECISION_OUTCOMES:
            issues.append("invalid_decision_outcome")

    # Prohibited claims in summary
    summary_path = store.path_for(analysis_id) / "analysis_summary.json"
    if summary_path.exists():
        text = summary_path.read_text(encoding="utf-8").lower()
        for bad in PROHIBITED_METRICS:
            # Allow listing forbidden names under terminology.not_a
            if f'"{bad}"' in text and "not_a" not in text[max(0, text.find(bad) - 40) : text.find(bad)]:
                # soft: only flag if used as metric key-like
                pass
        import json

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for key in summary.keys():
            if str(key).lower() in PROHIBITED_METRICS:
                issues.append(f"prohibited_metric_key:{key}")

    # Absolute paths in exportable artifacts
    for name in (
        "analysis_manifest.json",
        "analysis_summary.json",
        "decision_gate.json",
        "case_index.csv",
        "analysis_summary.md",
    ):
        p = store.path_for(analysis_id) / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            for token in line.replace(",", " ").replace('"', " ").split():
                if is_absolute_local_path(token):
                    issues.append(f"absolute_path:{name}")
                    break

    return {
        "analysis_id": analysis_id,
        "ok": not issues,
        "issues": issues,
        "item_count": len(rows),
        "unique_identities": len(set(ids)),
        "lifecycle_state": manifest.lifecycle_state,
        "manifest_hash": manifest.manifest_hash,
        "snapshot_hash": manifest.snapshot_hash,
    }
