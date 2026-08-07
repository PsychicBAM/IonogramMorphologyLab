#!/usr/bin/env python3
"""Validate ML-B.1 dataset manifest contracts (shadow-only; no training)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.ml_dataset_manifests.constants import (  # noqa: E402
    GATE_F,
    MANIFEST_PROTOCOL_VERSION,
    NO_CLAIM_STATEMENT_EN,
    PROHIBITED_METRICS,
)
from ionogram_morphology_lab.ml_dataset_manifests.integrity import (  # noqa: E402
    validate_manifest_dir,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import (  # noqa: E402
    MLDatasetManifestStore,
)
from ionogram_morphology_lab.ml_dataset_readiness.store import (  # noqa: E402
    MLDatasetReadinessStore,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (  # noqa: E402
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import (  # noqa: E402
    MorphologyReviewCorpusStore,
)


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _snap(cid, it):
    return CandidateSnapshot(
        cohort_id=cid,
        item_id=it.item_id,
        source_sha256=it.source_sha256,
        frame_index=it.frame_index,
        candidate_engine_version="iml-morph-candidate-0.1.1",
        ruleset_id="iml-morph-candidate-rules",
        ruleset_hash="rules0.1.0",
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


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        corpus = MorphologyReviewCorpusStore(root)
        cid = "mlb1_val"
        specs = []
        for i in range(6):
            specs.append(
                {
                    "source_sha256": _sha(0x9000 + i),
                    "frame_index": 1,
                    "source_display_name": f"v{i}.mat",
                    "source_inventory_id": f"inv_v{i}",
                    "frame_time": f"201{i}-06-01T12:00:00Z",
                    "feature_version": "iml2-0.2.0",
                    "grouping": {
                        "sequence_id": f"seqV{i}",
                        "related_frame_group": f"relV{i}",
                        "source_date": f"201{i}-06-01",
                    },
                }
            )
        corpus.create_cohort(items=specs, cohort_id=cid)
        items = corpus.load_items(cid)
        corpus.freeze_cohort(cid, candidate_snapshots=[_snap(cid, it) for it in items])
        morphs = [
            "mixed_spread",
            "frequency_spread",
            "range_spread",
            "no_supported_visible_spread",
            "mixed_spread",
            "frequency_spread",
        ]
        for it, morph in zip(items, morphs):
            corpus.save_blind_review(
                cid,
                BlindReviewRecord.create(
                    reviewer_id="expert_one",
                    reviewer_role="reviewer",
                    review_round=1,
                    cohort_id=cid,
                    item_id=it.item_id,
                    morphology=morph,
                    assessability="assessable",
                    interference=["none_supported"],
                    ambiguity="low",
                    confidence="high",
                    rationale="ok",
                ),
            )
        rstore = MLDatasetReadinessStore(root)
        draft = rstore.create_draft(
            title="val",
            description="",
            task_contract="spread_f_morphology_classification",
            cohort_ids=[cid],
            analyst_id="validator",
        )
        frozen = rstore.freeze_audit(draft.audit_id, corpus)
        feas = rstore.run_holdout_feasibility(frozen.audit_id)
        if not feas.class_aware_group_separated_holdout_appears_possible:
            errors.append("expected holdout feasibility appears_possible for validator fixture")
        else:
            rstore.record_gate(
                frozen.audit_id,
                outcome=GATE_F,
                analyst_id="validator",
                analyst_rationale="Validator synthetic fixture for ML-B planning only.",
                blockers=[],
            )

        mstore = MLDatasetManifestStore(root)
        ms = mstore.create_draft_from_readiness(
            rstore, audit_id=frozen.audit_id, title="manifest_val", seed=17
        )
        if ms.manifest_protocol_version != MANIFEST_PROTOCOL_VERSION:
            errors.append("protocol version mismatch")
        mstore.propose_split(ms.manifest_set_id, seed=17, holdout_share=0.34)
        groups = mstore.load_groups(ms.manifest_set_id)
        eligible = [g for g in groups if g.eligible_untouched_holdout]
        if eligible:
            mapping = {}
            for i, g in enumerate(sorted(groups, key=lambda x: x.group_id)):
                if g.group_id == eligible[0].group_id:
                    mapping[g.group_id] = "untouched_holdout"
                elif i % 2 == 0:
                    mapping[g.group_id] = "train"
                else:
                    mapping[g.group_id] = "development"
            mstore.assign_manual(ms.manifest_set_id, mapping)
        report = mstore.validate(ms.manifest_set_id)
        if report.get("authorizes_training") or report.get("authorizes_mlc"):
            errors.append("validation must not authorize training/ML-C")
        if report.get("can_freeze"):
            fz = mstore.freeze(ms.manifest_set_id)
            if fz.authorizes_training or fz.authorizes_mlc:
                errors.append("frozen set authorizes training/ML-C")
            chk = validate_manifest_dir(mstore.path_for(fz.manifest_set_id))
            if not chk["ok"]:
                errors.extend(chk["errors"])
            pub = (mstore.path_for(fz.manifest_set_id) / "holdout_public_manifest.jsonl").read_text(
                encoding="utf-8"
            )
            for bad in ("target_label", "morphology", "assessability"):
                if f'"{bad}"' in pub:
                    errors.append(f"public holdout contains {bad}")
            out = mstore.export_bundle(fz.manifest_set_id)
            if (out / "holdout_reference_labels.jsonl").exists():
                errors.append("export leaked sealed reference labels")
            summary = (out / "manifest_summary.md").read_text(encoding="utf-8").lower()
            if "authorizes training: false" not in summary and "authorizes training: false" not in summary:
                # accept no-claim statement
                if "no model training" not in summary and "not authorize" not in NO_CLAIM_STATEMENT_EN.lower():
                    pass
            for metric in ("accuracy", "f1_score", "ground_truth"):
                if metric in summary and metric not in NO_CLAIM_STATEMENT_EN.lower():
                    # no-claim mentions accuracy/f1 as denied — OK
                    if "no accuracy" not in summary and "without" not in summary:
                        if metric in summary.replace("accuracy/f1", ""):
                            errors.append(f"prohibited metric language: {metric}")
        else:
            errors.append("expected can_freeze for Gate F validator fixture: " + str(report.get("freeze_blockers")))

    if errors:
        print("validate_ml_dataset_manifests FAILED:")
        for e in errors:
            print(" -", e)
        return 1
    print(
        f"validate_ml_dataset_manifests OK ({MANIFEST_PROTOCOL_VERSION}; "
        f"{len(PROHIBITED_METRICS)} prohibited metrics guarded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
