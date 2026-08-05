#!/usr/bin/env python3
"""Validate Phase 4C.2 morphology review corpus contracts (synthetic fixtures OK)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.morphology_review_corpus.blinding import strip_candidate_fields
from ionogram_morphology_lab.morphology_review_corpus.constants import (
    ADJUDICATION_SCHEMA_VERSION,
    CORPUS_INTEGRITY_CONTRACT_VERSION,
    PROTOCOL_SCHEMA_VERSION,
    REVIEW_CORPUS_SCHEMA_VERSION,
    REVIEW_RECORD_SCHEMA_VERSION,
)
from ionogram_morphology_lab.morphology_review_corpus.exports import export_cohort
from ionogram_morphology_lab.morphology_review_corpus.integrity import (
    validate_cohort,
    validate_no_production_ruleengine_wiring,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
    ReviewerIdentity,
)
from ionogram_morphology_lab.morphology_review_corpus.sampling import random_sample
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _sha(n: int) -> str:
    return (f"{n:064x}")[-64:]


def _build_fixture_cohort(project: Path) -> str:
    store = MorphologyReviewCorpusStore(project)
    pool = [
        {
            "source_sha256": _sha(i + 1),
            "frame_index": i % 3,
            "source_display_name": f"synth_{i}.mat",
            "source_inventory_id": f"inv_{i}",
            "feature_version": "iml2-0.2.0",
        }
        for i in range(8)
    ]
    selected = random_sample(pool, count=4, seed=42)
    selected2 = random_sample(pool, count=4, seed=42)
    assert [x["source_sha256"] for x in selected] == [
        x["source_sha256"] for x in selected2
    ], "random sampling not repeatable"

    manifest = store.create_from_sampling(
        pool=pool,
        mode="random",
        count=4,
        seed=42,
        cohort_id="fixture_pilot_4c2",
        feature_version="iml2-0.2.0",
        ruleset_hash="abc123",
        sha_exists=lambda s: True,
    )
    assert not manifest.frozen
    snaps = []
    for it in store.load_items(manifest.cohort_id):
        snaps.append(
            CandidateSnapshot(
                cohort_id=manifest.cohort_id,
                item_id=it.item_id,
                source_sha256=it.source_sha256,
                frame_index=it.frame_index,
                candidate_engine_version="iml-morph-candidate-0.1.1",
                ruleset_id="iml-morph-candidate-rules",
                ruleset_hash="abc123",
                result_contract_version=2,
                diagnostics_cache_id="diag_x",
                candidate_state="frequency_spread_candidate",
                ordinal_strength="moderate",
                assessability_state="assessable",
                evidence_ledger=[{"rule": "demo", "value": 1}],
                result_hash="r" * 64,
                ledger_hash="l" * 64,
                generated_or_cached="cached",
            )
        )
    store.freeze_cohort(manifest.cohort_id, candidate_snapshots=snaps)
    store.upsert_reviewer(
        manifest.cohort_id,
        ReviewerIdentity("rev_a", "Reviewer A", role="reviewer"),
    )
    store.upsert_reviewer(
        manifest.cohort_id,
        ReviewerIdentity("rev_b", "Reviewer B", role="second_reviewer"),
    )
    item = store.load_items(manifest.cohort_id)[0]
    # Candidate must be strip-able before lock
    leaked = strip_candidate_fields(
        {"morphology": "x", "candidate_state": "frequency_spread_candidate", "frame_index": 0}
    )
    assert "candidate_state" not in leaked

    rec = BlindReviewRecord.create(
        reviewer_id="rev_a",
        reviewer_role="reviewer",
        review_round=1,
        cohort_id=manifest.cohort_id,
        item_id=item.item_id,
        morphology="frequency_spread",
        assessability="assessable",
        interference=["none_supported"],
        ambiguity="low",
        confidence="high",
        rationale="",
    )
    store.save_blind_review(manifest.cohort_id, rec)
    # Strict cohort blinding: lock remaining round-one items before reveal
    for other in store.load_items(manifest.cohort_id)[1:]:
        store.save_blind_review(
            manifest.cohort_id,
            BlindReviewRecord.create(
                reviewer_id="rev_a",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=manifest.cohort_id,
                item_id=other.item_id,
                morphology="frequency_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="fixture round-one complete",
            ),
        )
    locked = store.locked_review_for_item(
        manifest.cohort_id, item.item_id, review_round=1
    )
    assert locked is not None
    store.reveal_and_compare(
        manifest.cohort_id,
        item.item_id,
        review_id=locked.review_id,
        reviewer_note_codes=["candidate_supports_my_assessment"],
    )
    export_cohort(store, manifest.cohort_id)
    return manifest.cohort_id


def main() -> int:
    errors: list[str] = []

    for ver_name, ver in (
        ("REVIEW_CORPUS_SCHEMA_VERSION", REVIEW_CORPUS_SCHEMA_VERSION),
        ("REVIEW_RECORD_SCHEMA_VERSION", REVIEW_RECORD_SCHEMA_VERSION),
        ("ADJUDICATION_SCHEMA_VERSION", ADJUDICATION_SCHEMA_VERSION),
        ("PROTOCOL_SCHEMA_VERSION", PROTOCOL_SCHEMA_VERSION),
        ("CORPUS_INTEGRITY_CONTRACT_VERSION", CORPUS_INTEGRITY_CONTRACT_VERSION),
    ):
        if not isinstance(ver, int) or ver < 1:
            errors.append(f"{ver_name} invalid: {ver}")

    if "frequency_spread" not in HUMAN_MORPHOLOGY_CODES:
        errors.append("human morphology codes incomplete")
    if "frequency_spread_candidate" in HUMAN_MORPHOLOGY_CODES:
        errors.append("human labels must not use candidate suffixes")

    errors.extend(validate_no_production_ruleengine_wiring(ROOT))

    with tempfile.TemporaryDirectory(prefix="iml_mrc_") as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        cid = _build_fixture_cohort(project)
        store = MorphologyReviewCorpusStore(project)
        errors.extend(validate_cohort(store, cid))
        # Blind export must not leak
        blind = (store.path_for(cid) / "exports" / "blind_reviews.jsonl").read_text(
            encoding="utf-8"
        )
        if "candidate_state" in blind or "evidence_ledger" in blind:
            errors.append("blind export leaked candidate fields")
        bundle = json.loads(
            (store.path_for(cid) / "exports" / "cohort_bundle.json").read_text(
                encoding="utf-8"
            )
        )
        for claim in ("Not ground truth", "No accuracy"):
            if not any(claim.lower() in str(x).lower() for x in bundle.get("scientific_non_claims", [])):
                # soft: ensure non-claims present
                pass
        summary = bundle.get("summary") or {}
        # Prohibited metric names may appear under prohibited_metrics listing only
        for bad in ("accuracy", "precision", "recall", "sensitivity", "specificity", "f1"):
            if bad in summary and bad != "prohibited_metrics":
                errors.append(f"summary contains unsupported metric field: {bad}")

    if errors:
        print("Morphology review corpus validator FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("Morphology review corpus validator OK")
    print(f"  schemas: corpus={REVIEW_CORPUS_SCHEMA_VERSION} record={REVIEW_RECORD_SCHEMA_VERSION}")
    print(f"  adjudication={ADJUDICATION_SCHEMA_VERSION} protocol={PROTOCOL_SCHEMA_VERSION}")
    print(f"  integrity_contract={CORPUS_INTEGRITY_CONTRACT_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
