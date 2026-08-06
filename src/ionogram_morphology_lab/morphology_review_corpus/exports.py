"""Deterministic portable exports for morphology review corpora."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ionogram_morphology_lab.morphology_review_corpus.analytics import (
    descriptive_summary,
    refuse_unsupported_metrics,
)
from ionogram_morphology_lab.morphology_review_corpus.constants import (
    ADJUDICATION_SCHEMA_VERSION,
    PROTOCOL_SCHEMA_VERSION,
    REVIEW_CORPUS_SCHEMA_VERSION,
    REVIEW_RECORD_SCHEMA_VERSION,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import assert_no_absolute_paths
from ionogram_morphology_lab.morphology_review_corpus.labels import assert_no_prohibited_metrics
from ionogram_morphology_lab.morphology_review_corpus.models import AuditEvent
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _meta(store: MorphologyReviewCorpusStore, cohort_id: str) -> dict[str, Any]:
    manifest = store.load_manifest(cohort_id)
    return {
        "cohort_id": cohort_id,
        "manifest_hash": manifest.manifest_hash,
        "protocol_hash": manifest.protocol_hash,
        "manifest_schema_version": REVIEW_CORPUS_SCHEMA_VERSION,
        "review_schema_version": REVIEW_RECORD_SCHEMA_VERSION,
        "protocol_schema_version": PROTOCOL_SCHEMA_VERSION,
        "adjudication_schema_version": ADJUDICATION_SCHEMA_VERSION,
        "candidate_engine_version": manifest.candidate_engine_version,
        "ruleset_id": manifest.ruleset_id,
        "ruleset_hash": manifest.ruleset_hash,
        "feature_version": manifest.feature_version,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "build_identity": "ML-A.1a.2",
        "scientific_non_claims": [
            "Not a scientific validation set",
            "Not ground truth",
            "No accuracy/precision/recall/sensitivity/specificity/F1",
            "Human review is expert assessment, not automatic truth",
        ],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def export_cohort(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    include_candidate_in_blind_worksheet: bool = False,
    progress: Callable[[str, float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    """Write exports/ under the cohort. Blind worksheet never includes candidate."""
    if include_candidate_in_blind_worksheet:
        raise ValueError("Blind-review worksheet must not include candidate data")
    d = store.path_for(cohort_id) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    meta = _meta(store, cohort_id)
    assert_no_absolute_paths(meta)

    def _prog(msg: str, frac: float) -> None:
        if progress:
            progress(msg, frac)
        if cancel_check and cancel_check():
            raise RuntimeError("Export cancelled")

    _prog("items", 0.1)
    items = [it.to_dict() for it in store.load_items(cohort_id)]
    for it in items:
        # Strip any absolute paths from rendering snapshots
        snap = it.get("rendering_snapshot") or {}
        if isinstance(snap, dict):
            it["rendering_snapshot"] = {
                k: v
                for k, v in snap.items()
                if not (isinstance(v, str) and (":\\" in v or v.startswith("/")))
            }
    _write_jsonl(d / "items.jsonl", items)
    _write_csv(
        d / "items.csv",
        items,
        [
            "cohort_id",
            "item_id",
            "source_inventory_id",
            "source_display_name",
            "source_sha256",
            "frame_index",
            "frame_time",
            "item_status",
            "partition",
            "sampling_stratum",
            "manifest_position",
            "unavailable_reason",
        ],
    )

    _prog("reviews", 0.35)
    reviews = store._read_jsonl(store.path_for(cohort_id) / "blind_reviews.jsonl")
    # Blind export: no candidate fields
    blind_safe = []
    for r in reviews:
        row = dict(r)
        for banned in (
            "candidate_state",
            "candidate_result_hash",
            "evidence_ledger",
            "candidate_strength",
            "ordinal_strength",
        ):
            row.pop(banned, None)
        blind_safe.append(row)
    _write_jsonl(d / "blind_reviews.jsonl", blind_safe)
    _write_csv(
        d / "reviews.csv",
        blind_safe,
        [
            "review_id",
            "reviewer_id",
            "review_round",
            "cohort_id",
            "item_id",
            "morphology",
            "assessability",
            "ambiguity",
            "confidence",
            "rationale",
            "created_at",
            "record_hash",
            "prior_review_id",
            "locked",
        ],
    )

    _prog("comparisons", 0.55)
    comparisons = store._read_jsonl(store.path_for(cohort_id) / "reveal_comparisons.jsonl")
    _write_jsonl(d / "reveal_comparisons.jsonl", comparisons)
    _write_csv(
        d / "comparisons.csv",
        comparisons,
        [
            "comparison_id",
            "cohort_id",
            "item_id",
            "review_id",
            "human_morphology",
            "candidate_state",
            "agreement_status",
            "comparison_comment",
            "record_hash",
        ],
    )

    _prog("adjudications", 0.7)
    adjs = store._read_jsonl(store.path_for(cohort_id) / "adjudications.jsonl")
    _write_jsonl(d / "adjudications.jsonl", adjs)
    _write_csv(
        d / "adjudications.csv",
        adjs,
        [
            "adjudication_id",
            "adjudicator_id",
            "cohort_id",
            "item_id",
            "adjudicated_morphology",
            "rationale",
            "record_hash",
            "label",
        ],
    )

    snaps = store._read_jsonl(store.path_for(cohort_id) / "candidate_snapshots.jsonl")
    _write_jsonl(d / "candidate_snapshots.jsonl", snaps)
    audit = store.load_audit(cohort_id)
    _write_jsonl(d / "audit_log.jsonl", audit)

    _prog("summary", 0.85)
    summary = descriptive_summary(store, cohort_id)
    assert_no_prohibited_metrics(summary)
    md = _summary_markdown(summary, meta)
    (d / "summary.md").write_text(md, encoding="utf-8")

    bundle = {
        **meta,
        "manifest": store.load_manifest(cohort_id).to_dict(),
        "protocol": store.load_protocol(cohort_id).to_dict(),
        "summary": summary,
        "item_count": len(items),
        "review_count": len(reviews),
        "comparison_count": len(comparisons),
        "adjudication_count": len(adjs),
    }
    assert_no_absolute_paths(bundle)
    (d / "cohort_bundle.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Also copy manifest
    (d / "cohort_manifest.json").write_text(
        json.dumps(store.load_manifest(cohort_id).to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    store.append_audit(
        cohort_id,
        AuditEvent.create(
            "export", cohort_id=cohort_id, details={"export_dir": "exports"}
        ),
    )
    _prog("done", 1.0)
    return d


def export_refuses_unsupported(metrics: list[str]) -> dict[str, Any]:
    return refuse_unsupported_metrics(metrics)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    buf = io.StringIO()
    for row in rows:
        assert_no_absolute_paths(row)
        buf.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    path.write_text(buf.getvalue(), encoding="utf-8")


def _summary_markdown(summary: dict[str, Any], meta: dict[str, Any]) -> str:
    lines = [
        f"# Morphology Review Corpus Summary — {meta['cohort_id']}",
        "",
        f"- Build Identity: {meta['build_identity']}",
        f"- Manifest hash: `{meta['manifest_hash']}`",
        f"- Protocol hash: `{meta['protocol_hash']}`",
        f"- Candidate engine: {meta['candidate_engine_version']}",
        f"- Generated: {meta['generation_timestamp']}",
        "",
        "## Scientific non-claims",
        "",
    ]
    for c in meta["scientific_non_claims"]:
        lines.append(f"- {c}")
    lines.extend(
        [
            "",
            "## Descriptive counts",
            "",
            f"- Items: {summary['item_count']}",
            f"- Round-1 locked reviews: {summary['completed_blind_reviews_round1']}",
            f"- Exact agreement count: {summary['exact_agreement_count']}",
            f"- Adjudications: {summary['adjudication_count']}",
            "",
            "### Human label distribution",
            "",
        ]
    )
    for k, v in sorted((summary.get("human_label_distribution") or {}).items()):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "### Availability", ""])
    for k, v in sorted((summary.get("availability_counts") or {}).items()):
        lines.append(f"- `{k}`: {v}")
    lines.extend(
        [
            "",
            "> Descriptive only. No accuracy/F1. Pilot corpus — not a validation set.",
            "",
        ]
    )
    return "\n".join(lines)
