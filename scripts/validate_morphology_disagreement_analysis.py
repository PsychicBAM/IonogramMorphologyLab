#!/usr/bin/env python3
"""Validate Phase 4C.4a disagreement analysis contracts (synthetic fixtures)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.morphology_disagreement_analysis.analytics import (
    descriptive_dashboard,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    ANALYSIS_PROTOCOL_VERSION,
    PROHIBITED_METRICS,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.holdout import (
    build_holdout_plan,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.store import (
    MorphologyDisagreementAnalysisStore,
)
from ionogram_morphology_lab.morphology_review_corpus.batch_compare import (
    batch_reveal_and_compare,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _build(project: Path) -> MorphologyReviewCorpusStore:
    store = MorphologyReviewCorpusStore(project)
    items = [
        {
            "source_sha256": _sha(0xAA00 + i),
            "frame_index": i + 1,
            "source_display_name": f"v{i}.mat",
            "feature_version": "iml2-0.2.0",
            "grouping": {
                "sequence_id": "seqV",
                "related_frame_group": "relV",
            },
        }
        for i in range(6)
    ]
    store.create_cohort(items=items, cohort_id="val_da")
    loaded = store.load_items("val_da")
    snaps = []
    for it in loaded:
        snaps.append(
            CandidateSnapshot(
                cohort_id="val_da",
                item_id=it.item_id,
                source_sha256=it.source_sha256,
                frame_index=it.frame_index,
                candidate_engine_version="iml-morph-candidate-0.1.1",
                ruleset_id="iml-morph-candidate-rules",
                ruleset_hash="0.1.0",
                result_contract_version=2,
                diagnostics_cache_id="n/a",
                candidate_state="frequency_spread_candidate",
                ordinal_strength="moderate",
                assessability_state="assessable",
                evidence_ledger=[],
                result_hash="c" * 64,
                ledger_hash="d" * 64,
                generated_or_cached="cached",
            )
        )
    store.freeze_cohort("val_da", candidate_snapshots=snaps)
    morphs = [
        "mixed_spread",
        "mixed_spread",
        "mixed_spread",
        "frequency_spread",
        "indeterminate",
        "mixed_spread",
    ]
    for it, morph in zip(loaded, morphs):
        store.save_blind_review(
            "val_da",
            BlindReviewRecord.create(
                reviewer_id="validator",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id="val_da",
                item_id=it.item_id,
                morphology=morph,
                assessability="assessable",
                interference=["vertical_interference"]
                if morph == "mixed_spread"
                else ["none_supported"],
                ambiguity="moderate",
                confidence="high",
                rationale="validator",
            ),
        )
    batch_reveal_and_compare(store, "val_da")
    return store


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="iml_da_val_") as td:
        project = Path(td)
        corpus = _build(project)
        astore = MorphologyDisagreementAnalysisStore(project)
        draft = astore.create_draft(
            title="Validator analysis",
            description="synthetic",
            cohort_ids=["val_da"],
            analyst_id="validator",
        )
        frozen = astore.freeze_snapshot(draft.analysis_id, corpus)
        assert frozen.lifecycle_state == "frozen"
        assert frozen.analysis_protocol_version == ANALYSIS_PROTOCOL_VERSION
        rows = astore.load_snapshot_rows(frozen.analysis_id)
        assert rows
        ids = {(r.cohort_id, r.item_id) for r in rows}
        assert len(ids) == len(rows)
        dash = descriptive_dashboard(rows)
        assert dash["morphology_disagreements"] >= 3
        assert dash["exact_label_matches"] >= 1
        for bad in PROHIBITED_METRICS:
            assert bad not in dash
        report = astore.integrity_report(frozen.analysis_id)
        assert report["ok"], report["issues"]
        contam = astore.load_contamination(frozen.analysis_id)
        assert contam
        plan = build_holdout_plan(
            analysis_id=frozen.analysis_id,
            title="untouched future",
            all_rows=rows,
            holdout_case_keys=["holdout_future:item_a"],
            contamination_records=contam,
        )
        assert not plan.overlap_errors
        astore.save_holdout_plan(plan)
        decision = astore.record_decision(
            analysis_id=frozen.analysis_id,
            outcome="F_candidate_ruleset_hypothesis_justified",
            analyst_id="validator",
            analyst_rationale="Descriptive mixed→frequency concentration justifies a future proposal phase only.",
            alternative_explanations=["label ambiguity", "interference"],
        )
        assert decision.holdout_required
        dest = project / "export"
        astore.export_bundle(frozen.analysis_id, dest)
        assert (dest / "decision_gate.json").exists()
        print("morphology disagreement analysis validator: OK")
        print(f"  protocol={ANALYSIS_PROTOCOL_VERSION}")
        print(f"  items={len(rows)} disagreements={dash['morphology_disagreements']}")
        print(f"  integrity_ok={report['ok']}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
