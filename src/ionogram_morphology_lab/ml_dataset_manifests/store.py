"""Project-local store for immutable ML dataset manifest sets."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    DEFAULT_GROUPING_POLICY,
    GATE_F,
    HOLDOUT_UNLOCK_FORBIDDEN_EN,
    MANIFEST_DIRNAME,
    MANIFEST_PROTOCOL_VERSION,
    NO_CLAIM_STATEMENT_EN,
    NO_CLAIM_STATEMENT_RU,
    SPLIT_POLICY_VERSION,
    WORKFLOW_SEAL_NOTE_EN,
)
from ionogram_morphology_lab.ml_dataset_manifests.integrity import (
    build_overlap_report,
    validate_freeze_eligibility,
    validate_manifest_dir,
)
from ionogram_morphology_lab.ml_dataset_manifests.leakage import build_leakage_graph
from ionogram_morphology_lab.ml_dataset_manifests.models import (
    AtomicGroup,
    HoldoutLockRecord,
    ManifestItemRecord,
    ManifestSet,
    SplitPolicy,
    new_manifest_set_id,
)
from ionogram_morphology_lab.ml_dataset_manifests.planning import (
    apply_manual_assignments,
    build_coverage_report,
    deterministic_proposal,
    role_group_counts_from_items,
    sync_group_roles_from_items,
)
from ionogram_morphology_lab.ml_dataset_manifests.projection import project_manifest_items
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    assert_no_absolute_paths,
    deterministic_hash,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManifestStoreError(RuntimeError):
    pass


class MLDatasetManifestStore:
    """Immutable manifest-set store under project review_dataset/ml_manifests."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / MANIFEST_DIRNAME
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, manifest_set_id: str) -> Path:
        return self.root / manifest_set_id

    def assignment_content_hash(
        self,
        items: list[ManifestItemRecord],
        groups: list[AtomicGroup],
        *,
        grouping_policy: str = "",
        seed: int = 0,
    ) -> str:
        """Hash of role assignment + grouping that validation seals against."""
        payload = {
            "grouping_policy": grouping_policy,
            "seed": int(seed),
            "items": sorted(
                (
                    {
                        "identity_key": it.identity_key(),
                        "atomic_group_id": it.atomic_group_id,
                        "role": it.role,
                    }
                    for it in items
                ),
                key=lambda r: r["identity_key"],
            ),
            "groups": sorted(
                (
                    {
                        "group_id": g.group_id,
                        "role": g.role,
                        "members": sorted(g.item_identity_keys),
                    }
                    for g in groups
                ),
                key=lambda r: r["group_id"],
            ),
        }
        return deterministic_hash(payload)

    def _invalidate_validation(self, ms: ManifestSet) -> None:
        if ms.lifecycle_state == "validated":
            ms.lifecycle_state = "draft"
        ms.validated_at = ""
        ms.validated_content_hash = ""
        ms.last_validation_ok = False

    def list_manifest_sets(self) -> list[ManifestSet]:
        out: list[ManifestSet] = []
        if not self.root.exists():
            return out
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and (d / "manifest_set.json").exists():
                out.append(self.load_manifest_set(d.name))
        return out

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            assert_no_absolute_paths(payload)
        except ValueError as exc:
            raise ManifestStoreError(str(exc)) from exc
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def load_manifest_set(self, manifest_set_id: str) -> ManifestSet:
        return ManifestSet.from_dict(
            self._read_json(self.path_for(manifest_set_id) / "manifest_set.json")
        )

    def _save_manifest_set(self, ms: ManifestSet) -> None:
        ms.authorizes_training = False
        ms.authorizes_mlc = False
        ms.authorizes_holdout_evaluation = False
        ms.manifest_set_hash = ms.compute_manifest_set_hash()
        self._write_json(self.path_for(ms.manifest_set_id) / "manifest_set.json", ms.to_dict())

    def load_items(self, manifest_set_id: str) -> list[ManifestItemRecord]:
        rows = self._read_jsonl(self.path_for(manifest_set_id) / "item_index.jsonl")
        return [ManifestItemRecord.from_dict(r) for r in rows]

    def load_groups(self, manifest_set_id: str) -> list[AtomicGroup]:
        rows = self._read_jsonl(self.path_for(manifest_set_id) / "atomic_groups.jsonl")
        return [AtomicGroup.from_dict(r) for r in rows]

    def load_policy(self, manifest_set_id: str) -> SplitPolicy:
        return SplitPolicy.from_dict(
            self._read_json(self.path_for(manifest_set_id) / "split_policy.json")
        )

    def _assert_mutable(self, ms: ManifestSet) -> None:
        if ms.lifecycle_state == "frozen":
            raise ManifestStoreError(
                "Frozen manifest set is immutable; create a revision instead"
            )
        if ms.lifecycle_state == "archived":
            raise ManifestStoreError("Archived manifest set cannot be modified")

    def create_draft_from_readiness(
        self,
        readiness_store: MLDatasetReadinessStore,
        *,
        audit_id: str,
        title: str,
        description: str = "",
        analyst_id: str = "",
        grouping_policy: str = DEFAULT_GROUPING_POLICY,
        seed: int = 42,
        parent_manifest_set_id: str = "",
        revision_reason: str = "",
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> ManifestSet:
        """Create a draft manifest set from a frozen/gate-recorded readiness audit."""
        if progress_cb:
            progress_cb(5, "Loading readiness audit")
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")

        rmanifest = readiness_store.load_manifest(audit_id)
        if rmanifest.lifecycle_state not in {"frozen", "gate_recorded", "reviewed"}:
            raise ManifestStoreError(
                "Source readiness audit must be frozen or gate-recorded"
            )
        inventory = readiness_store.load_inventory(audit_id)
        gate_outcome = rmanifest.gate_outcome or ""
        authorizes_mlb = gate_outcome == GATE_F
        gate_path = readiness_store.path_for(audit_id) / "readiness_gate.json"
        if gate_path.exists():
            gate = readiness_store._read_json(gate_path)
            gate_outcome = gate.get("outcome", gate_outcome)
            authorizes_mlb = bool(gate.get("authorizes_mlb_manifest_planning_only")) and (
                gate_outcome == GATE_F
            )

        if progress_cb:
            progress_cb(20, "Projecting unique items")
        items, accounting = project_manifest_items(
            inventory,
            task_contract=rmanifest.task_contract,
            project_id=str(self.project_root.name),
        )
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")

        if progress_cb:
            progress_cb(45, "Building leakage graph")
        groups, leakage_meta = build_leakage_graph(items, policy_id=grouping_policy)

        mid = new_manifest_set_id()
        path = self.path_for(mid)
        path.mkdir(parents=True, exist_ok=True)

        rev = 1
        if parent_manifest_set_id:
            parent = self.load_manifest_set(parent_manifest_set_id)
            rev = int(parent.revision_number) + 1

        policy = SplitPolicy(
            policy_id=grouping_policy,
            policy_version=SPLIT_POLICY_VERSION,
            included_relations=list(leakage_meta.get("included_relations") or []),
            unavailable_relations=list(leakage_meta.get("unavailable_relations") or []),
            fallback_decisions=list(leakage_meta.get("fallback_decisions") or []),
            limitations=list(leakage_meta.get("limitations") or []),
            seed=int(seed),
        )

        blockers = []
        if gate_outcome != GATE_F or not authorizes_mlb:
            blockers.append(
                f"readiness_gate_not_F:outcome={gate_outcome or '(none)'}; "
                "draft planning allowed; final freeze and holdout reservation blocked"
            )
        eligible = [g for g in groups if g.eligible_untouched_holdout]
        if not eligible:
            blockers.append(
                "no_untouched_eligible_groups: no independent untouched group exists; "
                "do not randomly split frames within one protected component"
            )

        ms = ManifestSet(
            manifest_set_id=mid,
            title=title,
            description=description,
            project_id=str(self.project_root.name),
            created_at=_utc_now(),
            analyst_id=analyst_id,
            source_readiness_audit_id=audit_id,
            source_readiness_manifest_hash=rmanifest.manifest_hash,
            source_readiness_gate_outcome=gate_outcome,
            task_contract=rmanifest.task_contract,
            lifecycle_state="draft",
            grouping_policy=grouping_policy,
            seed=int(seed),
            parent_manifest_set_id=parent_manifest_set_id,
            revision_number=rev,
            revision_reason=revision_reason,
            item_count=len(items),
            group_count=len(groups),
            role_counts={},
            freeze_blockers=blockers,
            limitations=list(leakage_meta.get("limitations") or []),
            compatibility_warnings=list(rmanifest.compatibility_warnings or []),
        )

        snapshot = {
            "audit_id": audit_id,
            "manifest_hash": rmanifest.manifest_hash,
            "inventory_hash": rmanifest.inventory_hash,
            "task_contract": rmanifest.task_contract,
            "gate_outcome": gate_outcome,
            "authorizes_mlb_manifest_planning_only": authorizes_mlb,
            "lifecycle_state": rmanifest.lifecycle_state,
            "audit_protocol_version": rmanifest.audit_protocol_version,
            "projection_accounting": accounting,
            "leakage_meta": leakage_meta,
        }
        self._write_json(path / "input_readiness_snapshot.json", snapshot)
        self._write_json(path / "split_policy.json", policy.to_dict())
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])
        self._append_jsonl(
            path / "assignment_history.jsonl",
            {"event": "draft_created", "at": _utc_now(), "seed": seed, "policy": grouping_policy},
        )
        self._save_manifest_set(ms)
        if progress_cb:
            progress_cb(100, "Draft created")
        return self.load_manifest_set(mid)

    def build_leakage(
        self,
        manifest_set_id: str,
        *,
        grouping_policy: str | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> tuple[list[AtomicGroup], dict[str, Any]]:
        ms = self.load_manifest_set(manifest_set_id)
        self._assert_mutable(ms)
        items = self.load_items(manifest_set_id)
        policy_id = grouping_policy or ms.grouping_policy
        if progress_cb:
            progress_cb(30, "Building leakage graph")
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")
        groups, meta = build_leakage_graph(items, policy_id=policy_id)
        # Keep group.role aligned with any prior item role assignment (same graph identity)
        sync_group_roles_from_items(items, groups)
        if progress_cb:
            progress_cb(80, "Writing atomic groups")
        path = self.path_for(manifest_set_id)
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])
        coverage = build_coverage_report(items, groups)
        self._write_json(path / "group_coverage.json", coverage)
        policy = self.load_policy(manifest_set_id)
        policy.policy_id = policy_id
        policy.included_relations = list(meta.get("included_relations") or [])
        policy.unavailable_relations = list(meta.get("unavailable_relations") or [])
        policy.fallback_decisions = list(meta.get("fallback_decisions") or [])
        policy.limitations = list(meta.get("limitations") or [])
        self._write_json(path / "split_policy.json", policy.to_dict())
        ms.grouping_policy = policy_id
        ms.group_count = len(groups)
        ms.item_count = len(items)
        ms.role_counts = {}
        for it in items:
            ms.role_counts[it.role] = ms.role_counts.get(it.role, 0) + 1
        ms.group_role_counts = role_group_counts_from_items(items)
        ms.limitations = list(meta.get("limitations") or [])
        self._invalidate_validation(ms)
        self._save_manifest_set(ms)
        if progress_cb:
            progress_cb(100, "Leakage graph complete")
        return groups, meta

    def propose_split(
        self,
        manifest_set_id: str,
        *,
        seed: int | None = None,
        train_share: float | None = None,
        development_share: float | None = None,
        holdout_share: float | None = None,
        required_classes: list[str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        ms = self.load_manifest_set(manifest_set_id)
        self._assert_mutable(ms)
        items = self.load_items(manifest_set_id)
        groups = self.load_groups(manifest_set_id)
        if not groups:
            groups, _ = build_leakage_graph(items, policy_id=ms.grouping_policy)
        if progress_cb:
            progress_cb(40, "Generating deterministic proposal")
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")
        use_seed = int(ms.seed if seed is None else seed)
        items, groups, report = deterministic_proposal(
            items,
            groups,
            seed=use_seed,
            train_share=train_share,
            development_share=development_share,
            holdout_share=holdout_share,
            required_classes=required_classes,
        )
        # Non-F: do not reserve holdout — force holdout groups back to excluded
        if ms.source_readiness_gate_outcome != GATE_F:
            for g in groups:
                if g.role == "untouched_holdout":
                    g.role = "excluded"
            for it in items:
                if it.role == "untouched_holdout":
                    it.role = "excluded"
                    it.exclusion_reason = (
                        it.exclusion_reason or "holdout_blocked_gate_not_F"
                    )
            report["holdout_reservation_blocked"] = True
            report["role_counts"] = {}
            for it in items:
                report["role_counts"][it.role] = report["role_counts"].get(it.role, 0) + 1

        path = self.path_for(manifest_set_id)
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])
        coverage = build_coverage_report(items, groups)
        overlap = build_overlap_report(items, groups)
        self._write_json(path / "class_coverage.json", report.get("class_coverage") or {})
        self._write_json(path / "group_coverage.json", coverage)
        self._write_json(path / "overlap_report.json", overlap)
        policy = self.load_policy(manifest_set_id)
        policy.seed = use_seed
        policy.requested_train_share = train_share
        policy.requested_development_share = development_share
        policy.requested_holdout_share = holdout_share
        policy.required_target_classes = list(required_classes or [])
        policy.planning_mode = "deterministic_proposal"
        self._write_json(path / "split_policy.json", policy.to_dict())
        self._append_jsonl(
            path / "assignment_history.jsonl",
            {"event": "deterministic_proposal", "at": _utc_now(), "report": report},
        )
        ms.seed = use_seed
        ms.role_counts = report.get("role_counts") or {}
        ms.group_role_counts = report.get("group_role_counts") or {}
        self._invalidate_validation(ms)
        self._save_manifest_set(ms)
        if progress_cb:
            progress_cb(100, "Proposal complete")
        return report

    def assign_manual(
        self,
        manifest_set_id: str,
        group_role_map: dict[str, str],
    ) -> dict[str, Any]:
        ms = self.load_manifest_set(manifest_set_id)
        self._assert_mutable(ms)
        items = self.load_items(manifest_set_id)
        groups = self.load_groups(manifest_set_id)
        # Block holdout assignment when gate is not F
        if ms.source_readiness_gate_outcome != GATE_F:
            for gid, role in list(group_role_map.items()):
                if role == "untouched_holdout":
                    raise ManifestStoreError(
                        "Holdout reservation blocked: readiness Gate is not F"
                    )
        items, groups, report = apply_manual_assignments(items, groups, group_role_map)
        path = self.path_for(manifest_set_id)
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])
        coverage = build_coverage_report(items, groups)
        overlap = build_overlap_report(items, groups)
        self._write_json(path / "group_coverage.json", coverage)
        self._write_json(path / "overlap_report.json", overlap)
        self._append_jsonl(
            path / "assignment_history.jsonl",
            {"event": "manual_assignment", "at": _utc_now(), "map": group_role_map},
        )
        ms.role_counts = report.get("role_counts") or {}
        ms.group_role_counts = report.get("group_role_counts") or {}
        self._invalidate_validation(ms)
        self._save_manifest_set(ms)
        return report

    def validate(
        self,
        manifest_set_id: str,
        *,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        ms = self.load_manifest_set(manifest_set_id)
        if ms.lifecycle_state == "frozen":
            raise ManifestStoreError("Frozen manifest sets are immutable")
        items = self.load_items(manifest_set_id)
        groups = self.load_groups(manifest_set_id)
        sync_group_roles_from_items(items, groups)
        policy = self.load_policy(manifest_set_id)
        if progress_cb:
            progress_cb(40, "Validating split integrity")
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")
        overlap = build_overlap_report(items, groups)
        authorizes_mlb = ms.source_readiness_gate_outcome == GATE_F
        freeze_blockers = validate_freeze_eligibility(
            gate_outcome=ms.source_readiness_gate_outcome,
            authorizes_mlb_planning=authorizes_mlb,
            items=items,
            groups=groups,
            overlap=overlap,
            required_classes=policy.required_target_classes,
            protocol_exceptions=policy.protocol_exceptions,
        )
        # Persist synced group roles + refreshed coverage (single authority)
        path = self.path_for(manifest_set_id)
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])
        coverage = build_coverage_report(items, groups)
        self._write_json(path / "group_coverage.json", coverage)

        candidate_leak = []
        for it in items:
            d = it.to_dict()
            for k in d:
                if "candidate" in k.lower():
                    candidate_leak.append(k)

        content_hash = self.assignment_content_hash(
            items, groups, grouping_policy=ms.grouping_policy, seed=ms.seed
        )
        integrity_ok = bool(overlap.get("ok", False)) and not freeze_blockers
        holdout_items = [it for it in items if it.role == "untouched_holdout"]
        holdout_groups_n = len(
            {it.atomic_group_id for it in holdout_items if it.atomic_group_id}
        )
        role_group_counts = role_group_counts_from_items(items)
        report = {
            "ok": integrity_ok,
            "integrity_ok": integrity_ok,
            "overlap": overlap,
            "freeze_blockers": freeze_blockers,
            "blockers": list(freeze_blockers),
            "can_freeze": integrity_ok,
            "can_draft": True,
            "authorizes_training": False,
            "authorizes_mlc": False,
            "candidate_field_leak": candidate_leak,
            "dir_check": validate_manifest_dir(self.path_for(manifest_set_id)),
            "no_claim_en": NO_CLAIM_STATEMENT_EN,
            "no_claim_ru": NO_CLAIM_STATEMENT_RU,
            "manifest_set_id": manifest_set_id,
            "validated_content_hash": content_hash,
            "item_count": len(items),
            "group_count": len(groups),
            "role_counts": {},
            "role_group_counts": role_group_counts,
            "holdout_item_count": len(holdout_items),
            "holdout_group_count": holdout_groups_n,
            "overlap_error_count": len(overlap.get("errors") or []),
            "holdout_conflict_count": len(overlap.get("holdout_conflicts") or []),
            "validated_at": _utc_now() if integrity_ok else "",
            "lifecycle_state": "validated" if integrity_ok else "draft",
        }
        for it in items:
            report["role_counts"][it.role] = report["role_counts"].get(it.role, 0) + 1

        self._write_json(path / "integrity_report.json", report)
        self._write_json(path / "overlap_report.json", overlap)
        ms.freeze_blockers = freeze_blockers
        ms.role_counts = dict(report["role_counts"])
        ms.group_role_counts = dict(role_group_counts)
        ms.item_count = len(items)
        ms.group_count = len(groups)
        if integrity_ok:
            ms.lifecycle_state = "validated"
            ms.validated_at = report["validated_at"]
            ms.validated_content_hash = content_hash
            ms.last_validation_ok = True
        else:
            # Validated + integrity false is impossible
            if ms.lifecycle_state == "validated":
                ms.lifecycle_state = "draft"
            ms.validated_at = ""
            ms.validated_content_hash = ""
            ms.last_validation_ok = False
            report["lifecycle_state"] = ms.lifecycle_state
        self._save_manifest_set(ms)
        if progress_cb:
            progress_cb(100, "Validation complete")
        return report

    def freeze(
        self,
        manifest_set_id: str,
        *,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> ManifestSet:
        ms = self.load_manifest_set(manifest_set_id)
        self._assert_mutable(ms)
        if progress_cb:
            progress_cb(20, "Validating before freeze")
        report = self.validate(manifest_set_id)
        if not report.get("can_freeze"):
            raise ManifestStoreError(
                "Final freeze blocked: " + "; ".join(report.get("freeze_blockers") or [])
            )
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")
        if progress_cb:
            progress_cb(50, "Writing role manifests")
        items = self.load_items(manifest_set_id)
        groups = self.load_groups(manifest_set_id)
        path = self.path_for(manifest_set_id)

        train = [it for it in items if it.role == "train"]
        development = [it for it in items if it.role == "development"]
        holdout = [it for it in items if it.role == "untouched_holdout"]
        excluded = [it for it in items if it.role == "excluded"]

        # Mark holdout_reserved on holdout items (workflow state)
        for it in holdout:
            it.contamination_state = "holdout_reserved"

        self._write_jsonl(path / "train_manifest.jsonl", [it.to_dict() for it in train])
        self._write_jsonl(
            path / "development_manifest.jsonl", [it.to_dict() for it in development]
        )
        public_rows = [it.public_holdout_dict() for it in holdout]
        ref_rows = [it.reference_label_dict() for it in holdout]
        self._write_jsonl(path / "holdout_public_manifest.jsonl", public_rows)
        self._write_jsonl(path / "holdout_reference_labels.jsonl", ref_rows)
        self._write_jsonl(path / "excluded_manifest.jsonl", [it.to_dict() for it in excluded])
        self._write_jsonl(path / "item_index.jsonl", [it.to_dict() for it in items])
        self._write_jsonl(path / "atomic_groups.jsonl", [g.to_dict() for g in groups])

        pub_hash = deterministic_hash({"rows": public_rows})
        ref_hash = deterministic_hash({"rows": ref_rows})
        lock = HoldoutLockRecord(
            manifest_set_id=manifest_set_id,
            public_manifest_hash=pub_hash,
            reference_labels_hash=ref_hash,
            sealed_at=_utc_now(),
            workflow_seal_note=WORKFLOW_SEAL_NOTE_EN,
        )
        lock.lock_hash = lock.compute_lock_hash()
        self._write_json(path / "holdout_lock.json", lock.to_dict())

        coverage = build_coverage_report(items, groups)
        self._write_json(path / "group_coverage.json", coverage)
        summary = self._build_summary(ms, items, groups, report)
        self._write_json(path / "manifest_summary.json", summary)
        self._write_text(path / "manifest_summary.md", self._summary_md(summary))

        ms.lifecycle_state = "frozen"
        ms.frozen_at = _utc_now()
        ms.holdout_sealed = True
        ms.train_manifest_hash = deterministic_hash({"rows": [it.to_dict() for it in train]})
        ms.development_manifest_hash = deterministic_hash(
            {"rows": [it.to_dict() for it in development]}
        )
        ms.holdout_public_manifest_hash = pub_hash
        ms.holdout_reference_labels_hash = ref_hash
        ms.excluded_manifest_hash = deterministic_hash(
            {"rows": [it.to_dict() for it in excluded]}
        )
        ms.holdout_lock_hash = lock.lock_hash
        ms.role_counts = {
            "train": len(train),
            "development": len(development),
            "untouched_holdout": len(holdout),
            "excluded": len(excluded),
        }
        ms.group_role_counts = {}
        for g in groups:
            ms.group_role_counts[g.role] = ms.group_role_counts.get(g.role, 0) + 1
        ms.freeze_blockers = []
        self._save_manifest_set(ms)
        self._append_jsonl(
            path / "assignment_history.jsonl",
            {"event": "frozen", "at": ms.frozen_at, "lock_hash": lock.lock_hash},
        )
        if progress_cb:
            progress_cb(100, "Frozen")
        return self.load_manifest_set(manifest_set_id)

    def unlock_holdout(self, manifest_set_id: str) -> None:
        """ML-B must never unlock holdout reference labels."""
        raise ManifestStoreError(HOLDOUT_UNLOCK_FORBIDDEN_EN)

    def create_revision(
        self,
        parent_manifest_set_id: str,
        readiness_store: MLDatasetReadinessStore,
        *,
        revision_reason: str,
        analyst_id: str = "",
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> ManifestSet:
        parent = self.load_manifest_set(parent_manifest_set_id)
        if parent.lifecycle_state != "frozen":
            raise ManifestStoreError("Revisions require a frozen parent")
        return self.create_draft_from_readiness(
            readiness_store,
            audit_id=parent.source_readiness_audit_id,
            title=f"{parent.title} (revision)",
            description=parent.description,
            analyst_id=analyst_id or parent.analyst_id,
            grouping_policy=parent.grouping_policy,
            seed=parent.seed,
            parent_manifest_set_id=parent_manifest_set_id,
            revision_reason=revision_reason,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )

    def archive(self, manifest_set_id: str) -> ManifestSet:
        ms = self.load_manifest_set(manifest_set_id)
        if ms.lifecycle_state == "frozen":
            # Archiving frozen is allowed; content remains immutable
            ms.lifecycle_state = "archived"
            self._save_manifest_set(ms)
            return ms
        self._assert_mutable(ms)
        ms.lifecycle_state = "archived"
        self._save_manifest_set(ms)
        return ms

    def export_bundle(
        self,
        manifest_set_id: str,
        export_dir: Path | str | None = None,
        *,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> Path:
        """Export public manifests/reports. Does not create a new manifest set.
        Does not export sealed holdout reference labels.
        """
        ms = self.load_manifest_set(manifest_set_id)
        items = self.load_items(manifest_set_id)
        groups = self.load_groups(manifest_set_id)
        if export_dir is None:
            out = (
                self.project_root
                / "review_dataset"
                / "exports"
                / f"ml_manifests_{manifest_set_id}"
            )
        else:
            out = Path(export_dir)
        out.mkdir(parents=True, exist_ok=True)
        if progress_cb:
            progress_cb(30, "Writing exports")
        if cancel_cb and cancel_cb():
            raise ManifestStoreError("cancelled")

        summary = self._build_summary(
            ms,
            items,
            groups,
            self._read_json(self.path_for(manifest_set_id) / "integrity_report.json")
            if (self.path_for(manifest_set_id) / "integrity_report.json").exists()
            else {},
        )
        self._write_json(out / "manifest_summary.json", summary)
        self._write_text(out / "manifest_summary.md", self._summary_md(summary))

        def _role_rows(role: str) -> list[dict[str, Any]]:
            return [it.to_dict() for it in items if it.role == role]

        for role, fname in (
            ("train", "train_manifest"),
            ("development", "development_manifest"),
            ("excluded", "excluded_manifest"),
        ):
            rows = _role_rows(role)
            self._write_jsonl(out / f"{fname}.jsonl", rows)
            self._write_csv(out / f"{fname}.csv", rows)

        # Public holdout only
        pub_path = self.path_for(manifest_set_id) / "holdout_public_manifest.jsonl"
        if pub_path.exists():
            pub = self._read_jsonl(pub_path)
        else:
            pub = [
                it.public_holdout_dict()
                for it in items
                if it.role == "untouched_holdout"
            ]
        self._write_jsonl(out / "holdout_public_manifest.jsonl", pub)
        self._write_csv(out / "holdout_public_manifest.csv", pub)

        self._write_csv(out / "atomic_groups.csv", [g.to_dict() for g in groups])
        coverage = build_coverage_report(items, groups)
        self._write_json(out / "role_coverage.json", coverage)
        # Flatten coverage for CSV
        cov_rows = []
        for level, roles in coverage.items():
            for role, stats in roles.items():
                cov_rows.append(
                    {
                        "level": level,
                        "role": role,
                        "unique_items": stats.get("unique_items", stats.get("items_in_groups", 0)),
                        "atomic_groups": stats.get("atomic_groups", 0),
                    }
                )
        self._write_csv(out / "role_coverage.csv", cov_rows)

        overlap = build_overlap_report(items, groups)
        self._write_json(out / "overlap_report.json", overlap)
        self._write_text(
            out / "overlap_report.md",
            "# Overlap report\n\n"
            + "\n".join(f"- {e}" for e in overlap.get("errors") or ["(none)"])
            + "\n",
        )
        contam_rows = [
            {
                "item_id": it.item_id,
                "role": it.role,
                "contamination_state": it.contamination_state,
                "sequence_id": it.sequence_id,
                "related_frame_group": it.related_frame_group,
            }
            for it in items
        ]
        self._write_csv(out / "contamination_report.csv", contam_rows)
        if (self.path_for(manifest_set_id) / "integrity_report.json").exists():
            self._write_json(
                out / "integrity_report.json",
                self._read_json(self.path_for(manifest_set_id) / "integrity_report.json"),
            )
        if (self.path_for(manifest_set_id) / "holdout_lock.json").exists():
            self._write_json(
                out / "holdout_lock.json",
                self._read_json(self.path_for(manifest_set_id) / "holdout_lock.json"),
            )
        # Explicitly do NOT copy holdout_reference_labels.jsonl
        meta = {
            "manifest_set_id": manifest_set_id,
            "source_readiness_audit_id": ms.source_readiness_audit_id,
            "source_readiness_manifest_hash": ms.source_readiness_manifest_hash,
            "task_contract": ms.task_contract,
            "protocol_version": MANIFEST_PROTOCOL_VERSION,
            "grouping_policy": ms.grouping_policy,
            "seed": ms.seed,
            "role_counts": ms.role_counts,
            "group_counts": ms.group_role_counts,
            "limitations": ms.limitations,
            "no_training": True,
            "no_claim_en": NO_CLAIM_STATEMENT_EN,
            "reference_labels_exported": False,
        }
        self._write_json(out / "export_meta.json", meta)
        if progress_cb:
            progress_cb(100, "Export complete")
        return out

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        # Flatten simple values
        keys: list[str] = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                flat = {
                    k: (
                        json.dumps(v, ensure_ascii=False)
                        if isinstance(v, (list, dict))
                        else v
                    )
                    for k, v in r.items()
                }
                w.writerow(flat)

    def _build_summary(
        self,
        ms: ManifestSet,
        items: list[ManifestItemRecord],
        groups: list[AtomicGroup],
        integrity: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "manifest_set_id": ms.manifest_set_id,
            "title": ms.title,
            "lifecycle_state": ms.lifecycle_state,
            "task_contract": ms.task_contract,
            "protocol_version": MANIFEST_PROTOCOL_VERSION,
            "source_readiness_audit_id": ms.source_readiness_audit_id,
            "source_readiness_manifest_hash": ms.source_readiness_manifest_hash,
            "source_readiness_gate_outcome": ms.source_readiness_gate_outcome,
            "grouping_policy": ms.grouping_policy,
            "seed": ms.seed,
            "item_count": len(items),
            "group_count": len(groups),
            "role_counts": ms.role_counts,
            "group_role_counts": ms.group_role_counts,
            "freeze_blockers": ms.freeze_blockers or integrity.get("freeze_blockers") or [],
            "holdout_sealed": ms.holdout_sealed,
            "authorizes_training": False,
            "authorizes_mlc": False,
            "limitations": ms.limitations,
            "no_claim_en": NO_CLAIM_STATEMENT_EN,
            "no_claim_ru": NO_CLAIM_STATEMENT_RU,
            "workflow_seal_note": WORKFLOW_SEAL_NOTE_EN,
        }

    def _summary_md(self, summary: dict[str, Any]) -> str:
        lines = [
            f"# Manifest set {summary.get('manifest_set_id')}",
            "",
            f"- Title: {summary.get('title')}",
            f"- Lifecycle: {summary.get('lifecycle_state')}",
            f"- Task contract: {summary.get('task_contract')}",
            f"- Protocol: {summary.get('protocol_version')}",
            f"- Source readiness audit: {summary.get('source_readiness_audit_id')}",
            f"- Gate outcome: {summary.get('source_readiness_gate_outcome')}",
            f"- Grouping policy: {summary.get('grouping_policy')}",
            f"- Seed: {summary.get('seed')}",
            f"- Items: {summary.get('item_count')}; groups: {summary.get('group_count')}",
            f"- Role counts: {summary.get('role_counts')}",
            f"- Holdout sealed: {summary.get('holdout_sealed')}",
            f"- Authorizes training: false",
            f"- Authorizes ML-C: false",
            "",
            "## Freeze blockers",
        ]
        blockers = summary.get("freeze_blockers") or []
        if blockers:
            lines.extend(f"- {b}" for b in blockers)
        else:
            lines.append("- (none)")
        lines.extend(["", "## Statement", "", summary.get("no_claim_en", ""), ""])
        return "\n".join(lines) + "\n"


# Re-export for typing convenience
__all__ = [
    "MLDatasetManifestStore",
    "ManifestStoreError",
    "InventoryItemRecord",
]
