"""Candidate-independent current-state label inventory projection."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    is_valid_acquisition_date,
    normalize_acquisition_date,
    parse_date_from_filename,
    resolve_acquisition_date,
)

# Re-export for callers/tests
__all__ = [
    "normalize_acquisition_date",
    "parse_date_from_filename",
    "project_cohort_inventory",
    "dedupe_cohort_references",
    "load_disagreement_exposure_index",
    "resolve_acquisition_date",
]
from ionogram_morphology_lab.ml_dataset_readiness.contracts import (
    REQUIRED_FIELDS_BY_CONTRACT,
    contract_descriptor,
)
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    ANALYSES_DIRNAME,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    HUMAN_MORPHOLOGY_CODES,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _grouping(item) -> dict[str, str]:
    g = getattr(item, "grouping", None) or {}
    if isinstance(g, dict):
        return {str(k): str(v) for k, v in g.items()}
    return {}


def _lookup_source_inventory_date(
    project_root: Path,
    *,
    source_sha: str,
    inventory_id: str,
    display_name: str,
) -> str:
    """Best-effort date from campaign source_scope (authority #1)."""
    try:
        from ionogram_morphology_lab.morphology_review_campaign.store import (
            MorphologyReviewCampaignStore,
        )

        camp = MorphologyReviewCampaignStore(project_root)
        for cid in camp.list_campaigns():
            try:
                manifest = camp.load_manifest(cid)
            except Exception:
                continue
            for s in list(getattr(manifest, "source_scope", None) or []):
                if isinstance(s, dict):
                    sha = str(s.get("source_sha256") or "").lower()
                    inv = str(s.get("source_inventory_id") or "")
                    name = str(s.get("source_display_name") or "")
                    hint = str(s.get("date_hint") or "")
                else:
                    sha = str(getattr(s, "source_sha256", "") or "").lower()
                    inv = str(getattr(s, "source_inventory_id", "") or "")
                    name = str(getattr(s, "source_display_name", "") or "")
                    hint = str(getattr(s, "date_hint", "") or "")
                if not hint:
                    continue
                if (
                    (source_sha and sha == source_sha)
                    or (inventory_id and inv == inventory_id)
                    or (display_name and name == display_name)
                ):
                    nd = normalize_acquisition_date(hint)
                    if nd:
                        return nd
    except Exception:
        pass
    return ""


def _safe_reviewer_alias(reviewer_id: str) -> str:
    rid = str(reviewer_id or "").strip()
    if not rid:
        return ""
    if len(rid) <= 8:
        return rid
    return f"{rid[:4]}…{rid[-4:]}"


def load_disagreement_exposure_index(project_root: Path) -> dict[str, Any]:
    """Load development-exposed identities from frozen disagreement analyses."""
    root = Path(project_root) / ANALYSES_DIRNAME
    item_keys: set[str] = set()
    shas: set[str] = set()
    dates: set[str] = set()
    groups: set[str] = set()
    seqs: set[str] = set()
    if not root.exists():
        return {
            "item_keys": [],
            "source_shas": [],
            "source_dates": [],
            "related_frame_groups": [],
            "sequence_ids": [],
        }
    for d in root.iterdir():
        if not d.is_dir():
            continue
        contam = d / "contamination.jsonl"
        if not contam.exists():
            # fallback: snapshot rows marked development_exposed
            snap = d / "analysis_snapshot.jsonl"
            if not snap.exists():
                continue
            for line in snap.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                import json

                row = json.loads(line)
                if str(row.get("contamination_status") or "") != "development_exposed":
                    continue
                cid = str(row.get("cohort_id") or "")
                iid = str(row.get("item_id") or "")
                if cid and iid:
                    item_keys.add(f"{cid}:{iid}")
                sha = str(row.get("source_sha256") or "").lower()
                if sha:
                    shas.add(sha)
                sd = normalize_acquisition_date(str(row.get("source_date") or ""))
                if sd:
                    dates.add(sd)
                rel = str(row.get("related_frame_group") or "")
                if rel:
                    groups.add(rel)
                seq = str(row.get("sequence_id") or "")
                if seq:
                    seqs.add(seq)
            continue
        import json

        for line in contam.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("status") or "") != "development_exposed":
                continue
            cid = str(row.get("cohort_id") or "")
            iid = str(row.get("item_id") or "")
            if cid and iid:
                item_keys.add(f"{cid}:{iid}")
            sha = str(row.get("source_sha256") or "").lower()
            if sha:
                shas.add(sha)
            sd = normalize_acquisition_date(str(row.get("source_date") or ""))
            if sd:
                dates.add(sd)
            rel = str(row.get("related_frame_group") or "")
            if rel:
                groups.add(rel)
            seq = str(row.get("sequence_id") or "")
            if seq:
                seqs.add(seq)
    return {
        "item_keys": sorted(item_keys),
        "source_shas": sorted(shas),
        "source_dates": sorted(dates),
        "related_frame_groups": sorted(groups),
        "sequence_ids": sorted(seqs),
    }


def _resolve_contamination(
    *,
    cohort_id: str,
    item_id: str,
    source_sha: str,
    source_date: str,
    related_group: str,
    sequence_id: str,
    exposure: dict[str, Any],
    identity_bad: bool,
) -> tuple[str, bool, bool, list[str]]:
    """Return (state, eligible_dev, eligible_holdout, warnings)."""
    warnings: list[str] = []
    if identity_bad:
        return "prohibited_invalid", False, False, warnings

    item_key = f"{cohort_id}:{item_id}"
    exposed_items = set(exposure.get("item_keys") or [])
    exposed_shas = set(exposure.get("source_shas") or [])
    exposed_dates = set(exposure.get("source_dates") or [])
    exposed_groups = set(exposure.get("related_frame_groups") or [])
    exposed_seqs = set(exposure.get("sequence_ids") or [])

    direct = item_key in exposed_items
    neighbor = (
        (source_sha and source_sha in exposed_shas)
        or (related_group and related_group in exposed_groups)
        or (sequence_id and sequence_id in exposed_seqs)
        or (source_date and source_date in exposed_dates and direct)
    )
    if direct:
        return "development_exposed", True, False, warnings
    if neighbor and (
        (related_group and related_group in exposed_groups)
        or (sequence_id and sequence_id in exposed_seqs)
    ):
        warnings.append(
            "Neighboring frame in a development-exposed related-frame group or "
            "sequence may be unsuitable for untouched holdout."
        )
        return "development_exposed", True, False, warnings
    return "untouched_candidate", True, True, warnings


def _missingness_for_row(
    *,
    task_contract: str,
    morphology: str,
    assessability: str,
    interference: list[str],
    ambiguity: str,
    locked_id: str,
    source_sha: str,
    frame_time: str,
    related_group: str,
    reviewer_alias: str,
    available: bool,
    identity_issues: list[str],
) -> str:
    if identity_issues:
        return "corrupted_identity"
    if not available:
        return "unavailable_data"
    if not locked_id:
        return "structurally_missing"
    required = REQUIRED_FIELDS_BY_CONTRACT.get(task_contract, ())
    if task_contract == "ionogram_parameter_scaling":
        return "not_applicable"
    if "expert_morphology" in required and not morphology:
        return "structurally_missing"
    if morphology in ("indeterminate", "not_assessable"):
        return "expert_abstained"
    if "assessability" in required and not assessability:
        return "structurally_missing"
    if "interference" in required and not interference:
        return "structurally_missing"
    if "ambiguity" in required and not ambiguity:
        return "structurally_missing"
    if not source_sha:
        return "structurally_missing"
    if not frame_time:
        return "structurally_missing"
    if not related_group:
        return "structurally_missing"
    if not reviewer_alias:
        return "structurally_missing"
    return ""


def _had_correction(store: MorphologyReviewCorpusStore, cohort_id: str, item_id: str, round_n: int) -> bool:
    rows = store._read_jsonl(store.path_for(cohort_id) / "blind_reviews.jsonl")
    count = 0
    for row in rows:
        if str(row.get("cohort_id") or cohort_id) != cohort_id:
            continue
        if row.get("item_id") != item_id:
            continue
        if int(row.get("review_round") or 0) != round_n:
            continue
        count += 1
    return count > 1


def project_cohort_inventory(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    task_contract: str,
    campaign_id: str = "",
    project_id: str = "",
    exposure: dict[str, Any] | None = None,
) -> tuple[list[InventoryItemRecord], dict[str, int], list[str]]:
    """Project unique current expert labels (candidate-independent)."""
    warnings: list[str] = []
    rows: list[InventoryItemRecord] = []
    accounting: Counter[str] = Counter()
    exposure = exposure or {}

    try:
        manifest = store.load_manifest(cohort_id)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"cohort_unreadable:{cohort_id}:{exc}")
        accounting["unresolved_cohort_revision"] += 1
        return rows, dict(accounting), warnings

    if not bool(getattr(manifest, "frozen", False)):
        warnings.append(f"cohort_not_frozen:{cohort_id}")
        # still attempt inventory of locked reviews if any

    items = {it.item_id: it for it in store.load_items(cohort_id)}
    seen_keys: set[str] = set()
    sha_frame_index: dict[tuple[str, int], list[str]] = {}

    # Consult reveal/blind only for exposure/contamination context — never for labels
    candidate_consulted = False
    try:
        # Presence of comparisons implies development exposure risk after reveal
        from ionogram_morphology_lab.morphology_review_corpus.current_state import (
            project_cohort_comparisons,
        )

        proj = project_cohort_comparisons(store, cohort_id)
        if proj.current_count > 0:
            candidate_consulted = True
    except Exception:
        candidate_consulted = False

    for item_id, item in items.items():
        grouping = _grouping(item)
        seq = str(grouping.get("sequence_id") or grouping.get("sequence") or "")
        explicit_rel = str(
            grouping.get("related_frame_group") or grouping.get("related_group") or ""
        ).strip()
        if explicit_rel:
            rel = explicit_rel
            rel_synthetic = False
        else:
            rel = f"{item.source_sha256}:{item.frame_index}"
            rel_synthetic = True
        display_name = str(item.source_display_name or "")
        inv_id = str(item.source_inventory_id or "")
        inv_date = _lookup_source_inventory_date(
            Path(store.project_root),
            source_sha=str(item.source_sha256 or "").lower(),
            inventory_id=inv_id,
            display_name=display_name,
        )
        # Never use frame_time / review timestamps as acquisition date.
        source_date = resolve_acquisition_date(
            source_inventory_date=inv_date,
            grouping=grouping,
            datetime_metadata=str(getattr(item, "datetime_metadata", "") or ""),
            source_display_name=display_name,
        )
        time_window = str(grouping.get("time_window") or "")

        r1 = store.locked_review_for_item(cohort_id, item_id, review_round=1)
        r2 = store.locked_review_for_item(cohort_id, item_id, review_round=2)

        adj_id = ""
        try:
            adjs = store._read_jsonl(store.path_for(cohort_id) / "adjudications.jsonl")
            for adj in adjs:
                if str(adj.get("item_id") or "") == item_id:
                    adj_id = str(adj.get("adjudication_id") or adj.get("id") or "")
        except Exception:
            adj_id = ""

        identity_issues: list[str] = []
        sha = str(item.source_sha256 or "").lower()
        if not sha:
            identity_issues.append("missing_sha")
        if item_id is None:
            identity_issues.append("missing_item_id")
        available = str(getattr(item, "item_status", "")) != "item_unavailable"
        if not available:
            identity_issues.append("unavailable_source")

        sf_key = (sha, int(item.frame_index))
        sha_frame_index.setdefault(sf_key, []).append(item_id)

        role = "first_reviewer"
        reviewer_id = str(getattr(r1, "reviewer_id", "") or "") if r1 else ""
        morph = str(getattr(r1, "morphology", "") or "") if r1 else ""
        assess = str(getattr(r1, "assessability", "") or "") if r1 else ""
        amb = str(getattr(r1, "ambiguity", "") or "") if r1 else ""
        interf = list(getattr(r1, "interference", []) or []) if r1 else []
        locked_id = str(getattr(r1, "review_id", "") or "") if r1 else ""
        ts = str(getattr(r1, "created_at", "") or "") if r1 else ""
        comment = bool(str(getattr(r1, "rationale", "") or "").strip()) if r1 else False

        exclusion = ""
        if not locked_id:
            exclusion = "missing_locked_review"
            accounting["missing_locked_review"] += 1
        elif morph and morph not in HUMAN_MORPHOLOGY_CODES:
            exclusion = "invalid_morphology_vocabulary"
            identity_issues.append("invalid_morphology")
            accounting["invalid_vocabulary"] += 1

        contam, elig_dev, elig_hold, cwarns = _resolve_contamination(
            cohort_id=cohort_id,
            item_id=item_id,
            source_sha=sha,
            source_date=source_date,
            related_group=rel,
            sequence_id=seq,
            exposure=exposure,
            identity_bad=bool(identity_issues),
        )
        warnings.extend(cwarns)
        # If cohort was revealed/compared, mark inspected items as exposed when already in DA
        # Candidate consultation never supplies morphology into this row.
        if candidate_consulted and contam == "untouched_candidate":
            # Revealed alone does not auto-expose; only DA registry / neighbor rules do.
            pass

        miss = _missingness_for_row(
            task_contract=task_contract,
            morphology=morph,
            assessability=assess,
            interference=interf,
            ambiguity=amb,
            locked_id=locked_id,
            source_sha=sha,
            frame_time=str(item.frame_time or item.datetime_metadata or ""),
            related_group=rel,
            reviewer_alias=_safe_reviewer_alias(reviewer_id),
            available=available,
            identity_issues=identity_issues,
        )

        row = InventoryItemRecord(
            project_id=project_id or Path(store.project_root).name,
            campaign_id=campaign_id,
            cohort_id=cohort_id,
            cohort_revision=int(getattr(manifest, "revision_number", 1) or 1),
            item_id=item_id,
            source_inventory_id=str(item.source_inventory_id or ""),
            source_display_name=str(item.source_display_name or ""),
            source_sha256=sha,
            source_date=source_date,
            frame_index=int(item.frame_index),
            frame_time=str(item.frame_time or item.datetime_metadata or ""),
            time_window=time_window,
            morphology=morph,
            assessability=assess,
            ambiguity=amb,
            interference=interf,
            reviewer_role=role,
            reviewer_alias=_safe_reviewer_alias(reviewer_id),
            review_timestamp=ts,
            locked_first_review_id=locked_id,
            independent_second_review_id=str(getattr(r2, "review_id", "") or "") if r2 else "",
            independent_second_review_available=bool(r2),
            arbitration_id=adj_id,
            arbitration_available=bool(adj_id),
            comment_available=comment,
            related_frame_group=rel,
            sequence_id=seq,
            contamination_state=contam,
            eligible_future_development=elig_dev and bool(locked_id),
            eligible_untouched_holdout=elig_hold and bool(locked_id) and not identity_issues,
            exclusion_reason=exclusion,
            missingness_category=miss,
            identity_issues=identity_issues,
            first_review_corrected=_had_correction(store, cohort_id, item_id, 1),
            second_review_corrected=_had_correction(store, cohort_id, item_id, 2) if r2 else False,
            candidate_consulted_for_exposure_only=candidate_consulted,
            related_frame_group_synthetic=rel_synthetic,
        )
        ikey = row.identity_key()
        if ikey in seen_keys:
            accounting["duplicate_exact_identity"] += 1
            warnings.append(f"duplicate_exact_identity:{ikey}")
            continue
        seen_keys.add(ikey)
        rows.append(row)
        accounting["selected_records"] += 1
        if locked_id:
            accounting["locked_first_reviews"] += 1
        if r2:
            accounting["independent_second_reviews"] += 1
        if adj_id:
            accounting["arbitration_records"] += 1

    for (sha, fi), iids in sha_frame_index.items():
        if sha and len(iids) > 1:
            warnings.append(
                f"same_source_sha_frame_multiple_items:{sha[:12]}:{fi}:{','.join(iids)}"
            )
            accounting["same_source_sha_frame_collision"] += 1

    # Contract note for parameter scaling
    desc = contract_descriptor(task_contract)
    if task_contract == "ionogram_parameter_scaling":
        warnings.append(desc["parameter_scaling_status_en"])
        accounting["parameter_scaling_unsupported"] = len(rows)

    accounting["unique_current_items"] = len(rows)
    return rows, dict(accounting), warnings


def dedupe_cohort_references(
    cohort_ids: list[str],
) -> tuple[list[str], dict[str, int]]:
    """Deduplicate cohort IDs with explicit accounting (no silent drop)."""
    seen: list[str] = []
    counts: Counter[str] = Counter()
    for cid in cohort_ids:
        counts[cid] += 1
        if cid not in seen:
            seen.append(cid)
    accounting = {
        "input_references": len(cohort_ids),
        "unique_cohorts": len(seen),
        "duplicate_references_removed": len(cohort_ids) - len(seen),
    }
    return seen, accounting
