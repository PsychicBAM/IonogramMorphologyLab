"""Project-scoped morphology review corpus store (append-only JSONL)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ionogram_morphology_lab.morphology_candidate.types import CANDIDATE_ENGINE_VERSION
from ionogram_morphology_lab.morphology_review_corpus.constants import CORPORA_DIRNAME
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    assert_no_absolute_paths,
    deterministic_hash,
    validate_sha256,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import (
    comparison_status,
    rationale_required,
)
from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
    CorpusLifecycleError,
    is_legacy_synthetic_cohort,
    is_legacy_synthetic_item,
    set_archived,
)
from ionogram_morphology_lab.morphology_review_corpus.models import (
    AdjudicationRecord,
    AuditEvent,
    BlindReviewRecord,
    CandidateSnapshot,
    CohortManifest,
    RevealComparison,
    ReviewItem,
    ReviewerIdentity,
)
from ionogram_morphology_lab.morphology_review_corpus.protocol import CohortProtocol
from ionogram_morphology_lab.morphology_review_corpus.sampling import (
    import_manifest,
    manual_selection,
    mark_availability,
    random_sample,
    stratified_sample,
)

_COHORT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def corpora_root(project_root: Path | str) -> Path:
    return Path(project_root) / CORPORA_DIRNAME


def cohort_dir(project_root: Path | str, cohort_id: str) -> Path:
    return corpora_root(project_root) / cohort_id


class FrozenCohortError(CorpusLifecycleError):
    """Raised when a frozen/immutable cohort rejects mutation or review gating fails."""

    def __init__(self, message_en: str = "", *, code: str = "frozen_immutable"):
        super().__init__(code, message_en or code)


class BlindRevealError(RuntimeError):
    pass


class MorphologyReviewCorpusStore:
    """Filesystem-backed store for one project's morphology review corpora."""

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.root = corpora_root(self.project_root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ paths
    def path_for(self, cohort_id: str) -> Path:
        self._check_cohort_id(cohort_id)
        return cohort_dir(self.project_root, cohort_id)

    def list_cohorts(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and (p / "cohort_manifest.json").is_file()
        )

    # -------------------------------------------------------------- create
    def create_cohort(
        self,
        *,
        cohort_id: str | None = None,
        protocol: CohortProtocol | None = None,
        items: list[dict[str, Any]] | None = None,
        sampling_method: str = "manual",
        random_seed: int | None = None,
        ruleset_hash: str = "",
        feature_version: str = "",
        source_inventory_snapshot: dict[str, Any] | None = None,
        parent_cohort_id: str = "",
        revision_reason: str = "",
        revision_number: int = 0,
        created_from_manifest_hash: str = "",
        created_from_protocol_hash: str = "",
        sha_exists: Callable[[str], bool] | None = None,
        frame_valid: Callable[[str, int], bool] | None = None,
    ) -> CohortManifest:
        cid = cohort_id or f"cohort_{uuid4().hex[:12]}"
        self._check_cohort_id(cid)
        d = self.path_for(cid)
        if d.exists():
            raise FileExistsError(f"Cohort already exists: {cid}")
        d.mkdir(parents=True, exist_ok=False)
        (d / "snapshots").mkdir(exist_ok=True)
        (d / "exports").mkdir(exist_ok=True)
        for name in (
            "items.jsonl",
            "candidate_snapshots.jsonl",
            "blind_reviews.jsonl",
            "reveal_comparisons.jsonl",
            "adjudications.jsonl",
            "comments.jsonl",
            "audit_log.jsonl",
        ):
            (d / name).write_text("", encoding="utf-8")
        (d / "reviewers.json").write_text("[]\n", encoding="utf-8")

        proto = (protocol or CohortProtocol(sampling_mode=sampling_method)).with_hash()
        raw_items = list(items or [])
        if sha_exists is not None:
            raw_items = mark_availability(
                raw_items, sha_exists=sha_exists, frame_valid=frame_valid
            )
        review_items = [
            self._normalize_item(cid, row, position=i) for i, row in enumerate(raw_items)
        ]
        self._write_json(d / "protocol.json", proto.to_dict())
        self._rewrite_jsonl(d / "items.jsonl", [it.to_dict() for it in review_items])
        legacy = is_legacy_synthetic_cohort(
            CohortManifest(
                cohort_id=cid,
                designation_en=proto.designation_en,
                designation_ru=proto.designation_ru,
            ),
            review_items,
        )
        manifest = CohortManifest(
            cohort_id=cid,
            sampling_method=sampling_method,
            random_seed=random_seed,
            ruleset_hash=ruleset_hash,
            feature_version=feature_version,
            source_inventory_snapshot=dict(source_inventory_snapshot or {}),
            protocol_hash=proto.protocol_hash,
            parent_cohort_id=parent_cohort_id,
            revision_reason=revision_reason,
            revision_number=int(revision_number or 0),
            created_from_manifest_hash=created_from_manifest_hash,
            created_from_protocol_hash=created_from_protocol_hash,
            item_count=len(review_items),
            designation_en=proto.designation_en,
            designation_ru=proto.designation_ru,
            candidate_engine_version=CANDIDATE_ENGINE_VERSION,
            legacy_synthetic=legacy,
        ).with_hash()
        self._write_json(d / "cohort_manifest.json", manifest.to_dict())
        self.append_audit(
            cid,
            AuditEvent.create(
                "cohort_creation",
                cohort_id=cid,
                new_record_hash=manifest.manifest_hash,
                details={
                    "item_count": len(review_items),
                    "sampling_method": sampling_method,
                    "legacy_synthetic": legacy,
                    "parent_cohort_id": parent_cohort_id,
                    "revision_number": revision_number,
                },
            ),
        )
        return manifest

    def create_from_sampling(
        self,
        *,
        pool: list[dict[str, Any]],
        mode: str,
        count: int | None = None,
        seed: int | None = None,
        strata_key: str = "candidate_state",
        per_stratum: int = 1,
        cohort_id: str | None = None,
        **kwargs: Any,
    ) -> CohortManifest:
        if mode == "manual":
            selected = manual_selection(pool)
        elif mode == "random":
            if seed is None or count is None:
                raise ValueError("random sampling requires seed and count")
            selected = random_sample(pool, count=count, seed=seed)
        elif mode == "stratified":
            if seed is None:
                raise ValueError("stratified sampling requires seed")
            selected = stratified_sample(
                pool,
                strata_key=strata_key,
                per_stratum=per_stratum,
                seed=seed,
                total_cap=count,
            )
        elif mode == "import":
            raise ValueError("Use create_from_import_manifest for import mode")
        else:
            raise ValueError(f"Unknown sampling mode: {mode!r}")
        return self.create_cohort(
            cohort_id=cohort_id,
            items=selected,
            sampling_method=mode,
            random_seed=seed,
            **kwargs,
        )

    def create_from_import_manifest(
        self,
        path: Path | str,
        *,
        cohort_id: str | None = None,
        sha_exists: Callable[[str], bool] | None = None,
        frame_valid: Callable[[str, int], bool] | None = None,
        **kwargs: Any,
    ) -> CohortManifest:
        items = import_manifest(path)
        return self.create_cohort(
            cohort_id=cohort_id,
            items=items,
            sampling_method="import",
            sha_exists=sha_exists,
            frame_valid=frame_valid,
            **kwargs,
        )

    # -------------------------------------------------------------- draft edit
    def load_manifest(self, cohort_id: str) -> CohortManifest:
        data = self._read_json(self.path_for(cohort_id) / "cohort_manifest.json")
        manifest = CohortManifest.from_dict(data)
        # Detect legacy synthetic for older corpora that lack the flag
        if not manifest.legacy_synthetic:
            items = self.load_items(cohort_id)
            if is_legacy_synthetic_cohort(manifest, items):
                manifest.legacy_synthetic = True
        return manifest

    def load_protocol(self, cohort_id: str) -> CohortProtocol:
        data = self._read_json(self.path_for(cohort_id) / "protocol.json")
        return CohortProtocol.from_dict(data)

    def load_items(self, cohort_id: str) -> list[ReviewItem]:
        return [
            ReviewItem.from_dict(r)
            for r in self._read_jsonl(self.path_for(cohort_id) / "items.jsonl")
        ]

    def update_protocol_draft(self, cohort_id: str, protocol: CohortProtocol) -> CohortProtocol:
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError("Cannot change protocol after freeze")
        proto = protocol.with_hash()
        self._write_json(self.path_for(cohort_id) / "protocol.json", proto.to_dict())
        manifest.protocol_hash = proto.protocol_hash
        manifest = manifest.with_hash()
        self._write_json(self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict())
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "protocol_change",
                cohort_id=cohort_id,
                new_record_hash=proto.protocol_hash,
            ),
        )
        return proto

    def replace_items_draft(
        self, cohort_id: str, items: list[dict[str, Any]]
    ) -> list[ReviewItem]:
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError("Cannot replace items after freeze")
        review_items = [
            self._normalize_item(cohort_id, row, position=i) for i, row in enumerate(items)
        ]
        self._rewrite_jsonl(
            self.path_for(cohort_id) / "items.jsonl",
            [it.to_dict() for it in review_items],
        )
        manifest.item_count = len(review_items)
        manifest = manifest.with_hash()
        self._write_json(self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict())
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "item_replacement",
                cohort_id=cohort_id,
                details={"item_count": len(review_items)},
                new_record_hash=manifest.manifest_hash,
            ),
        )
        return review_items

    def add_items_to_draft(
        self,
        cohort_id: str,
        new_items: list[dict[str, Any]],
        *,
        allow_legacy_import: bool = False,
    ) -> dict[str, Any]:
        """Append items to a draft cohort; reject frozen; report duplicates."""
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError(
                "Frozen cohort cannot receive new items",
                code="frozen_cannot_add",
            )
        if not allow_legacy_import and not manifest.legacy_synthetic:
            for row in new_items:
                if is_legacy_synthetic_item(row):
                    raise CorpusLifecycleError(
                        "legacy_item_blocked",
                        "Legacy synthetic items cannot be added to a real cohort "
                        "without explicit import/mapping",
                    )
        existing = self.load_items(cohort_id)
        by_identity = {it.identity_key(): it for it in existing}
        added: list[ReviewItem] = []
        duplicates: list[str] = []
        for row in new_items:
            sha = str(row.get("source_sha256") or "").lower()
            frame = int(row.get("frame_index") if row.get("frame_index") is not None else -1)
            key = (sha, frame)
            if key in by_identity and sha:
                duplicates.append(f"{sha[:12]}#{frame}")
                continue
            pos = len(existing) + len(added)
            item = self._normalize_item(cohort_id, row, position=pos)
            by_identity[item.identity_key()] = item
            added.append(item)
        if added:
            all_items = existing + added
            # Re-number positions stably
            out = []
            for i, it in enumerate(all_items):
                d = it.to_dict()
                d["manifest_position"] = i
                out.append(d)
            self._rewrite_jsonl(self.path_for(cohort_id) / "items.jsonl", out)
            manifest.item_count = len(out)
            manifest = manifest.with_hash()
            self._write_json(
                self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict()
            )
            self.append_audit(
                cohort_id,
                AuditEvent.create(
                    "item_addition",
                    cohort_id=cohort_id,
                    details={"added": len(added), "duplicates": len(duplicates)},
                    new_record_hash=manifest.manifest_hash,
                ),
            )
        return {
            "added": len(added),
            "duplicates": duplicates,
            "item_count": manifest.item_count,
            "added_ids": [a.item_id for a in added],
        }

    def remove_items_from_draft(
        self,
        cohort_id: str,
        *,
        item_ids: list[str] | None = None,
        identities: list[tuple[str, int]] | None = None,
    ) -> dict[str, Any]:
        """Remove draft items by item_id and/or (sha, frame). Frozen rejected."""
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError(
                "Frozen cohort cannot remove items",
                code="frozen_cannot_remove",
            )
        id_set = set(item_ids or [])
        ident_set = {(s.lower(), int(f)) for s, f in (identities or [])}
        existing = self.load_items(cohort_id)
        kept: list[ReviewItem] = []
        removed: list[dict[str, Any]] = []
        for it in existing:
            hit = it.item_id in id_set or it.identity_key() in ident_set
            if hit:
                removed.append(
                    {
                        "item_id": it.item_id,
                        "source_sha256": it.source_sha256,
                        "frame_index": it.frame_index,
                        "source_display_name": it.source_display_name,
                        "frame_time": it.frame_time,
                    }
                )
            else:
                kept.append(it)
        if not removed:
            return {
                "removed_count": 0,
                "item_count": len(existing),
                "removed_ids": [],
                "removed_items": [],
            }
        out = []
        for i, it in enumerate(kept):
            d = it.to_dict()
            d["manifest_position"] = i
            out.append(d)
        self._rewrite_jsonl(self.path_for(cohort_id) / "items.jsonl", out)
        manifest.item_count = len(out)
        # Refresh legacy flag
        manifest.legacy_synthetic = is_legacy_synthetic_cohort(
            manifest, [ReviewItem.from_dict(x) for x in out]
        )
        manifest = manifest.with_hash()
        self._write_json(
            self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict()
        )
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "item_removal",
                cohort_id=cohort_id,
                details={"removed": removed, "count": len(removed)},
                new_record_hash=manifest.manifest_hash,
            ),
        )
        return {
            "removed_count": len(removed),
            "item_count": len(out),
            "removed_ids": [r["item_id"] for r in removed],
            "removed_items": removed,
        }

    def clear_draft(self, cohort_id: str) -> dict[str, Any]:
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError(
                "Frozen cohort cannot be cleared",
                code="frozen_cannot_clear",
            )
        existing = self.load_items(cohort_id)
        identities = [
            {
                "item_id": it.item_id,
                "source_sha256": it.source_sha256,
                "frame_index": it.frame_index,
            }
            for it in existing
        ]
        self._rewrite_jsonl(self.path_for(cohort_id) / "items.jsonl", [])
        manifest.item_count = 0
        manifest.legacy_synthetic = False
        manifest = manifest.with_hash()
        self._write_json(
            self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict()
        )
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "draft_clear",
                cohort_id=cohort_id,
                details={"cleared_identities": identities, "count": len(identities)},
                new_record_hash=manifest.manifest_hash,
            ),
        )
        return {"cleared": len(identities), "item_count": 0}

    def delete_draft(self, cohort_id: str) -> None:
        """Delete a draft cohort directory. Frozen and reviewed corpora rejected."""
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError(
                "Frozen cohort cannot be deleted; archive instead",
                code="frozen_cannot_delete",
            )
        reviews = self._read_jsonl(self.path_for(cohort_id) / "blind_reviews.jsonl")
        comps = self._read_jsonl(self.path_for(cohort_id) / "reveal_comparisons.jsonl")
        adjs = self._read_jsonl(self.path_for(cohort_id) / "adjudications.jsonl")
        if reviews or comps or adjs:
            raise CorpusLifecycleError(
                "draft_has_reviews",
                "Draft with locked reviews or comparisons cannot be deleted",
            )
        import shutil

        d = self.path_for(cohort_id)
        shutil.rmtree(d)
        # workspace cleanup
        from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
            load_workspace,
            save_workspace,
        )

        ws = load_workspace(self.project_root)
        ids = [x for x in (ws.get("archived_cohort_ids") or []) if x != cohort_id]
        ws["archived_cohort_ids"] = ids
        if ws.get("selected_cohort_id") == cohort_id:
            ws["selected_cohort_id"] = ""
        save_workspace(self.project_root, ws)

    def draft_contains_identity(
        self, cohort_id: str, source_sha256: str, frame_index: int
    ) -> bool:
        key = ((source_sha256 or "").lower(), int(frame_index))
        return any(it.identity_key() == key for it in self.load_items(cohort_id))

    def freeze_cohort(
        self,
        cohort_id: str,
        *,
        candidate_snapshots: list[CandidateSnapshot] | None = None,
    ) -> CohortManifest:
        """Freeze cohort — RU: «Зафиксировать корпус» / EN: Freeze cohort."""
        manifest = self.load_manifest(cohort_id)
        if manifest.frozen:
            raise FrozenCohortError("Cohort already frozen")
        items = self.load_items(cohort_id)
        if not items:
            raise FrozenCohortError("Cannot freeze a cohort with zero items")
        d = self.path_for(cohort_id)
        if candidate_snapshots:
            for snap in candidate_snapshots:
                self._append_jsonl(d / "candidate_snapshots.jsonl", snap.with_hash().to_dict())
        from datetime import datetime, timezone

        manifest.frozen = True
        manifest.frozen_at = datetime.now(timezone.utc).isoformat()
        proto = self.load_protocol(cohort_id)
        proto.cohort_lock_state = "frozen"
        proto = proto.with_hash()
        self._write_json(d / "protocol.json", proto.to_dict())
        manifest.protocol_hash = proto.protocol_hash
        manifest = manifest.with_hash()
        self._write_json(d / "cohort_manifest.json", manifest.to_dict())
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "cohort_freeze",
                cohort_id=cohort_id,
                new_record_hash=manifest.manifest_hash,
            ),
        )
        return manifest

    def create_editable_revision(
        self,
        cohort_id: str,
        *,
        reason: str,
        new_cohort_id: str | None = None,
    ) -> CohortManifest:
        """Create a new draft child from a frozen parent — never unfreeze in place."""
        if not (reason or "").strip():
            raise CorpusLifecycleError(
                "revision_reason_required",
                "Revision reason required",
            )
        parent = self.load_manifest(cohort_id)
        if not parent.frozen:
            raise CorpusLifecycleError(
                "revision_requires_frozen",
                "Editable revision requires a frozen parent cohort",
            )
        parent_hash_before = parent.manifest_hash
        parent_proto = self.load_protocol(cohort_id)
        parent_proto_hash = parent_proto.protocol_hash
        # Copy item identities only — mint new item_ids; never copy review state
        items = []
        for i, it in enumerate(self.load_items(cohort_id)):
            items.append(self._sanitize_item_row_for_revision(it.to_dict(), position=i))
        rev_num = int(parent.revision_number or 0) + 1
        if not new_cohort_id:
            new_cohort_id = f"{cohort_id}_r{rev_num}"
            # ensure unique
            base = new_cohort_id
            n = 1
            while self.path_for(new_cohort_id).exists():
                new_cohort_id = f"{base}_{n}"
                n += 1
        proto = CohortProtocol.from_dict(parent_proto.to_dict())
        proto.cohort_lock_state = "draft"
        proto.protocol_hash = ""
        child = self.create_cohort(
            cohort_id=new_cohort_id,
            protocol=proto,
            items=items,
            sampling_method=parent.sampling_method,
            random_seed=parent.random_seed,
            ruleset_hash=parent.ruleset_hash,
            feature_version=parent.feature_version,
            source_inventory_snapshot=parent.source_inventory_snapshot,
            parent_cohort_id=cohort_id,
            revision_reason=reason.strip(),
            revision_number=rev_num,
            created_from_manifest_hash=parent_hash_before,
            created_from_protocol_hash=parent_proto_hash,
        )
        # Parent unchanged — verify hash
        parent_after = self.load_manifest(cohort_id)
        if parent_after.manifest_hash != parent_hash_before:
            raise RuntimeError("Parent manifest was mutated during revision — abort")
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "cohort_revision_spawned",
                cohort_id=cohort_id,
                details={
                    "child_cohort_id": child.cohort_id,
                    "revision_number": rev_num,
                    "reason": reason.strip(),
                },
                prior_record_hash=parent_hash_before,
                new_record_hash=parent_hash_before,
            ),
        )
        self.append_audit(
            child.cohort_id,
            AuditEvent.create(
                "cohort_revision_created",
                cohort_id=child.cohort_id,
                details={
                    "parent_cohort_id": cohort_id,
                    "revision_number": rev_num,
                    "reason": reason.strip(),
                    "created_from_manifest_hash": parent_hash_before,
                },
                new_record_hash=child.manifest_hash,
            ),
        )
        # Hard guarantee: review stores must be empty
        for name in (
            "blind_reviews.jsonl",
            "reveal_comparisons.jsonl",
            "adjudications.jsonl",
            "comments.jsonl",
        ):
            text = (self.path_for(child.cohort_id) / name).read_text(encoding="utf-8").strip()
            if text:
                raise RuntimeError(f"Revision child leaked {name}")
        for it in self.load_items(child.cohort_id):
            if it.item_status not in ("item_pending", "item_unavailable"):
                raise RuntimeError(f"Revision child item status not pending: {it.item_status}")
        return child

    @staticmethod
    def _sanitize_item_row_for_revision(row: dict[str, Any], *, position: int) -> dict[str, Any]:
        """Keep identity/order/metadata; reset status; mint new item_id."""
        sha = str(row.get("source_sha256") or "").lower()
        frame = int(row.get("frame_index") if row.get("frame_index") is not None else 0)
        parent_item_id = str(row.get("item_id") or "")
        status = str(row.get("item_status") or "item_pending")
        if status != "item_unavailable":
            status = "item_pending"
        new_id = f"item_{position:04d}_{(sha[:8] if sha else 'nosha')}_{frame}_r{uuid4().hex[:6]}"
        keep_keys = (
            "source_inventory_id",
            "source_display_name",
            "source_sha256",
            "frame_index",
            "frame_time",
            "datetime_metadata",
            "feature_version",
            "diagnostics_cache_id",
            "v2_result_hash",
            "v2_quality_status",
            "candidate_result_hash",
            "candidate_engine_version",
            "ruleset_id",
            "ruleset_hash",
            "evidence_ledger_hash",
            "rendering_snapshot",
            "inclusion_reason",
            "sampling_stratum",
            "partition",
            "unavailable_reason",
            "grouping",
        )
        out = {k: row.get(k) for k in keep_keys if k in row}
        out["item_id"] = new_id
        out["parent_item_id"] = parent_item_id
        out["item_status"] = status
        out["manifest_position"] = position
        if row.get("cohort_id"):
            out["cohort_id"] = row["cohort_id"]
        return out

    def repair_revision_integrity(self, cohort_id: str) -> dict[str, Any]:
        """Repair a child revision that inherited review statuses/IDs. Never mutates parent."""
        manifest = self.load_manifest(cohort_id)
        if not manifest.parent_cohort_id:
            return {"repaired": False, "reason": "not_a_revision_child"}
        parent_id = manifest.parent_cohort_id
        parent_items = {}
        if self.path_for(parent_id).exists():
            parent_items = {it.item_id: it for it in self.load_items(parent_id)}
        child_items = self.load_items(cohort_id)
        completed = {
            "blind_review_locked",
            "second_review_locked",
            "comparison_recorded",
            "adjudication_locked",
            "item_complete",
            "blind_review_in_progress",
        }
        needs = False
        # Detect leaked review JSONL
        for name in ("blind_reviews.jsonl", "reveal_comparisons.jsonl", "adjudications.jsonl"):
            p = self.path_for(cohort_id) / name
            if p.is_file() and p.read_text(encoding="utf-8").strip():
                needs = True
                quarantine = p.with_suffix(p.suffix + ".quarantine")
                p.replace(quarantine)
                p.write_text("", encoding="utf-8")
        # Detect status / id collision
        out_rows: list[dict[str, Any]] = []
        reminted = 0
        for i, it in enumerate(child_items):
            row = it.to_dict()
            collide = it.item_id in parent_items
            bad_status = it.item_status in completed
            if collide or bad_status:
                needs = True
                row = self._sanitize_item_row_for_revision(row, position=i)
                reminted += 1
            else:
                if row.get("item_status") not in ("item_pending", "item_unavailable"):
                    row["item_status"] = "item_pending"
                    needs = True
                row["manifest_position"] = i
            out_rows.append(row)
        if needs:
            for row in out_rows:
                row["cohort_id"] = cohort_id
            self._rewrite_jsonl(self.path_for(cohort_id) / "items.jsonl", out_rows)
            manifest.item_count = len(out_rows)
            # Do not change frozen scientific hash of a frozen child unless draft —
            # for frozen children only rewrite items if leaked; re-hash draft only.
            if not manifest.frozen:
                manifest = manifest.with_hash()
                self._write_json(
                    self.path_for(cohort_id) / "cohort_manifest.json", manifest.to_dict()
                )
            self.append_audit(
                cohort_id,
                AuditEvent.create(
                    "revision_integrity_repaired",
                    cohort_id=cohort_id,
                    details={
                        "parent_cohort_id": parent_id,
                        "reminted_items": reminted,
                        "parent_untouched": True,
                    },
                ),
            )
        return {
            "repaired": needs,
            "reminted_items": reminted,
            "parent_cohort_id": parent_id,
        }

    def detect_revision_leakage(self, cohort_id: str) -> list[str]:
        """Return human-readable leakage markers for a revision child."""
        issues: list[str] = []
        manifest = self.load_manifest(cohort_id)
        if not manifest.parent_cohort_id:
            return issues
        for name in ("blind_reviews.jsonl", "reveal_comparisons.jsonl", "adjudications.jsonl"):
            p = self.path_for(cohort_id) / name
            if p.is_file() and p.read_text(encoding="utf-8").strip():
                issues.append(f"nonempty_{name}")
        parent_ids = set()
        if self.path_for(manifest.parent_cohort_id).exists():
            parent_ids = {it.item_id for it in self.load_items(manifest.parent_cohort_id)}
        for it in self.load_items(cohort_id):
            if it.item_id in parent_ids:
                issues.append(f"shared_item_id:{it.item_id}")
            if it.item_status not in ("item_pending", "item_unavailable"):
                issues.append(f"status:{it.item_id}:{it.item_status}")
        return issues

    def revise_cohort(
        self,
        cohort_id: str,
        *,
        reason: str,
        new_cohort_id: str | None = None,
    ) -> CohortManifest:
        """Alias for create_editable_revision (frozen parent required)."""
        return self.create_editable_revision(
            cohort_id, reason=reason, new_cohort_id=new_cohort_id
        )

    def archive_cohort(self, cohort_id: str) -> None:
        """UI/workspace archive — does not mutate scientific manifest hash."""
        self.load_manifest(cohort_id)  # exists
        set_archived(self.project_root, cohort_id, True)
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "cohort_archive",
                cohort_id=cohort_id,
                details={"archived": True, "workspace_only": True},
            ),
        )

    def unarchive_cohort(self, cohort_id: str) -> None:
        self.load_manifest(cohort_id)
        set_archived(self.project_root, cohort_id, False)
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "cohort_unarchive",
                cohort_id=cohort_id,
                details={"archived": False, "workspace_only": True},
            ),
        )

    # ----------------------------------------------------------- reviewers
    def list_reviewers(self, cohort_id: str) -> list[ReviewerIdentity]:
        data = self._read_json(self.path_for(cohort_id) / "reviewers.json")
        if not isinstance(data, list):
            return []
        return [ReviewerIdentity.from_dict(x) for x in data]

    def upsert_reviewer(self, cohort_id: str, reviewer: ReviewerIdentity) -> ReviewerIdentity:
        rows = self.list_reviewers(cohort_id)
        out = []
        found = False
        for r in rows:
            if r.reviewer_id == reviewer.reviewer_id:
                out.append(reviewer)
                found = True
            else:
                out.append(r)
        if not found:
            out.append(reviewer)
        self._write_json(
            self.path_for(cohort_id) / "reviewers.json",
            [r.to_dict() for r in out],
        )
        return reviewer

    # --------------------------------------------------------- blind review
    def current_blind_reviews(
        self, cohort_id: str, *, review_round: int | None = None
    ) -> dict[str, BlindReviewRecord]:
        """Latest non-superseded review per (item_id, review_round)."""
        current: dict[tuple[str, int], BlindReviewRecord] = {}
        for row in self._read_jsonl(self.path_for(cohort_id) / "blind_reviews.jsonl"):
            rec = BlindReviewRecord.from_dict(row)
            key = (rec.item_id, rec.review_round)
            current[key] = rec
        # Mark superseded: any prior with same key before last is superseded in chain
        # Rebuild: last write wins; mark earlier hashes via superseded flag on record
        latest: dict[str, BlindReviewRecord] = {}
        for (item_id, rnd), rec in current.items():
            if review_round is not None and rnd != review_round:
                continue
            # Prefer round-specific key when filtering
            key = f"{item_id}:r{rnd}"
            latest[key] = rec
        # Filter superseded flag
        return {
            k: v
            for k, v in latest.items()
            if not v.superseded
        }

    def locked_review_for_item(
        self, cohort_id: str, item_id: str, *, review_round: int = 1
    ) -> BlindReviewRecord | None:
        """Latest append-only record for item/round (later revisions supersede earlier)."""
        current = None
        superseded_ids: set[str] = set()
        rows = self._read_jsonl(self.path_for(cohort_id) / "blind_reviews.jsonl")
        for row in rows:
            prior = str(row.get("prior_review_id") or "")
            if prior:
                superseded_ids.add(prior)
        for row in rows:
            # Isolate lookups by cohort_id inside the record
            if str(row.get("cohort_id") or cohort_id) != cohort_id:
                continue
            if row.get("item_id") != item_id:
                continue
            if int(row.get("review_round") or 0) != review_round:
                continue
            rid = str(row.get("review_id") or "")
            if rid in superseded_ids:
                continue
            current = BlindReviewRecord.from_dict(row)
        return current

    def save_blind_review(
        self,
        cohort_id: str,
        record: BlindReviewRecord,
        *,
        allow_same_reviewer_second: bool = False,
    ) -> BlindReviewRecord:
        manifest = self.load_manifest(cohort_id)
        if not manifest.frozen:
            raise FrozenCohortError(
                "Cohort must be frozen before blind review",
                code="cohort_must_be_frozen",
            )
        item = self._item_by_id(cohort_id, record.item_id)
        if item.item_status == "item_unavailable":
            raise BlindRevealError("Cannot review unavailable item")

        if record.review_round >= 2:
            first = self.locked_review_for_item(cohort_id, record.item_id, review_round=1)
            if first is None:
                raise BlindRevealError("Second review requires a locked first review")
            if first.reviewer_id == record.reviewer_id and not allow_same_reviewer_second:
                raise BlindRevealError(
                    "Same reviewer cannot serve as independent second reviewer "
                    "(override with allow_same_reviewer_second=True)"
                )

        # Append-only supersession: new record references prior; old rows untouched
        prior = self.locked_review_for_item(
            cohort_id, record.item_id, review_round=record.review_round
        )
        payload = record.to_dict()
        if prior is not None and not payload.get("prior_review_id"):
            payload["prior_review_id"] = prior.review_id
            payload["supersedes_review_id"] = prior.review_id
        if prior is not None and not (payload.get("revision_reason") or "").strip():
            # Revision of a locked decision requires reason
            if not payload.get("revision_reason"):
                raise BlindRevealError("Revision of a locked blind review requires revision_reason")

        # Post-reveal revision flag enforcement
        if self._candidate_revealed(cohort_id, record.item_id):
            if not payload.get("post_reveal_revision"):
                raise BlindRevealError(
                    "After candidate reveal, revisions require post_reveal_revision=True and reason"
                )
            if not (payload.get("revision_reason") or "").strip():
                raise BlindRevealError("Post-reveal revision requires a reason")

        payload["record_hash"] = ""
        rec = BlindReviewRecord.from_dict(payload).with_hash()
        if not rec.locked:
            raise BlindRevealError("Blind review must be locked on save")
        self._append_jsonl(self.path_for(cohort_id) / "blind_reviews.jsonl", rec.to_dict())
        self._update_item_status(
            cohort_id,
            record.item_id,
            "blind_review_locked"
            if record.review_round == 1
            else "second_review_locked",
        )
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "blind_review_save" if prior is None else "review_revision",
                cohort_id=cohort_id,
                item_id=record.item_id,
                actor_id=record.reviewer_id,
                prior_record_hash=prior.record_hash if prior else "",
                new_record_hash=rec.record_hash,
                details={"review_round": record.review_round, "review_id": rec.review_id},
            ),
        )
        return rec

    def can_reveal_candidate(self, cohort_id: str, item_id: str) -> bool:
        from ionogram_morphology_lab.morphology_review_corpus.constants import (
            REVEAL_STRICT_COHORT,
        )
        from ionogram_morphology_lab.morphology_review_corpus.workflow import (
            normalize_reveal_policy,
            round1_complete,
        )

        rev = self.locked_review_for_item(cohort_id, item_id, review_round=1)
        if rev is None or not rev.locked:
            return False
        proto = self.load_protocol(cohort_id)
        policy = normalize_reveal_policy(proto.reveal_policy)
        if policy == REVEAL_STRICT_COHORT:
            return round1_complete(self, cohort_id)
        return True

    def current_comparison_for_item(
        self, cohort_id: str, item_id: str
    ) -> RevealComparison | None:
        from ionogram_morphology_lab.morphology_review_corpus.current_state import (
            current_comparison_for_item,
        )

        row = current_comparison_for_item(self, cohort_id, item_id)
        return RevealComparison.from_dict(row) if row else None

    def reveal_and_compare(
        self,
        cohort_id: str,
        item_id: str,
        *,
        review_id: str,
        reviewer_note_codes: list[str] | None = None,
        comparison_comment: str = "",
        override_revealed_candidate: bool = False,
        revision_reason: str = "",
        allow_revision: bool = False,
    ) -> RevealComparison:
        """Save a comparison. Idempotent for the same current logical identity.

        Repeated saves with the same review/candidate/agreement payload return
        the existing current record without appending. Material changes require
        ``allow_revision=True`` and a non-empty ``revision_reason``.
        """
        if not self.can_reveal_candidate(cohort_id, item_id):
            raise BlindRevealError(
                "Reveal blocked until blind review is locked "
                "(strict cohort blinding requires full round-one completion)"
            )
        rev = self.locked_review_for_item(cohort_id, item_id, review_round=1)
        assert rev is not None
        if rev.review_id != review_id:
            raise BlindRevealError("review_id does not match locked blind review")
        if override_revealed_candidate and not (comparison_comment or "").strip():
            raise BlindRevealError("Override of revealed candidate requires a comparison comment")
        snap = self.candidate_snapshot_for_item(cohort_id, item_id)
        cand_state = snap.candidate_state if snap else ""
        cand_hash = ""
        if snap is not None:
            cand_hash = str(getattr(snap, "result_hash", "") or "")
        status = comparison_status(
            human_morphology=rev.morphology,
            human_assessability=rev.assessability,
            candidate_state=cand_state or None,
            candidate_assessability=snap.assessability_state if snap else None,
            candidate_available=snap is not None,
        )
        notes = list(reviewer_note_codes or [])
        comment = (comparison_comment or "").strip()

        existing = self.current_comparison_for_item(cohort_id, item_id)
        if existing is not None:
            same = (
                existing.review_id == review_id
                and existing.human_morphology == rev.morphology
                and existing.candidate_state == cand_state
                and existing.agreement_status == status
                and list(existing.reviewer_note_codes or []) == notes
                and (existing.comparison_comment or "").strip() == comment
            )
            if same:
                # Idempotent: no new append-only row.
                return existing
            if not allow_revision:
                raise BlindRevealError(
                    "Comparison already saved for this item; "
                    "create a corrected comparison revision with a reason"
                )
            if not (revision_reason or "").strip():
                raise BlindRevealError(
                    "Corrected comparison revision requires revision_reason"
                )

        from uuid import uuid4

        cmp = RevealComparison(
            comparison_id=str(uuid4()),
            cohort_id=cohort_id,
            item_id=item_id,
            review_id=review_id,
            human_morphology=rev.morphology,
            candidate_state=cand_state,
            candidate_strength=snap.ordinal_strength if snap else "",
            agreement_status=status,
            reviewer_note_codes=notes,
            comparison_comment=comment,
            prior_comparison_id=existing.comparison_id if existing else "",
            supersedes_comparison_id=existing.comparison_id if existing else "",
            revision_reason=(revision_reason or "").strip() if existing else "",
            candidate_result_hash=cand_hash,
        ).with_hash()
        self._append_jsonl(
            self.path_for(cohort_id) / "reveal_comparisons.jsonl", cmp.to_dict()
        )
        self._update_item_status(cohort_id, item_id, "comparison_recorded")
        if existing is None:
            self.append_audit(
                cohort_id,
                AuditEvent.create(
                    "candidate_reveal",
                    cohort_id=cohort_id,
                    item_id=item_id,
                    new_record_hash=cmp.record_hash,
                    details={"agreement_status": status},
                ),
            )
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "comparison_save" if existing is None else "comparison_revision",
                cohort_id=cohort_id,
                item_id=item_id,
                prior_record_hash=existing.record_hash if existing else "",
                new_record_hash=cmp.record_hash,
                details={"agreement_status": status, "revision_reason": cmp.revision_reason},
            ),
        )
        return cmp

    def save_post_comparison_note(
        self,
        cohort_id: str,
        item_id: str,
        *,
        note: str,
    ) -> RevealComparison:
        """Append an optional post-comparison note without changing comparison class.

        Requires an existing current comparison. Uses a corrected revision so
        history stays append-only; current comparison count is unchanged.
        """
        existing = self.current_comparison_for_item(cohort_id, item_id)
        if existing is None:
            raise BlindRevealError(
                "Post-comparison note requires an existing derived comparison"
            )
        rev = self.locked_review_for_item(cohort_id, item_id, review_round=1)
        if rev is None:
            raise BlindRevealError("Locked blind review missing for post-comparison note")
        text = (note or "").strip()
        if (existing.comparison_comment or "").strip() == text:
            return existing
        return self.reveal_and_compare(
            cohort_id,
            item_id,
            review_id=rev.review_id,
            reviewer_note_codes=list(existing.reviewer_note_codes or []),
            comparison_comment=text,
            allow_revision=True,
            revision_reason="optional_post_comparison_note",
        )

    def save_adjudication(
        self, cohort_id: str, record: AdjudicationRecord
    ) -> AdjudicationRecord:
        r1 = self.locked_review_for_item(cohort_id, record.item_id, review_round=1)
        r2 = self.locked_review_for_item(cohort_id, record.item_id, review_round=2)
        if r1 is None or r2 is None:
            raise BlindRevealError("Adjudication requires two locked independent reviews")
        expected = {r1.review_id, r2.review_id}
        if set(record.input_review_ids) != expected:
            raise BlindRevealError("Adjudication input_review_ids must match locked reviews")
        if r1.reviewer_id == r2.reviewer_id:
            raise BlindRevealError(
                "Cannot adjudicate when both reviews are from the same reviewer"
            )
        rec = record if record.record_hash else record.with_hash()
        self._append_jsonl(self.path_for(cohort_id) / "adjudications.jsonl", rec.to_dict())
        self._update_item_status(cohort_id, record.item_id, "adjudication_locked")
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "adjudication",
                cohort_id=cohort_id,
                item_id=record.item_id,
                actor_id=record.adjudicator_id,
                new_record_hash=rec.record_hash,
            ),
        )
        return rec

    def candidate_snapshot_for_item(
        self, cohort_id: str, item_id: str
    ) -> CandidateSnapshot | None:
        last = None
        for row in self._read_jsonl(
            self.path_for(cohort_id) / "candidate_snapshots.jsonl"
        ):
            if row.get("item_id") == item_id:
                last = CandidateSnapshot.from_dict(row)
        return last

    def append_candidate_snapshot(
        self, cohort_id: str, snap: CandidateSnapshot
    ) -> CandidateSnapshot:
        manifest = self.load_manifest(cohort_id)
        existing = self.candidate_snapshot_for_item(cohort_id, snap.item_id)
        if existing is not None:
            if (
                existing.ruleset_hash != snap.ruleset_hash
                or existing.candidate_engine_version != snap.candidate_engine_version
            ):
                raise FrozenCohortError(
                    "Cannot overwrite candidate snapshot under a different ruleset/engine"
                )
            # identical reuse — do not append duplicate
            if existing.result_hash == snap.result_hash:
                return existing
            raise FrozenCohortError(
                "Candidate snapshot already frozen for this item; create a new cohort"
            )
        item = self._item_by_id(cohort_id, snap.item_id)
        if item.source_sha256.lower() != snap.source_sha256.lower() or int(
            item.frame_index
        ) != int(snap.frame_index):
            raise BlindRevealError("Candidate snapshot source/frame mismatch")
        if snap.candidate_engine_version != manifest.candidate_engine_version:
            raise FrozenCohortError("Candidate engine version mismatch for cohort freeze")
        rec = snap.with_hash()
        self._append_jsonl(
            self.path_for(cohort_id) / "candidate_snapshots.jsonl", rec.to_dict()
        )
        return rec

    def second_review_visibility(
        self, cohort_id: str, item_id: str, *, viewer_round: int
    ) -> dict[str, Any]:
        """What a second reviewer may see — never first decision or candidate."""
        payload = {
            "item_id": item_id,
            "first_review_visible": False,
            "candidate_visible": False,
            "agreement_visible": False,
            "adjudication_notes_visible": False,
        }
        if viewer_round >= 2:
            # Still blind to first review and candidate until both locked (for agreement UI)
            r1 = self.locked_review_for_item(cohort_id, item_id, review_round=1)
            r2 = self.locked_review_for_item(cohort_id, item_id, review_round=2)
            if r1 and r2:
                payload["agreement_visible"] = True
                payload["first_review_visible"] = True  # only after both locked
        return payload

    # --------------------------------------------------------------- audit
    def append_audit(self, cohort_id: str, event: AuditEvent) -> None:
        self._append_jsonl(self.path_for(cohort_id) / "audit_log.jsonl", event.to_dict())

    def load_audit(self, cohort_id: str) -> list[dict[str, Any]]:
        return self._read_jsonl(self.path_for(cohort_id) / "audit_log.jsonl")

    # ------------------------------------------------------------- helpers
    def _candidate_revealed(self, cohort_id: str, item_id: str) -> bool:
        for row in self._read_jsonl(
            self.path_for(cohort_id) / "reveal_comparisons.jsonl"
        ):
            if row.get("item_id") == item_id:
                return True
        return False

    def _update_item_status(self, cohort_id: str, item_id: str, status: str) -> None:
        items = self.load_items(cohort_id)
        out = []
        for it in items:
            d = it.to_dict()
            if it.item_id == item_id:
                d["item_status"] = status
            out.append(d)
        self._rewrite_jsonl(self.path_for(cohort_id) / "items.jsonl", out)

    def _item_by_id(self, cohort_id: str, item_id: str) -> ReviewItem:
        for it in self.load_items(cohort_id):
            if it.item_id == item_id:
                return it
        raise KeyError(f"Unknown item_id: {item_id}")

    def _normalize_item(
        self, cohort_id: str, row: dict[str, Any], *, position: int
    ) -> ReviewItem:
        sha = str(row.get("source_sha256") or "").lower()
        status = str(row.get("item_status") or "item_pending")
        unavailable_reason = str(row.get("unavailable_reason") or "")
        try:
            if sha:
                validate_sha256(sha)
        except ValueError:
            status = "item_unavailable"
            unavailable_reason = unavailable_reason or "invalid_source_sha256"
        item_id = str(
            row.get("item_id")
            or f"item_{position:04d}_{(sha[:8] if sha else 'nosha')}_{row.get('frame_index', 0)}"
        )
        return ReviewItem(
            cohort_id=cohort_id,
            item_id=item_id,
            source_inventory_id=str(row.get("source_inventory_id") or ""),
            source_display_name=str(row.get("source_display_name") or ""),
            source_sha256=sha,
            frame_index=int(row.get("frame_index") if row.get("frame_index") is not None else 0),
            frame_time=str(row.get("frame_time") or ""),
            datetime_metadata=str(row.get("datetime_metadata") or ""),
            feature_version=str(row.get("feature_version") or ""),
            diagnostics_cache_id=str(row.get("diagnostics_cache_id") or ""),
            v2_result_hash=str(row.get("v2_result_hash") or ""),
            v2_quality_status=str(row.get("v2_quality_status") or ""),
            candidate_result_hash=str(row.get("candidate_result_hash") or ""),
            candidate_engine_version=str(
                row.get("candidate_engine_version") or CANDIDATE_ENGINE_VERSION
            ),
            ruleset_id=str(row.get("ruleset_id") or "iml-morph-candidate-rules"),
            ruleset_hash=str(row.get("ruleset_hash") or ""),
            evidence_ledger_hash=str(row.get("evidence_ledger_hash") or ""),
            rendering_snapshot=dict(row.get("rendering_snapshot") or {}),
            item_status=status,
            inclusion_reason=str(row.get("inclusion_reason") or ""),
            sampling_stratum=str(row.get("sampling_stratum") or ""),
            manifest_position=position,
            partition=str(row.get("partition") or "pilot_review"),
            unavailable_reason=unavailable_reason,
            grouping=dict(row.get("grouping") or {}),
            parent_item_id=str(row.get("parent_item_id") or ""),
        )

    # ------------------------------------------------------------- comments
    def save_comment(self, cohort_id: str, comment) -> Any:
        from ionogram_morphology_lab.morphology_review_corpus.comments import CommentRecord

        if not isinstance(comment, CommentRecord):
            raise TypeError("comment must be CommentRecord")
        if comment.cohort_id != cohort_id:
            raise ValueError("comment.cohort_id mismatch")
        # Ensure item exists
        self._item_by_id(cohort_id, comment.item_id)
        path = self.path_for(cohort_id) / "comments.jsonl"
        if not path.exists():
            path.write_text("", encoding="utf-8")
        rec = comment.with_hash()
        self._append_jsonl(path, rec.to_dict())
        self.append_audit(
            cohort_id,
            AuditEvent.create(
                "comment_save",
                cohort_id=cohort_id,
                item_id=rec.item_id,
                actor_id=rec.reviewer_id,
                new_record_hash=rec.record_hash,
                details={
                    "comment_id": rec.comment_id,
                    "comment_type": rec.comment_type,
                },
            ),
        )
        return rec

    def load_comments(
        self, cohort_id: str, *, item_id: str | None = None, comment_type: str | None = None
    ) -> list[Any]:
        from ionogram_morphology_lab.morphology_review_corpus.comments import CommentRecord

        path = self.path_for(cohort_id) / "comments.jsonl"
        if not path.exists():
            return []
        out = []
        superseded: set[str] = set()
        rows = self._read_jsonl(path)
        for row in rows:
            sid = str(row.get("supersedes_comment_id") or "")
            if sid:
                superseded.add(sid)
        for row in rows:
            if str(row.get("cohort_id") or "") != cohort_id:
                continue
            if item_id and row.get("item_id") != item_id:
                continue
            if comment_type and row.get("comment_type") != comment_type:
                continue
            if str(row.get("comment_id") or "") in superseded:
                continue
            out.append(CommentRecord.from_dict(row))
        return out

    @staticmethod
    def _check_cohort_id(cohort_id: str) -> None:
        if not _COHORT_ID_RE.match(cohort_id or ""):
            raise ValueError(f"Invalid cohort_id: {cohort_id!r}")

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        assert_no_absolute_paths(data)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
        assert_no_absolute_paths(row)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _rewrite_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            assert_no_absolute_paths(row)
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.is_file() or path.stat().st_size == 0:
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows


def required_fields_complete(payload: dict[str, Any]) -> bool:
    morphology = str(payload.get("morphology") or "")
    if not morphology:
        return False
    for key in ("assessability", "ambiguity", "confidence"):
        if not payload.get(key):
            return False
    if payload.get("interference") is None:
        return False
    if rationale_required(
        morphology=morphology,
        interference_flags=list(payload.get("interference") or []),
        is_revision=bool(payload.get("prior_review_id")),
        is_post_reveal_revision=bool(payload.get("post_reveal_revision")),
        override_revealed_candidate=bool(payload.get("override_revealed_candidate")),
    ) and not str(payload.get("rationale") or "").strip():
        return False
    return True
