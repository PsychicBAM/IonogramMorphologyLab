"""Portable campaign readiness export (Phase 4C.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.analytics import (
    campaign_descriptive_summary,
)
from ionogram_morphology_lab.morphology_review_campaign.constants import (
    BUILD_IDENTITY_DEFAULT,
)
from ionogram_morphology_lab.morphology_review_campaign.progress import campaign_progress
from ionogram_morphology_lab.morphology_review_campaign.models import CampaignAuditEvent
from ionogram_morphology_lab.morphology_review_campaign.store import MorphologyReviewCampaignStore
from ionogram_morphology_lab.morphology_review_corpus.hashing import assert_no_absolute_paths


def export_campaign_readiness(
    store: MorphologyReviewCampaignStore,
    campaign_id: str,
    *,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Write campaign_readiness_report.md + .json under campaign exports/."""
    manifest = store.load_manifest(campaign_id)
    protocol = store.load_protocol(campaign_id)
    prog = campaign_progress(store, campaign_id)
    summary = campaign_descriptive_summary(store, campaign_id)
    links = [L.to_dict() for L in store.list_cohort_links(campaign_id)]
    assignments = [a.to_dict() for a in store.list_assignments(campaign_id)]

    payload: dict[str, Any] = {
        "kind": "campaign_readiness_report",
        "campaign_id": campaign_id,
        "display_name": manifest.display_name,
        "designation_en": manifest.designation_en,
        "designation_ru": manifest.designation_ru,
        "state": manifest.state,
        "campaign_hash": manifest.campaign_hash,
        "protocol_hash": protocol.protocol_hash,
        "protocol": protocol.to_dict(),
        "source_scope": manifest.source_scope,
        "time_windows": manifest.time_windows,
        "sampling_plan": manifest.sampling_plan,
        "reviewer_plan": manifest.reviewer_plan,
        "cohort_links": links,
        "assignments": assignments,
        "progress": {
            "planned_items": prog["planned_items"],
            "unique_real_items": prog["unique_real_items"],
            "first_blind": prog["first_blind_progress"],
            "comparisons": prog["comparison_progress"],
            "second_reviews": prog["second_review_progress"],
            "adjudications": prog["adjudication_progress"],
            "unavailable": prog["unavailable_items"],
        },
        "integrity": {
            "ok": prog["integrity_ok"],
            "messages": prog["integrity_messages"],
            "invariants": prog["invariants"],
        },
        "descriptive_summary": summary,
        "unresolved_issues": list(prog["integrity_messages"])
        + [b.get("reason") for b in prog["blocked_items"]],
        "scientific_non_claims": {
            "en": summary["note_en"],
            "ru": summary["note_ru"],
            "accuracy_f1_unavailable": True,
        },
        "candidate_identity": {
            "engine": "iml-morph-candidate-0.1.1",
            "ruleset": "iml-morph-candidate-rules 0.1.0",
            "shadow_only": True,
        },
        "build_identity": manifest.build_identity or BUILD_IDENTITY_DEFAULT,
        "shadow_only": True,
        "scientifically_validated": False,
    }
    assert_no_absolute_paths(payload)

    dest = Path(out_dir) if out_dir else store.path_for(campaign_id) / "exports"
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "campaign_readiness_report.json"
    md_path = dest / "campaign_readiness_report.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    store.append_audit(
        campaign_id,
        CampaignAuditEvent.create(
            "readiness_exported",
            campaign_id=campaign_id,
            details={"json": json_path.name, "md": md_path.name},
        ),
    )
    return {
        "json_path": str(json_path.as_posix()),
        "md_path": str(md_path.as_posix()),
        "payload": payload,
    }


def _to_markdown(payload: dict[str, Any]) -> str:
    prog = payload.get("progress") or {}
    integ = payload.get("integrity") or {}
    lines = [
        f"# Campaign readiness — {payload.get('display_name')}",
        "",
        f"- Campaign ID: `{payload.get('campaign_id')}`",
        f"- State: {payload.get('state')}",
        f"- Designation (EN): {payload.get('designation_en')}",
        f"- Designation (RU): {payload.get('designation_ru')}",
        f"- Campaign hash: `{payload.get('campaign_hash')}`",
        f"- Protocol hash: `{payload.get('protocol_hash')}`",
        f"- Build Identity: {payload.get('build_identity')}",
        "",
        "## Coverage",
        f"- Sources in scope: {len(payload.get('source_scope') or [])}",
        f"- Time windows: {len(payload.get('time_windows') or [])}",
        f"- Sampling: `{((payload.get('sampling_plan') or {}).get('method'))}` "
        f"seed={((payload.get('sampling_plan') or {}).get('seed'))}",
        "",
        "## Progress (current-state)",
        f"- Planned items: {prog.get('planned_items')}",
        f"- Unique real items: {prog.get('unique_real_items')}",
        f"- First blind: {prog.get('first_blind')}",
        f"- Comparisons: {prog.get('comparisons')}",
        f"- Optional second reviews: {prog.get('second_reviews')}",
        f"- Adjudications: {prog.get('adjudications')}",
        f"- Unavailable: {prog.get('unavailable')}",
        "",
        "## Integrity",
        f"- OK: {integ.get('ok')}",
    ]
    for msg in integ.get("messages") or []:
        lines.append(f"- Issue: {msg}")
    lines.extend(
        [
            "",
            "## Scientific non-claims",
            str((payload.get("scientific_non_claims") or {}).get("en") or ""),
            "",
            "- Candidate remains shadow-only.",
            "- No accuracy / F1 / validated performance.",
            "- No production RuleEngine wiring.",
            "",
            "## Cohort links",
        ]
    )
    for link in payload.get("cohort_links") or []:
        lines.append(
            f"- `{link.get('cohort_id')}` role=`{link.get('cohort_role')}` "
            f"manifest=`{(link.get('manifest_hash') or '')[:16]}…`"
        )
    lines.append("")
    return "\n".join(lines) + "\n"
