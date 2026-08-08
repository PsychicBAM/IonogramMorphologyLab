"""Synthetic-only ML-C.1 project fixture builder."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from scipy.io import savemat

from ionogram_morphology_lab.ml_dataset_manifests.store import MLDatasetManifestStore
from ionogram_morphology_lab.ml_dataset_manifests.constants import GATE_F
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.ml_offline_baselines.source_resolve import SourcePathIndex
from ionogram_morphology_lab.morphology_review_corpus.models import BlindReviewRecord, CandidateSnapshot
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stack(label: str, seed: int) -> np.ndarray:
    """Four valid frames with intentionally distinct, non-research morphology."""
    rng = np.random.default_rng(seed)
    data = rng.normal(0, 0.02, (4, 256, 400)).astype(np.float32)
    if label == "mixed_spread":
        data[:, 65:190, 80:330] += 2.0
        data[:, 20:230, 150:180] += 1.0
    elif label == "frequency_spread":
        data[:, 110:145, 25:375] += 3.0
    else:
        data[:, 20:235, 170:220] += 3.0
    return data


def build_mlc1_fixture(project_root: Path, *, item_count: int = 36):
    """Create a frozen, source-resolvable synthetic ML-C.1 fixture.

    The corpus has 12 independent atomic groups (three labelled items each);
    the first three frames of each four-frame MAT stack are referenced.
    """
    project_root.mkdir(parents=True, exist_ok=True)
    labels = ("mixed_spread", "frequency_spread", "range_spread")
    source_dir = project_root / "synthetic_sources"
    source_dir.mkdir(exist_ok=True)
    corpus = MorphologyReviewCorpusStore(project_root)
    specs, source_index = [], SourcePathIndex()
    groups = max(12, (item_count + 2) // 3)
    item_no = 0
    for group in range(groups):
        label = labels[group % len(labels)]
        source = source_dir / f"SYNTHETIC_QA_{group:02d}_{label}.mat"
        savemat(source, {"Amp_all": _stack(label, group)})
        digest = _sha(source)
        source_index.paths[digest] = source
        for frame in (1, 2, 3):
            if item_no >= item_count:
                break
            specs.append({
                "source_sha256": digest, "frame_index": frame,
                "source_display_name": source.name, "source_inventory_id": f"synthetic_{group}_{frame}",
                "frame_time": f"2020-01-{group + 1:02d}T0{frame}:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {"sequence_id": f"synthetic_seq_{group}", "related_frame_group": f"synthetic_group_{group}",
                             "source_date": f"2020-01-{group + 1:02d}"},
            })
            item_no += 1
    cohort_id = "mlc1_synthetic_qa"
    corpus.create_cohort(items=specs, cohort_id=cohort_id)
    items = corpus.load_items(cohort_id)
    snapshots = [CandidateSnapshot(
        cohort_id=cohort_id, item_id=item.item_id, source_sha256=item.source_sha256,
        frame_index=item.frame_index, candidate_engine_version="synthetic-qa",
        ruleset_id="synthetic", ruleset_hash="0" * 64, result_contract_version=2,
        diagnostics_cache_id="synthetic", candidate_state="synthetic_only",
        ordinal_strength="moderate", assessability_state="assessable",
        evidence_ledger=[], result_hash="c" * 64, ledger_hash="d" * 64, generated_or_cached="cached",
    ) for item in items]
    corpus.freeze_cohort(cohort_id, candidate_snapshots=snapshots)
    for item in items:
        label = labels[int(item.source_inventory_id.split("_")[1]) % len(labels)]
        corpus.save_blind_review(cohort_id, BlindReviewRecord.create(
            reviewer_id="synthetic_qa", reviewer_role="reviewer", review_round=1,
            cohort_id=cohort_id, item_id=item.item_id, morphology=label, assessability="assessable",
            interference=["none_supported"], ambiguity="low", confidence="high", rationale="SYNTHETIC QA DATA",
        ))
    readiness_store = MLDatasetReadinessStore(project_root)
    audit = readiness_store.create_draft(
        title="SYNTHETIC QA DATA", description="NOT RESEARCH IONOGRAMS",
        task_contract="spread_f_morphology_classification", cohort_ids=[cohort_id], analyst_id="synthetic_qa",
    )
    frozen_audit = readiness_store.freeze_audit(audit.audit_id, corpus)
    readiness_store.run_holdout_feasibility(frozen_audit.audit_id)
    readiness_store.record_gate(
        frozen_audit.audit_id, outcome=GATE_F, analyst_id="synthetic_qa",
        analyst_rationale="Independent synthetic groups reserve a sealed synthetic holdout.", blockers=[],
    )
    manifest_store = MLDatasetManifestStore(project_root)
    manifest = manifest_store.create_draft_from_readiness(
        readiness_store, audit_id=frozen_audit.audit_id, title="ML-C.1 synthetic QA", seed=17,
    )
    manifest_store.build_leakage(manifest.manifest_set_id)
    manifest_store.propose_split(manifest.manifest_set_id, seed=17, holdout_share=0.25)
    report = manifest_store.validate(manifest.manifest_set_id)
    if not report["can_freeze"]:
        groups_rows, _ = manifest_store.build_leakage(manifest.manifest_set_id)
        roles = ("train", "train", "development", "untouched_holdout")
        manifest_store.assign_manual(manifest.manifest_set_id, {
            row.group_id: roles[index % len(roles)] for index, row in enumerate(sorted(groups_rows, key=lambda row: row.group_id))
        })
    frozen_manifest = manifest_store.freeze(manifest.manifest_set_id)
    return project_root, frozen_manifest.manifest_set_id, source_index, readiness_store, manifest_store
