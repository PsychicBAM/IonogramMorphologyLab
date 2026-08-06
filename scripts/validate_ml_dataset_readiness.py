#!/usr/bin/env python3
"""Validate Phase ML-A.1 dataset readiness contracts (synthetic fixtures)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    NO_CLAIM_STATEMENT_EN,
    PARAMETER_SCALING_UNSUPPORTED_EN,
    PROHIBITED_METRICS,
    READINESS_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_dataset_readiness.contracts import contract_descriptor
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.integrity import validate_audit_dir
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _build(project: Path) -> MorphologyReviewCorpusStore:
    store = MorphologyReviewCorpusStore(project)
    items = []
    for i in range(6):
        items.append(
            {
                "source_sha256": _sha(0x5100 + (i // 3)),
                "frame_index": (i % 3) + 1,
                "source_display_name": f"v{i}.mat",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": f"seq_{i // 3}",
                    "related_frame_group": f"rel_{i // 3}",
                    "source_date": f"2014-11-{10 + i // 3:02d}",
                },
            }
        )
    store.create_cohort(items=items, cohort_id="val_mla1")
    loaded = store.load_items("val_mla1")
    snaps = [
        CandidateSnapshot(
            cohort_id="val_mla1",
            item_id=it.item_id,
            source_sha256=it.source_sha256,
            frame_index=it.frame_index,
            candidate_engine_version="iml-morph-candidate-0.1.1",
            ruleset_id="iml-morph-candidate-rules",
            ruleset_hash="0.1.0",
            result_contract_version=2,
            diagnostics_cache_id="n/a",
            candidate_state="mixed_spread_candidate",
            ordinal_strength="moderate",
            assessability_state="assessable",
            evidence_ledger=[],
            result_hash="c" * 64,
            ledger_hash="d" * 64,
            generated_or_cached="cached",
        )
        for it in loaded
    ]
    store.freeze_cohort("val_mla1", candidate_snapshots=snaps)
    morphs = [
        "mixed_spread",
        "mixed_spread",
        "frequency_spread",
        "range_spread",
        "indeterminate",
        "no_supported_visible_spread",
    ]
    for it, morph in zip(loaded, morphs):
        store.save_blind_review(
            "val_mla1",
            BlindReviewRecord.create(
                reviewer_id="validator",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="val_mla1",
                item_id=it.item_id,
                morphology=morph,
                assessability="assessable" if morph != "indeterminate" else "partially_assessable",
                interference=["vertical_interference"] if morph == "mixed_spread" else ["none_supported"],
                ambiguity="moderate",
                confidence="high",
                rationale="validator",
            ),
        )
    return store


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="iml_mla1_val_") as tmp:
        root = Path(tmp)
        corpus = _build(root)
        store = MLDatasetReadinessStore(root)

        # Parameter scaling unsupported
        desc = contract_descriptor("ionogram_parameter_scaling")
        if desc.get("parameter_scaling_status_en") != PARAMETER_SCALING_UNSUPPORTED_EN:
            errors.append("parameter_scaling_status_mismatch")

        draft = store.create_draft(
            title="validator",
            description="synthetic",
            task_contract="spread_f_morphology_classification",
            cohort_ids=["val_mla1", "val_mla1"],  # duplicate refs
            analyst_id="validator",
        )
        if draft.audit_protocol_version != READINESS_PROTOCOL_VERSION:
            errors.append("protocol_mismatch")
        frozen = store.freeze_audit(draft.audit_id, corpus)
        rows = store.load_inventory(frozen.audit_id)
        if not rows:
            errors.append("empty_inventory")
        for r in rows:
            if "_candidate" in (r.morphology or ""):
                errors.append("candidate_leakage")
        cov = build_coverage_summary(rows)
        if "accuracy" in cov or "f1" in cov:
            errors.append("prohibited_metric_in_coverage")

        report = validate_audit_dir(store.path_for(frozen.audit_id))
        if not report["ok"]:
            errors.extend(report["errors"])

        store.record_gate(
            frozen.audit_id,
            outcome="C_expand_class_source_date_sequence_coverage",
            analyst_id="validator",
            analyst_rationale="Synthetic fixture — coverage expansion required before ML-B.",
        )
        out = store.export_report(frozen.audit_id)
        md = (out / "readiness_report.md").read_text(encoding="utf-8")
        if NO_CLAIM_STATEMENT_EN.split("—")[0].strip() not in md and "descriptive" not in md.lower():
            errors.append("missing_no_claim")
        for metric in ("accuracy=", "f1="):
            if metric in md.lower():
                errors.append(f"forbidden_claim:{metric}")
        if "E:\\" in md or "/Users/" in md:
            errors.append("absolute_path_in_export")

        # Gate F must not authorize training
        gate = store._read_json(store.path_for(frozen.audit_id) / "readiness_gate.json")
        if gate.get("authorizes_training"):
            errors.append("gate_authorizes_training")

    if errors:
        print("ML dataset readiness validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("ML dataset readiness validation passed.")
    print(f"  protocol: {READINESS_PROTOCOL_VERSION}")
    print(f"  prohibited metrics guarded: {len(PROHIBITED_METRICS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
