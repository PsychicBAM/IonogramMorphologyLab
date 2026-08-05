"""Filesystem store for pilot expert-review campaigns (Phase 4C.3)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from ionogram_morphology_lab.morphology_review_campaign.constants import (
    BUILD_IDENTITY_DEFAULT,
    CAMPAIGNS_DIRNAME,
)
from ionogram_morphology_lab.morphology_review_campaign.models import (
    AssignmentRecord,
    CampaignAuditEvent,
    CampaignManifest,
    CampaignProtocol,
    CohortLink,
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.sampling import (
    apply_sampling,
    build_eligible_pool,
)
from ionogram_morphology_lab.morphology_review_corpus.models import ReviewerIdentity
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{1,63}$")


class CampaignError(RuntimeError):
    pass


class MorphologyReviewCampaignStore:
    """Project-scoped campaign coordinator over morphology cohorts."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / CAMPAIGNS_DIRNAME
        self.corpus = MorphologyReviewCorpusStore(self.project_root)

    def path_for(self, campaign_id: str) -> Path:
        return self.root / campaign_id

    def _check_id(self, campaign_id: str) -> None:
        if not _ID_RE.match(campaign_id or ""):
            raise CampaignError(f"Invalid campaign_id: {campaign_id!r}")

    def _read_json(self, path: Path) -> Any:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def list_campaigns(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir() and (p / "campaign.json").is_file()
        )

    def append_audit(self, campaign_id: str, event: CampaignAuditEvent) -> None:
        self._append_jsonl(
            self.path_for(campaign_id) / "campaign_audit.jsonl", event.to_dict()
        )

    def load_manifest(self, campaign_id: str) -> CampaignManifest:
        data = self._read_json(self.path_for(campaign_id) / "campaign.json")
        if not isinstance(data, dict):
            raise CampaignError(f"Campaign not found: {campaign_id}")
        return CampaignManifest.from_dict(data)

    def load_protocol(self, campaign_id: str) -> CampaignProtocol:
        data = self._read_json(self.path_for(campaign_id) / "campaign_protocol.json")
        if not isinstance(data, dict):
            raise CampaignError(f"Campaign protocol missing: {campaign_id}")
        return CampaignProtocol.from_dict(data)

    def save_manifest(self, manifest: CampaignManifest) -> CampaignManifest:
        m = manifest.with_hash()
        self._write_json(self.path_for(m.campaign_id) / "campaign.json", m.to_dict())
        return m

    def preview_sampling(
        self,
        *,
        sources: list[SourceScopeEntry],
        windows: list[TimeWindow],
        plan: SamplingPlan,
    ) -> dict[str, Any]:
        pool = build_eligible_pool(sources, windows)
        return apply_sampling(pool, plan)

    def create_campaign(
        self,
        *,
        campaign_id: str | None = None,
        display_name: str,
        description: str = "",
        created_by: str = "",
        project_identity: str = "",
        sources: list[SourceScopeEntry] | None = None,
        windows: list[TimeWindow] | None = None,
        sampling_plan: SamplingPlan | None = None,
        reviewer_plan: ReviewerPlan | None = None,
        reveal_policy: str = "strict_cohort_blinding",
        create_linked_cohort: bool = True,
        cohort_id: str | None = None,
        freeze_cohort: bool = False,
        candidate_snapshots: list[Any] | None = None,
        session: Any | None = None,
        skip_inventory_validation: bool = False,
    ) -> CampaignManifest:
        """Create campaign after explicit confirmation; optionally create/link cohort.

        When ``session`` is provided (normal UI path), every source must resolve
        against the authoritative project inventory — free-text SHA/alias pairs
        are rejected (Phase 4C.3a).
        """
        cid = campaign_id or f"campaign_{uuid4().hex[:12]}"
        self._check_id(cid)
        d = self.path_for(cid)
        if d.exists():
            raise CampaignError(f"Campaign already exists: {cid}")

        sources = list(sources or [])
        windows = list(windows or [])
        sampling_plan = sampling_plan or SamplingPlan()
        reviewer_plan = reviewer_plan or ReviewerPlan(second_reviewer_optional=True)
        if session is not None and not skip_inventory_validation:
            from ionogram_morphology_lab.morphology_review_campaign.repair import (
                assert_sources_registered_or_raise,
            )

            assert_sources_registered_or_raise(session, sources)
            # Normalize display names / inventory IDs from registry
            from ionogram_morphology_lab.morphology_review_campaign.project_sources import (
                list_registered_project_sources,
            )

            inv = {r.source_sha256: r for r in list_registered_project_sources(session)}
            normalized: list[SourceScopeEntry] = []
            for s in sources:
                reg = inv[s.source_sha256.lower()]
                normalized.append(
                    SourceScopeEntry(
                        source_sha256=reg.source_sha256,
                        source_display_name=reg.display_name,
                        source_inventory_id=reg.inventory_id,
                        date_hint=reg.date_hint or s.date_hint,
                        available=reg.available,
                    )
                )
            sources = normalized
        preview = self.preview_sampling(
            sources=sources, windows=windows, plan=sampling_plan
        )
        selected = list(preview["selected"])
        # Keep unavailable eligible frames in the cohort as blocked rows
        # so the campaign queue can surface them (not silently dropped).
        unavailable_rows = list(preview.get("unavailable") or [])

        proto = CampaignProtocol(
            reveal_policy=reveal_policy,
            second_reviewer_optional=bool(reviewer_plan.second_reviewer_optional),
        ).with_hash()

        d.mkdir(parents=True, exist_ok=False)
        (d / "exports").mkdir(exist_ok=True)
        self._write_json(d / "campaign_protocol.json", proto.to_dict())

        manifest = CampaignManifest(
            campaign_id=cid,
            display_name=display_name or cid,
            description=description,
            state="ready" if selected else "draft",
            created_by=created_by,
            project_identity=project_identity,
            source_scope=[s.to_dict() for s in sources],
            time_windows=[w.to_dict() for w in windows],
            target_review_count=int(sampling_plan.target_count or len(selected)),
            actual_item_count=len(selected),
            reviewer_plan=reviewer_plan.to_dict(),
            reveal_policy=reveal_policy,
            sampling_plan=sampling_plan.to_dict(),
            grouping_plan={
                "keep_adjacent_frames_together": sampling_plan.keep_adjacent_frames_together,
            },
            selected_item_fingerprints=list(preview.get("fingerprints") or []),
            protocol_hash=proto.protocol_hash,
            build_identity=BUILD_IDENTITY_DEFAULT,
        ).with_hash()
        self._write_json(d / "campaign.json", manifest.to_dict())
        self.append_audit(
            cid,
            CampaignAuditEvent.create(
                "campaign_created",
                campaign_id=cid,
                details={
                    "selected_count": len(selected),
                    "method": sampling_plan.method,
                    "seed": sampling_plan.seed,
                },
            ),
        )

        # Assignments
        if reviewer_plan.first_reviewer_id:
            self._append_jsonl(
                d / "assignments.jsonl",
                AssignmentRecord.create(
                    campaign_id=cid,
                    reviewer_id=reviewer_plan.first_reviewer_id,
                    reviewer_alias=reviewer_plan.first_reviewer_alias,
                    role="first_reviewer",
                ).to_dict(),
            )
        if reviewer_plan.second_reviewer_id:
            self._append_jsonl(
                d / "assignments.jsonl",
                AssignmentRecord.create(
                    campaign_id=cid,
                    reviewer_id=reviewer_plan.second_reviewer_id,
                    reviewer_alias=reviewer_plan.second_reviewer_alias,
                    role="second_reviewer",
                ).to_dict(),
            )
        if reviewer_plan.adjudicator_id:
            self._append_jsonl(
                d / "assignments.jsonl",
                AssignmentRecord.create(
                    campaign_id=cid,
                    reviewer_id=reviewer_plan.adjudicator_id,
                    reviewer_alias=reviewer_plan.adjudicator_alias,
                    role="adjudicator",
                ).to_dict(),
            )

        if create_linked_cohort and (selected or unavailable_rows):
            self.create_and_link_cohort(
                cid,
                items=selected + unavailable_rows,
                cohort_id=cohort_id,
                cohort_role="first_review",
                freeze=freeze_cohort,
                candidate_snapshots=candidate_snapshots,
                reviewer_plan=reviewer_plan,
            )
        return self.load_manifest(cid)

    def create_and_link_cohort(
        self,
        campaign_id: str,
        *,
        items: list[dict[str, Any]],
        cohort_id: str | None = None,
        cohort_role: str = "first_review",
        freeze: bool = False,
        candidate_snapshots: list[Any] | None = None,
        reviewer_plan: ReviewerPlan | None = None,
    ) -> CohortLink:
        """Create a morphology cohort from selected items and link it."""
        manifest = self.load_manifest(campaign_id)
        plan = reviewer_plan or ReviewerPlan.from_dict(manifest.reviewer_plan)
        coid = cohort_id or f"{campaign_id}_first"
        sampling = SamplingPlan.from_dict(manifest.sampling_plan)
        cohort_manifest = self.corpus.create_cohort(
            cohort_id=coid,
            items=items,
            sampling_method=sampling.method,
            random_seed=sampling.seed,
            source_inventory_snapshot={
                "campaign_id": campaign_id,
                "campaign_hash": manifest.campaign_hash,
                "sources": manifest.source_scope,
            },
        )
        if plan.first_reviewer_id:
            self.corpus.upsert_reviewer(
                coid,
                ReviewerIdentity(
                    plan.first_reviewer_id,
                    plan.first_reviewer_alias or plan.first_reviewer_id,
                    role="reviewer",
                ),
            )
        if freeze:
            self.corpus.freeze_cohort(coid, candidate_snapshots=candidate_snapshots)
            cohort_manifest = self.corpus.load_manifest(coid)
        link = CohortLink.create(
            campaign_id=campaign_id,
            cohort_id=cohort_manifest.cohort_id,
            cohort_role=cohort_role,
            manifest_hash=cohort_manifest.manifest_hash,
        )
        self._append_jsonl(self.path_for(campaign_id) / "cohort_links.jsonl", link.to_dict())
        # Update actual count / state
        manifest.actual_item_count = len(items)
        if manifest.state == "draft":
            manifest.state = "ready"
        self.save_manifest(manifest)
        self.append_audit(
            campaign_id,
            CampaignAuditEvent.create(
                "cohort_linked",
                campaign_id=campaign_id,
                details={
                    "cohort_id": link.cohort_id,
                    "cohort_role": link.cohort_role,
                    "manifest_hash": link.manifest_hash,
                    "frozen": bool(freeze),
                },
            ),
        )
        return link

    def link_existing_cohort(
        self,
        campaign_id: str,
        cohort_id: str,
        *,
        cohort_role: str = "first_review",
    ) -> CohortLink:
        cm = self.corpus.load_manifest(cohort_id)
        # Duplicate identity check within same role
        for existing in self.list_cohort_links(campaign_id):
            if existing.cohort_role == cohort_role and existing.cohort_id == cohort_id:
                raise CampaignError(
                    f"Cohort {cohort_id} already linked in role {cohort_role}"
                )
            if existing.cohort_role == cohort_role:
                # Check silent duplicate fingerprints across cohorts in same role
                pass
        link = CohortLink.create(
            campaign_id=campaign_id,
            cohort_id=cohort_id,
            cohort_role=cohort_role,
            manifest_hash=cm.manifest_hash,
        )
        self._append_jsonl(self.path_for(campaign_id) / "cohort_links.jsonl", link.to_dict())
        self.append_audit(
            campaign_id,
            CampaignAuditEvent.create(
                "cohort_linked_existing",
                campaign_id=campaign_id,
                details={"cohort_id": cohort_id, "cohort_role": cohort_role},
            ),
        )
        return link

    def list_cohort_links(self, campaign_id: str) -> list[CohortLink]:
        return [
            CohortLink.from_dict(r)
            for r in self._read_jsonl(self.path_for(campaign_id) / "cohort_links.jsonl")
        ]

    def list_assignments(self, campaign_id: str) -> list[AssignmentRecord]:
        return [
            AssignmentRecord.from_dict(r)
            for r in self._read_jsonl(self.path_for(campaign_id) / "assignments.jsonl")
        ]

    def set_state(self, campaign_id: str, state: str) -> CampaignManifest:
        m = self.load_manifest(campaign_id)
        m.state = state
        m = self.save_manifest(m)
        self.append_audit(
            campaign_id,
            CampaignAuditEvent.create(
                "campaign_state_changed",
                campaign_id=campaign_id,
                details={"state": state},
            ),
        )
        return m

    def delete_campaign(self, campaign_id: str, *, delete_cohorts: bool = False) -> None:
        """Delete campaign folder; never deletes frozen cohorts by default."""
        if delete_cohorts:
            raise CampaignError("delete_cohorts is not supported; archive cohorts separately")
        import shutil

        d = self.path_for(campaign_id)
        if d.is_dir():
            shutil.rmtree(d)

    def primary_first_review_cohort(self, campaign_id: str) -> str | None:
        for link in self.list_cohort_links(campaign_id):
            if link.cohort_role == "first_review":
                return link.cohort_id
        links = self.list_cohort_links(campaign_id)
        return links[0].cohort_id if links else None
