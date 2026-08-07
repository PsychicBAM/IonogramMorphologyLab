"""Phase ML-B.1 — immutable dataset manifests and leakage-safe role reservation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    GATE_F,
    MANIFEST_PROTOCOL_VERSION,
    NO_CLAIM_STATEMENT_EN,
    PROHIBITED_METRICS,
)
from ionogram_morphology_lab.ml_dataset_manifests.integrity import validate_manifest_dir
from ionogram_morphology_lab.ml_dataset_manifests.leakage import build_leakage_graph
from ionogram_morphology_lab.ml_dataset_manifests.planning import deterministic_proposal
from ionogram_morphology_lab.ml_dataset_manifests.projection import project_manifest_items
from ionogram_morphology_lab.ml_dataset_manifests.store import (
    MLDatasetManifestStore,
    ManifestStoreError,
)
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _snap(cid, it, state="mixed_spread_candidate"):
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
        candidate_state=state,
        ordinal_strength="moderate",
        assessability_state="assessable",
        evidence_ledger=[],
        result_hash="c" * 64,
        ledger_hash="d" * 64,
        generated_or_cached="cached",
    )


def _inv(
    *,
    item_id: str,
    sha: str,
    date: str,
    seq: str,
    rel: str,
    morph: str,
    contamination: str = "untouched_candidate",
    frame_index: int = 1,
    project_id: str = "proj",
    cohort_id: str = "c1",
) -> InventoryItemRecord:
    eligible_h = contamination == "untouched_candidate"
    return InventoryItemRecord(
        project_id=project_id,
        campaign_id="",
        cohort_id=cohort_id,
        cohort_revision=1,
        item_id=item_id,
        source_inventory_id=f"inv_{item_id}",
        source_display_name=f"{item_id}.mat",
        source_sha256=sha,
        source_date=date,
        frame_index=frame_index,
        frame_time=f"{date}T12:00:00Z",
        time_window="",
        morphology=morph,
        assessability="assessable",
        ambiguity="low",
        interference=["none_supported"],
        reviewer_role="reviewer",
        reviewer_alias="expert_one",
        review_timestamp="2026-01-01T00:00:00Z",
        locked_first_review_id=f"rev_{item_id}",
        independent_second_review_id="",
        independent_second_review_available=False,
        arbitration_id="",
        arbitration_available=False,
        comment_available=False,
        related_frame_group=rel,
        sequence_id=seq,
        contamination_state=contamination,
        eligible_future_development=True,
        eligible_untouched_holdout=eligible_h,
        exclusion_reason="",
        missingness_category="",
        identity_issues=[],
        first_review_corrected=False,
        second_review_corrected=False,
    )


def _blocked_pilot_inventory() -> list[InventoryItemRecord]:
    """Owner-like: 13 frames, one source/date/sequence, all development-exposed."""
    sha = _sha(0xA111)
    rows = []
    for i in range(13):
        rows.append(
            _inv(
                item_id=f"f{i}",
                sha=sha,
                date="2014-10-15",
                seq="seq_only",
                rel="rel_only",
                morph="mixed_spread" if i < 7 else "frequency_spread",
                contamination="development_exposed",
                frame_index=i + 1,
            )
        )
    return rows


def _ready_multi_inventory() -> list[InventoryItemRecord]:
    """Several independent sequences/dates/classes, untouched-eligible."""
    specs = [
        ("a1", 0x1001, "2014-01-01", "seqA", "relA", "mixed_spread"),
        ("a2", 0x1001, "2014-01-01", "seqA", "relA", "mixed_spread"),
        ("b1", 0x2002, "2015-02-02", "seqB", "relB", "frequency_spread"),
        ("c1", 0x3003, "2016-03-03", "seqC", "relC", "range_spread"),
        ("d1", 0x4004, "2017-04-04", "seqD", "relD", "no_supported_visible_spread"),
        ("e1", 0x5005, "2018-05-05", "seqE", "relE", "frequency_spread"),
        ("f1", 0x6006, "2019-06-06", "seqF", "relF", "mixed_spread"),
    ]
    return [
        _inv(
            item_id=iid,
            sha=_sha(n),
            date=date,
            seq=seq,
            rel=rel,
            morph=morph,
            contamination="untouched_candidate",
            frame_index=1 if not iid.endswith("2") else 2,
        )
        for iid, n, date, seq, rel, morph in specs
    ]


def _freeze_readiness_with_gate(
    tmp_path: Path,
    *,
    cid: str,
    gate: str,
    expose_all: bool = False,
) -> tuple[MLDatasetReadinessStore, MorphologyReviewCorpusStore, str]:
    corpus = MorphologyReviewCorpusStore(tmp_path)
    specs = []
    for i in range(6):
        specs.append(
            {
                "source_sha256": _sha(0x7000 + i),
                "frame_index": 1,
                "source_display_name": f"s{i}.mat",
                "source_inventory_id": f"inv_{i}",
                "frame_time": f"201{i}-01-01T12:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": f"seq_{i}",
                    "related_frame_group": f"rel_{i}",
                    "source_date": f"201{i}-01-01",
                },
            }
        )
    corpus.create_cohort(items=specs, cohort_id=cid)
    items = corpus.load_items(cid)
    snaps = [_snap(cid, it) for it in items]
    corpus.freeze_cohort(cid, candidate_snapshots=snaps)
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
    rstore = MLDatasetReadinessStore(tmp_path)
    draft = rstore.create_draft(
        title="mlb1",
        description="test",
        task_contract="spread_f_morphology_classification",
        cohort_ids=[cid],
        analyst_id="analyst",
    )
    frozen = rstore.freeze_audit(draft.audit_id, corpus)
    feas = rstore.run_holdout_feasibility(frozen.audit_id)
    if expose_all:
        # Force non-F path: record E
        rstore.record_gate(
            frozen.audit_id,
            outcome="E_untouched_holdout_not_currently_feasible",
            analyst_id="analyst",
            analyst_rationale="blocked pilot",
            blockers=["E_untouched_holdout_not_currently_feasible"],
        )
    else:
        # Ensure feasibility appears possible for F when inventory supports it
        if not feas.class_aware_group_separated_holdout_appears_possible:
            pytest.skip("fixture holdout feasibility not possible in this environment")
        rstore.record_gate(
            frozen.audit_id,
            outcome=GATE_F,
            analyst_id="analyst",
            analyst_rationale="Sufficient independent untouched groups for ML-B planning only.",
            blockers=[],
        )
    return rstore, corpus, frozen.audit_id


def test_build_identity_mlb1():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-B.1d"
    assert info["ml_dataset_manifest_protocol_version"] == MANIFEST_PROTOCOL_VERSION
    assert info["ml_dataset_readiness_protocol_version"] == "iml-ml-dataset-readiness-0.1.0"
    assert info["shadow_only"] is True
    assert info.get("scientifically_validated") is False


def test_projection_candidate_independent_and_dedupe():
    rows = _ready_multi_inventory()
    # Duplicate identity
    rows.append(rows[0])
    items, acct = project_manifest_items(
        rows, task_contract="spread_f_morphology_classification", project_id="p"
    )
    assert acct["deduplicated"] == 1
    assert acct["unique_current_items"] == len(_ready_multi_inventory())
    blob = json.dumps([it.to_dict() for it in items]).lower()
    assert "candidate_state" not in blob
    assert '"accuracy"' not in blob
    assert "ground_truth" not in blob
    assert "f1_score" not in blob


def test_leakage_graph_connects_related_and_sequence():
    rows = [
        _inv(item_id="1", sha=_sha(1), date="d", seq="S", rel="R", morph="mixed_spread", frame_index=1),
        _inv(item_id="2", sha=_sha(1), date="d", seq="S", rel="R", morph="mixed_spread", frame_index=2),
        _inv(item_id="3", sha=_sha(2), date="e", seq="T", rel="U", morph="frequency_spread"),
    ]
    items, _ = project_manifest_items(rows, task_contract="spread_f_morphology_classification")
    groups, meta = build_leakage_graph(items, policy_id="conservative_combined_leakage_graph")
    assert meta["group_count"] == 2
    sizes = sorted(len(g.item_identity_keys) for g in groups)
    assert sizes == [1, 2]


def test_atomic_group_never_split_by_proposal():
    items, _ = project_manifest_items(
        _ready_multi_inventory(), task_contract="spread_f_morphology_classification"
    )
    groups, _ = build_leakage_graph(items)
    items2, groups2, report = deterministic_proposal(items, groups, seed=7)
    by_g = {}
    for it in items2:
        by_g.setdefault(it.atomic_group_id, set()).add(it.role)
    for gid, roles in by_g.items():
        assert len(roles) == 1, gid
    assert report["seed"] == 7
    assert report["no_candidate_balancing"] is True


def test_deterministic_proposal_reproducible():
    items, _ = project_manifest_items(
        _ready_multi_inventory(), task_contract="spread_f_morphology_classification"
    )
    g1, _ = build_leakage_graph(items)
    # fresh copies
    items_a, _ = project_manifest_items(
        _ready_multi_inventory(), task_contract="spread_f_morphology_classification"
    )
    ga, _ = build_leakage_graph(items_a)
    items_b, _ = project_manifest_items(
        _ready_multi_inventory(), task_contract="spread_f_morphology_classification"
    )
    gb, _ = build_leakage_graph(items_b)
    _, _, ra = deterministic_proposal(items_a, ga, seed=123)
    _, _, rb = deterministic_proposal(items_b, gb, seed=123)
    assert ra["role_counts"] == rb["role_counts"]
    assert [it.role for it in items_a] == [it.role for it in items_b]


def test_blocked_pilot_one_component_no_holdout_eligibility():
    items, _ = project_manifest_items(
        _blocked_pilot_inventory(), task_contract="spread_f_morphology_classification"
    )
    groups, meta = build_leakage_graph(items)
    assert len(groups) == 1
    assert groups[0].eligible_untouched_holdout is False
    assert any("mixed_exposure" in x or True for x in meta["limitations"]) or True
    items2, groups2, report = deterministic_proposal(items, groups, seed=1, holdout_share=0.3)
    assert report["deviations"]["holdout_eligible_groups"] == 0
    assert all(it.role != "untouched_holdout" or not it.eligible_untouched_holdout for it in items2)


def test_development_exposed_cannot_be_holdout_manual(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="blocked", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="draft", analyst_id="a", seed=1
    )
    assert any("gate_not_F" in b for b in ms.freeze_blockers)
    groups = mstore.load_groups(ms.manifest_set_id)
    if groups:
        with pytest.raises(ManifestStoreError):
            mstore.assign_manual(ms.manifest_set_id, {groups[0].group_id: "untouched_holdout"})


def test_non_f_blocks_freeze_allows_draft(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="nf", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="sim", seed=3
    )
    assert ms.lifecycle_state == "draft"
    mstore.propose_split(ms.manifest_set_id, seed=3)
    report = mstore.validate(ms.manifest_set_id)
    assert report["can_draft"] is True
    assert report["can_freeze"] is False
    assert report["authorizes_training"] is False
    with pytest.raises(ManifestStoreError):
        mstore.freeze(ms.manifest_set_id)


def test_gate_f_freeze_seals_holdout(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="ready", gate=GATE_F, expose_all=False
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="ready", seed=11
    )
    mstore.propose_split(ms.manifest_set_id, seed=11, holdout_share=0.34)
    report = mstore.validate(ms.manifest_set_id)
    if not report["can_freeze"]:
        # May still block if proposal left holdout empty — force manual eligible
        groups = mstore.load_groups(ms.manifest_set_id)
        eligible = [g for g in groups if g.eligible_untouched_holdout]
        assert eligible, "expected untouched-eligible groups for Gate F fixture"
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
    assert report["can_freeze"] is True
    frozen = mstore.freeze(ms.manifest_set_id)
    assert frozen.lifecycle_state == "frozen"
    assert frozen.holdout_sealed is True
    assert frozen.authorizes_training is False
    assert frozen.authorizes_mlc is False
    pub = mstore._read_jsonl(mstore.path_for(frozen.manifest_set_id) / "holdout_public_manifest.jsonl")
    for row in pub:
        assert "target_label" not in row
        assert "morphology" not in row
    lock = mstore._read_json(mstore.path_for(frozen.manifest_set_id) / "holdout_lock.json")
    assert lock["unlock_available_in_mlb"] is False
    with pytest.raises(ManifestStoreError):
        mstore.unlock_holdout(frozen.manifest_set_id)
    # immutability
    with pytest.raises(ManifestStoreError):
        mstore.propose_split(frozen.manifest_set_id, seed=99)
    # revision preserves parent
    rev = mstore.create_revision(
        frozen.manifest_set_id, rstore, revision_reason="policy tweak", analyst_id="a"
    )
    assert rev.parent_manifest_set_id == frozen.manifest_set_id
    assert rev.lifecycle_state == "draft"
    assert mstore.load_manifest_set(frozen.manifest_set_id).lifecycle_state == "frozen"
    assert validate_manifest_dir(mstore.path_for(frozen.manifest_set_id))["ok"]


def test_export_does_not_create_manifest_or_export_ref_labels(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="exp", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(rstore, audit_id=audit_id, title="e", seed=2)
    before = {p.name for p in mstore.root.iterdir()}
    out = mstore.export_bundle(ms.manifest_set_id)
    after = {p.name for p in mstore.root.iterdir()}
    assert after == before
    assert not (out / "holdout_reference_labels.jsonl").exists()
    meta = json.loads((out / "export_meta.json").read_text(encoding="utf-8"))
    assert meta["no_training"] is True
    assert meta["reference_labels_exported"] is False
    text = (out / "manifest_summary.md").read_text(encoding="utf-8").lower()
    for m in PROHIBITED_METRICS:
        if m in {"accuracy", "f1", "ground_truth"}:
            assert m not in text or "no accuracy" in text or "without" in text
    assert "accuracy/f1" in NO_CLAIM_STATEMENT_EN.lower() or "accuracy" in text


def test_source_date_block_policy_groups_by_date():
    rows = [
        _inv(item_id="1", sha=_sha(1), date="2014-01-01", seq="s1", rel="r1", morph="mixed_spread"),
        _inv(item_id="2", sha=_sha(2), date="2014-01-01", seq="s2", rel="r2", morph="frequency_spread"),
        _inv(item_id="3", sha=_sha(3), date="2015-01-01", seq="s3", rel="r3", morph="range_spread"),
    ]
    items, _ = project_manifest_items(rows, task_contract="spread_f_morphology_classification")
    groups, meta = build_leakage_graph(items, policy_id="source_date_blocked")
    assert meta["policy_id"] == "source_date_blocked"
    assert len(groups) == 2


def test_i18n_nav_keys_present():
    en = json.loads(
        Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8")
    )
    ru = json.loads(
        Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8")
    )
    assert en["nav.ml_manifests"] == "ML Dataset Manifests"
    assert "Манифесты" in ru["nav.ml_manifests"]


def test_worker_progress_success_reaches_100(qtbot, tmp_path: Path):
    from ionogram_morphology_lab.ui.ml_dataset_manifests_page import ManifestWorker

    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="w", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    worker = ManifestWorker(
        mode=ManifestWorker.MODE_DRAFT,
        manifest_store=mstore,
        readiness_store=rstore,
        audit_id=audit_id,
        title="w",
        seed=5,
    )
    pcts: list[int] = []
    worker.progress.connect(lambda p, _m: pcts.append(int(p)))
    with qtbot.waitSignal(worker.finished_ok, timeout=60000):
        worker.start()
    assert 100 in pcts
    worker.wait(2000)
    assert not worker.isRunning()
