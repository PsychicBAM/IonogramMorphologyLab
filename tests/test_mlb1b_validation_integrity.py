"""ML-C.1 — metric scan semantics, holdout group counts, validation lifecycle/UX."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    GATE_F,
    MANIFEST_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_dataset_manifests.display_labels import format_blocker
from ionogram_morphology_lab.ml_dataset_manifests.integrity import (
    build_overlap_report,
    validate_freeze_eligibility,
)
from ionogram_morphology_lab.ml_dataset_manifests.metric_scan import (
    scan_prohibited_metrics,
    string_has_performance_claim,
)
from ionogram_morphology_lab.ml_dataset_manifests.planning import (
    role_group_counts_from_items,
    sync_group_roles_from_items,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import (
    MLDatasetManifestStore,
    ManifestStoreError,
)
from ionogram_morphology_lab.ui.build_identity import collect_build_identity
from tests.test_mlb1_dataset_manifests import _freeze_readiness_with_gate
from tests.test_mlb1a_manifest_ux_dates import _build_scenario_b_gate_f


def test_build_identity_mlb1b():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-C.1b"
    assert info["ml_dataset_manifest_protocol_version"] == MANIFEST_PROTOCOL_VERSION


def test_f1_inside_atomic_group_id_allowed():
    payload = {
        "atomic_group_id": "ag_02c5d70cf1745f85",
        "item_id": "item_f1deadbeef",
        "source_sha256": "aa" * 28 + "f1accuracy00",
        "manifest_set_hash": "3dfe014ba1db25ef1ffe9ff2a052b2ede582fe044c11e",
        "role": "train",
        "target_label": "mixed_spread",
    }
    assert scan_prohibited_metrics(payload) == []


def test_true_metric_fields_rejected():
    assert "prohibited_metric_payload:f1" in scan_prohibited_metrics({"f1": 0.91})
    assert "prohibited_metric_payload:f1_score" in scan_prohibited_metrics(
        {"f1_score": 0.91}
    )
    assert "prohibited_metric_payload:accuracy" in scan_prohibited_metrics(
        {"accuracy": 0.99}
    )


def test_claim_string_rejected_in_claim_fields():
    assert string_has_performance_claim("model accuracy = 0.91")
    hits = scan_prohibited_metrics({"claim": "F1 score = 0.88"})
    assert any("prohibited_metric_payload:claim" in h for h in hits)
    # Opaque identity containing accuracy substring remains allowed
    assert scan_prohibited_metrics({"source_inventory_id": "src_accuracy_probe_01"}) == []


def test_freeze_eligibility_ignores_hex_f1(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="adv_f1", gate=GATE_F, expose_all=False
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="adv", seed=42
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    items = mstore.load_items(ms.manifest_set_id)
    # Inject adversarial hex group id containing f1 into one item/group
    groups = mstore.load_groups(ms.manifest_set_id)
    assert groups
    old = groups[0].group_id
    new = "ag_deadbeefcf1745aa"
    groups[0].group_id = new
    for it in items:
        if it.atomic_group_id == old:
            it.atomic_group_id = new
    sync_group_roles_from_items(items, groups)
    overlap = build_overlap_report(items, groups)
    blockers = validate_freeze_eligibility(
        gate_outcome=GATE_F,
        authorizes_mlb_planning=True,
        items=items,
        groups=groups,
        overlap=overlap,
    )
    assert not any("prohibited_metric_payload:f1" == b or b.endswith(":f1") for b in blockers)


def test_scenario_b_holdout_3_items_2_groups(tmp_path: Path):
    mstore, ms, _ = _scenario_b_ready_draft(tmp_path)
    # Rebuild leakage again — must not desync holdout group roles
    mstore.build_leakage(ms.manifest_set_id)
    items = mstore.load_items(ms.manifest_set_id)
    groups = mstore.load_groups(ms.manifest_set_id)
    sync_group_roles_from_items(items, groups)
    holdout_items = [it for it in items if it.role == "untouched_holdout"]
    holdout_gids = {it.atomic_group_id for it in holdout_items if it.atomic_group_id}
    assert len(holdout_items) == 3
    assert len(holdout_gids) == 2
    assert sum(1 for g in groups if g.role == "untouched_holdout") == 2
    counts = role_group_counts_from_items(items)
    assert counts.get("train") == 4
    assert counts.get("development") == 2
    assert counts.get("untouched_holdout") == 2
    # After leakage rebuild, holdout groups still match item atomic_group_ids
    mstore.build_leakage(ms.manifest_set_id)
    items2 = mstore.load_items(ms.manifest_set_id)
    groups2 = mstore.load_groups(ms.manifest_set_id)
    sync_group_roles_from_items(items2, groups2)
    assert len({it.atomic_group_id for it in items2 if it.role == "untouched_holdout"}) == 2
    assert sum(1 for g in groups2 if g.role == "untouched_holdout") == 2


def test_one_group_cannot_have_multiple_roles():
    from ionogram_morphology_lab.ml_dataset_manifests.models import (
        AtomicGroup,
        ManifestItemRecord,
    )

    g = AtomicGroup(
        group_id="ag_x",
        item_identity_keys=["a", "b"],
        item_ids=["a", "b"],
        source_shas=["s"],
        source_dates=["2014-01-01"],
        sequence_ids=["seq"],
        related_frame_groups=["rel"],
        campaign_ids=[],
        target_labels=["mixed_spread"],
        contamination_states=["untouched_candidate"],
        eligible_untouched_holdout=True,
        role="train",
    )

    def _item(iid, role):
        return ManifestItemRecord(
            project_id="p",
            cohort_id="c",
            cohort_revision=1,
            item_id=iid,
            task_contract="spread_f_morphology_classification",
            source_inventory_id=iid,
            source_display_name=f"{iid}.mat",
            source_sha256="a" * 64,
            source_date="2014-01-01",
            frame_index=1,
            frame_time="12:00",
            related_frame_group="rel",
            sequence_id="seq",
            campaign_id="",
            acquisition_period="",
            morphology="mixed_spread",
            assessability="assessable",
            ambiguity="low",
            interference=[],
            reviewer_role="reviewer",
            reviewer_alias="expert_one",
            contamination_state="untouched_candidate",
            eligible_future_development=True,
            eligible_untouched_holdout=True,
            exclusion_reason="",
            missingness_category="",
            independent_second_review_available=False,
            target_label="mixed_spread",
            atomic_group_id="ag_x",
            role=role,
        )

    items = [_item("a", "train"), _item("b", "development")]
    overlap = build_overlap_report(items, [g])
    assert overlap["ok"] is False
    assert any("atomic_group_split" in e for e in overlap["errors"])


def test_validation_lifecycle_consistency(tmp_path: Path):
    rstore, _, audit_id = _freeze_readiness_with_gate(
        tmp_path, cid="life", gate="E", expose_all=True
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="life", seed=1
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=1)
    report = mstore.validate(ms.manifest_set_id)
    assert report["ok"] is False
    assert report["integrity_ok"] is False
    ms2 = mstore.load_manifest_set(ms.manifest_set_id)
    assert ms2.lifecycle_state == "draft"
    assert ms2.last_validation_ok is False


def _scenario_b_ready_draft(tmp_path: Path, *, cohort_id: str = "scenario_b_ready_f1_005"):
    """Shared Scenario B draft; ensure holdout 3 items / 2 groups via domain APIs."""
    rstore, audit_id, meta = _build_scenario_b_gate_f(tmp_path, cohort_id=cohort_id)
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="scenario-b", seed=42
    )
    mstore.build_leakage(ms.manifest_set_id)
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    items = mstore.load_items(ms.manifest_set_id)
    holdout_n = sum(1 for it in items if it.role == "untouched_holdout")
    holdout_g = len(
        {it.atomic_group_id for it in items if it.role == "untouched_holdout" and it.atomic_group_id}
    )
    if holdout_n != 3 or holdout_g != 2:
        # Project-id affects shuffle; force authoritative Scenario B assignment.
        groups = mstore.load_groups(ms.manifest_set_id)
        pair = next(g for g in groups if len(g.item_ids) >= 2)
        singles = sorted(
            [g for g in groups if g.group_id != pair.group_id], key=lambda g: g.group_id
        )
        mapping = {pair.group_id: "untouched_holdout", singles[0].group_id: "untouched_holdout"}
        for g in singles[1:3]:
            mapping[g.group_id] = "development"
        for g in singles[3:]:
            mapping[g.group_id] = "train"
        mstore.assign_manual(ms.manifest_set_id, mapping)
    return mstore, ms, meta


def test_successful_validation_sets_validated_and_idempotent(tmp_path: Path):
    mstore, ms, _ = _scenario_b_ready_draft(tmp_path)
    r1 = mstore.validate(ms.manifest_set_id)
    assert r1["ok"] is True
    assert r1["integrity_ok"] is True
    assert r1["can_freeze"] is True
    assert r1["holdout_item_count"] == 3
    assert r1["holdout_group_count"] == 2
    ms1 = mstore.load_manifest_set(ms.manifest_set_id)
    assert ms1.lifecycle_state == "validated"
    assert ms1.validated_content_hash
    r2 = mstore.validate(ms.manifest_set_id)
    assert r2["ok"] is True
    ms2 = mstore.load_manifest_set(ms.manifest_set_id)
    assert ms2.lifecycle_state == "validated"
    assert ms2.validated_content_hash == ms1.validated_content_hash


def test_manifest_change_invalidates_validation(tmp_path: Path):
    mstore, ms, _ = _scenario_b_ready_draft(tmp_path)
    assert mstore.validate(ms.manifest_set_id)["ok"] is True
    assert mstore.load_manifest_set(ms.manifest_set_id).lifecycle_state == "validated"
    # Mutation invalidates
    mstore.propose_split(ms.manifest_set_id, seed=42, holdout_share=0.34)
    ms2 = mstore.load_manifest_set(ms.manifest_set_id)
    assert ms2.lifecycle_state == "draft"
    assert ms2.validated_content_hash == ""
    assert ms2.last_validation_ok is False


def test_scenario_b_freeze_seal_export_unlock(tmp_path: Path):
    mstore, ms, _ = _scenario_b_ready_draft(tmp_path)
    assert mstore.validate(ms.manifest_set_id)["can_freeze"] is True
    frozen = mstore.freeze(ms.manifest_set_id)
    assert frozen.lifecycle_state == "frozen"
    assert frozen.holdout_sealed is True
    pub = mstore._read_jsonl(
        mstore.path_for(frozen.manifest_set_id) / "holdout_public_manifest.jsonl"
    )
    assert len(pub) == 3
    for row in pub:
        assert "target_label" not in row
        assert "morphology" not in row
    lock = mstore._read_json(mstore.path_for(frozen.manifest_set_id) / "holdout_lock.json")
    assert lock["unlock_available_in_mlb"] is False
    with pytest.raises(ManifestStoreError):
        mstore.unlock_holdout(frozen.manifest_set_id)
    before = {p.name for p in mstore.root.iterdir()}
    out = mstore.export_bundle(frozen.manifest_set_id, tmp_path / "exp")
    after = {p.name for p in mstore.root.iterdir()}
    assert before == after
    assert not any("holdout_reference" in p.name for p in Path(out).rglob("*"))


def test_blocker_localization_prohibited_metric():
    ru = format_blocker("prohibited_metric_payload:f1", "ru")
    en = format_blocker("prohibited_metric_payload:f1", "en")
    assert "prohibited_metric_payload" not in ru
    assert "f1" in en.lower() or "metric" in en.lower()
    assert "метрик" in ru.lower() or "запрещ" in ru.lower()


def test_validate_feedback_i18n_keys_present():
    en = json.loads(Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads(Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    for key in (
        "manifests.validate_ok_title",
        "manifests.validate_ok_body",
        "manifests.validate_fail_title",
        "manifests.validate_fail_body",
        "manifests.validation_stale",
    ):
        assert "{items}" in en["manifests.validate_ok_body"] or key != "manifests.validate_ok_body"
        assert en[key]
        assert ru[key]
    assert "ПРОЙДЕНА" in ru["manifests.validate_ok_body"]
    assert "PASS" in en["manifests.validate_ok_body"]
