"""Project-local store for immutable disagreement analysis runs."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ionogram_morphology_lab.morphology_disagreement_analysis.analytics import (
    descriptive_dashboard,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.constants import (
    ANALYSES_DIRNAME,
    ANALYSIS_PROTOCOL_VERSION,
    LIFECYCLE_STATES,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.contamination import (
    mark_development_exposed,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.decision_gate import (
    build_decision_record,
    validate_decision_record,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.eligibility import (
    check_version_compatibility,
    resolve_cohort_items,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.holdout import (
    build_holdout_plan,
    validate_holdout_plan,
)
from ionogram_morphology_lab.morphology_disagreement_analysis.models import (
    AnalysisManifest,
    AnalysisSelection,
    AnalystHypothesis,
    ContaminationRecord,
    DecisionGateRecord,
    HoldoutPlan,
    SnapshotItemRecord,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    is_absolute_local_path,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisStoreError(RuntimeError):
    pass


class MorphologyDisagreementAnalysisStore:
    """Append-only / immutable-snapshot analysis store under project root."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / ANALYSES_DIRNAME
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, analysis_id: str) -> Path:
        return self.root / analysis_id

    def list_analyses(self) -> list[AnalysisManifest]:
        out: list[AnalysisManifest] = []
        if not self.root.exists():
            return out
        for d in sorted(self.root.iterdir()):
            if not d.is_dir():
                continue
            mp = d / "analysis_manifest.json"
            if mp.exists():
                out.append(self.load_manifest(d.name))
        return out

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
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

    def load_manifest(self, analysis_id: str) -> AnalysisManifest:
        return AnalysisManifest.from_dict(
            self._read_json(self.path_for(analysis_id) / "analysis_manifest.json")
        )

    def _save_manifest(self, manifest: AnalysisManifest) -> None:
        manifest.manifest_hash = manifest.compute_manifest_hash()
        self._write_json(
            self.path_for(manifest.analysis_id) / "analysis_manifest.json",
            manifest.to_dict(),
        )

    def load_snapshot_rows(self, analysis_id: str) -> list[SnapshotItemRecord]:
        rows = self._read_jsonl(self.path_for(analysis_id) / "analysis_snapshot.jsonl")
        return [SnapshotItemRecord.from_dict(r) for r in rows]

    def create_draft(
        self,
        *,
        title: str,
        description: str,
        cohort_ids: list[str],
        campaign_ids: list[str] | None = None,
        analyst_id: str = "",
        parent_analysis_id: str = "",
        revision_reason: str = "",
    ) -> AnalysisManifest:
        aid = f"analysis_{uuid4().hex[:12]}"
        d = self.path_for(aid)
        d.mkdir(parents=True, exist_ok=True)
        rev = 1
        if parent_analysis_id:
            try:
                parent = self.load_manifest(parent_analysis_id)
                rev = int(parent.revision_number) + 1
            except Exception:
                rev = 1
        manifest = AnalysisManifest(
            analysis_id=aid,
            title=title,
            description=description,
            created_at=_utc_now(),
            analysis_protocol_version=ANALYSIS_PROTOCOL_VERSION,
            lifecycle_state="draft",
            selection=AnalysisSelection(
                cohort_ids=list(cohort_ids),
                campaign_ids=list(campaign_ids or []),
            ),
            selected_cohort_ids=list(cohort_ids),
            selected_campaign_ids=list(campaign_ids or []),
            parent_analysis_id=parent_analysis_id,
            revision_number=rev,
            revision_reason=revision_reason,
            analyst_id=analyst_id,
        )
        self._save_manifest(manifest)
        return manifest

    def preview(
        self,
        corpus_store: MorphologyReviewCorpusStore,
        cohort_ids: list[str],
        *,
        campaign_id_by_cohort: dict[str, str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        all_rows: list[SnapshotItemRecord] = []
        excl: dict[str, int] = {}
        warnings: list[str] = []
        cohort_revisions: dict[str, int] = {}
        cmap = campaign_id_by_cohort or {}
        total = max(len(cohort_ids), 1)
        for i, cid in enumerate(cohort_ids):
            if cancel_cb and cancel_cb():
                raise AnalysisStoreError("cancelled")
            if progress_cb:
                progress_cb(int(100 * i / total), f"Resolving {cid}")
            rows, buckets, warns = resolve_cohort_items(
                corpus_store,
                cid,
                campaign_id=cmap.get(cid, ""),
                require_revealed=True,
            )
            all_rows.extend(rows)
            for k, v in buckets.items():
                excl[k] = excl.get(k, 0) + v
            warnings.extend(warns)
            if rows:
                cohort_revisions[cid] = rows[0].cohort_revision_number
            else:
                try:
                    m = corpus_store.load_manifest(cid)
                    cohort_revisions[cid] = int(getattr(m, "revision_number", 1) or 1)
                except Exception:
                    cohort_revisions[cid] = 0
        compat = check_version_compatibility(all_rows)
        dash = descriptive_dashboard(all_rows, exclusion_counts=excl)
        if progress_cb:
            progress_cb(100, "Preview ready")
        return {
            "rows": all_rows,
            "exclusion_counts": excl,
            "warnings": warnings,
            "cohort_revisions": cohort_revisions,
            "compatibility": compat,
            "dashboard": dash,
        }

    def freeze_snapshot(
        self,
        analysis_id: str,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        campaign_id_by_cohort: dict[str, str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> AnalysisManifest:
        manifest = self.load_manifest(analysis_id)
        if manifest.lifecycle_state not in ("draft",):
            raise AnalysisStoreError(
                f"Cannot freeze analysis in state {manifest.lifecycle_state!r}"
            )
        preview = self.preview(
            corpus_store,
            manifest.selected_cohort_ids,
            campaign_id_by_cohort=campaign_id_by_cohort,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )
        rows: list[SnapshotItemRecord] = preview["rows"]
        if not rows and "blind_not_revealed" in str(preview.get("warnings")):
            raise AnalysisStoreError(
                "Selected corpora are blind or incomplete; candidate leakage forbidden."
            )
        if any("blind_incomplete" in w or "blind_not_revealed" in w for w in preview["warnings"]):
            # Fail closed if all items rejected as blind
            if not any(r.comparison_id for r in rows):
                raise AnalysisStoreError(
                    "Cannot freeze analysis from still-blind corpora."
                )

        contam = mark_development_exposed(rows, analysis_id=analysis_id)
        snap_path = self.path_for(analysis_id) / "analysis_snapshot.jsonl"
        if snap_path.exists():
            snap_path.unlink()
        for r in rows:
            self._append_jsonl(snap_path, r.to_dict())

        contam_path = self.path_for(analysis_id) / "contamination.jsonl"
        if contam_path.exists():
            contam_path.unlink()
        for c in contam:
            self._append_jsonl(contam_path, c.to_dict())

        snapshot_hash = deterministic_hash([r.to_dict() for r in rows])
        compat = preview["compatibility"]
        manifest.lifecycle_state = "frozen"
        manifest.frozen_at = _utc_now()
        manifest.cohort_revisions = dict(preview["cohort_revisions"])
        manifest.candidate_engine_versions = list(compat["candidate_engine_versions"])
        manifest.candidate_ruleset_versions = list(compat["candidate_ruleset_versions"])
        manifest.geometry_versions = list(compat["geometry_versions"])
        manifest.version_strata_required = bool(compat["version_strata_required"])
        manifest.compatibility_warnings = list(compat["compatibility_warnings"])
        manifest.snapshot_hash = snapshot_hash
        manifest.contamination_status = "development_exposed"
        self._save_manifest(manifest)

        dash = descriptive_dashboard(rows, exclusion_counts=preview["exclusion_counts"])
        self._write_json(self.path_for(analysis_id) / "analysis_summary.json", dash)
        md = self._summary_markdown(manifest, dash)
        (self.path_for(analysis_id) / "analysis_summary.md").write_text(md, encoding="utf-8")
        self._write_matrix_csv(analysis_id, dash.get("transition_matrix") or {})
        self._write_case_index_csv(analysis_id, rows)
        integrity = self.integrity_report(analysis_id)
        self._write_json(self.path_for(analysis_id) / "integrity_report.json", integrity)
        return self.load_manifest(analysis_id)

    def create_revision(
        self,
        parent_analysis_id: str,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        revision_reason: str,
        title: str | None = None,
        campaign_id_by_cohort: dict[str, str] | None = None,
    ) -> AnalysisManifest:
        parent = self.load_manifest(parent_analysis_id)
        draft = self.create_draft(
            title=title or f"{parent.title} (rev {parent.revision_number + 1})",
            description=parent.description,
            cohort_ids=list(parent.selected_cohort_ids),
            campaign_ids=list(parent.selected_campaign_ids),
            analyst_id=parent.analyst_id,
            parent_analysis_id=parent.analysis_id,
            revision_reason=revision_reason,
        )
        return self.freeze_snapshot(
            draft.analysis_id,
            corpus_store,
            campaign_id_by_cohort=campaign_id_by_cohort,
        )

    def append_hypothesis(self, note: AnalystHypothesis) -> AnalystHypothesis:
        manifest = self.load_manifest(note.analysis_id)
        if manifest.lifecycle_state == "archived":
            raise AnalysisStoreError("Cannot append notes to archived analysis")
        self._append_jsonl(
            self.path_for(note.analysis_id) / "analyst_notes.jsonl", note.to_dict()
        )
        return note

    def load_hypotheses(self, analysis_id: str) -> list[AnalystHypothesis]:
        return [
            AnalystHypothesis.from_dict(r)
            for r in self._read_jsonl(self.path_for(analysis_id) / "analyst_notes.jsonl")
        ]

    def load_contamination(self, analysis_id: str) -> list[ContaminationRecord]:
        return [
            ContaminationRecord.from_dict(r)
            for r in self._read_jsonl(self.path_for(analysis_id) / "contamination.jsonl")
        ]

    def save_holdout_plan(self, plan: HoldoutPlan) -> HoldoutPlan:
        issues = validate_holdout_plan(plan)
        # Persist even with warnings; hard errors still saved but flagged
        self._write_json(
            self.path_for(plan.analysis_id) / "holdout_plan.json", plan.to_dict()
        )
        manifest = self.load_manifest(plan.analysis_id)
        manifest.holdout_plan_id = plan.holdout_plan_id
        self._save_manifest(manifest)
        plan._validation_issues = issues  # type: ignore[attr-defined]
        return plan

    def load_holdout_plan(self, analysis_id: str) -> HoldoutPlan | None:
        p = self.path_for(analysis_id) / "holdout_plan.json"
        if not p.exists():
            return None
        return HoldoutPlan.from_dict(self._read_json(p))

    def record_decision(
        self,
        *,
        analysis_id: str,
        outcome: str,
        analyst_id: str,
        analyst_rationale: str,
        alternative_explanations: list[str] | None = None,
        limitations: list[str] | None = None,
        relevant_strata: list[str] | None = None,
    ) -> DecisionGateRecord:
        manifest = self.load_manifest(analysis_id)
        if manifest.lifecycle_state not in ("frozen", "reviewed", "decision_recorded"):
            raise AnalysisStoreError("Decision gate requires a frozen analysis")
        rows = self.load_snapshot_rows(analysis_id)
        holdout = self.load_holdout_plan(analysis_id)
        record = build_decision_record(
            manifest=manifest,
            rows=rows,
            outcome=outcome,
            analyst_id=analyst_id,
            analyst_rationale=analyst_rationale,
            alternative_explanations=alternative_explanations,
            limitations=limitations,
            relevant_strata=relevant_strata,
            holdout_plan=holdout,
        )
        issues = validate_decision_record(record)
        if issues:
            raise AnalysisStoreError("Decision record incomplete: " + ", ".join(issues))
        self._write_json(
            self.path_for(analysis_id) / "decision_gate.json", record.to_dict()
        )
        md = self._decision_markdown(record)
        (self.path_for(analysis_id) / "decision_gate.md").write_text(md, encoding="utf-8")
        manifest.lifecycle_state = "decision_recorded"
        manifest.decision_outcome = outcome
        self._save_manifest(manifest)
        return record

    def load_decision(self, analysis_id: str) -> DecisionGateRecord | None:
        p = self.path_for(analysis_id) / "decision_gate.json"
        if not p.exists():
            return None
        return DecisionGateRecord.from_dict(self._read_json(p))

    def integrity_report(self, analysis_id: str) -> dict[str, Any]:
        from ionogram_morphology_lab.morphology_disagreement_analysis.integrity import (
            validate_analysis,
        )

        return validate_analysis(self, analysis_id)

    def export_bundle(self, analysis_id: str, dest: Path) -> Path:
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        src = self.path_for(analysis_id)
        for name in (
            "analysis_manifest.json",
            "analysis_snapshot.jsonl",
            "analysis_summary.json",
            "analysis_summary.md",
            "disagreement_matrix.csv",
            "case_index.csv",
            "analyst_notes.jsonl",
            "decision_gate.json",
            "decision_gate.md",
            "integrity_report.json",
            "holdout_plan.json",
            "contamination.jsonl",
        ):
            p = src / name
            if p.exists():
                text = p.read_text(encoding="utf-8")
                (dest / name).write_text(text, encoding="utf-8")
        # Fail closed on absolute paths in exported JSON payloads
        self._assert_no_abs_paths(dest)
        return dest

    def _assert_no_abs_paths(self, folder: Path) -> None:
        for p in folder.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".json", ".jsonl", ".md", ".csv"}:
                continue
            text = p.read_text(encoding="utf-8")
            for line in text.splitlines():
                for token in line.replace(",", " ").replace('"', " ").split():
                    if is_absolute_local_path(token):
                        raise AnalysisStoreError(
                            f"Absolute local path in export {p.name}: {token}"
                        )

    def _write_matrix_csv(self, analysis_id: str, matrix: dict[str, dict[str, int]]) -> None:
        experts = sorted(matrix.keys())
        cands: set[str] = set()
        for row in matrix.values():
            cands.update(row.keys())
        cands_l = sorted(cands)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["expert_label"] + cands_l)
        for h in experts:
            w.writerow([h] + [int(matrix.get(h, {}).get(c, 0)) for c in cands_l])
        (self.path_for(analysis_id) / "disagreement_matrix.csv").write_text(
            buf.getvalue(), encoding="utf-8"
        )

    def _write_case_index_csv(
        self, analysis_id: str, rows: list[SnapshotItemRecord]
    ) -> None:
        buf = io.StringIO()
        fields = [
            "cohort_id",
            "item_id",
            "source_sha256",
            "frame_index",
            "frame_time",
            "expert_morphology",
            "candidate_state",
            "comparison_status",
            "eligibility_bucket",
            "candidate_engine_version",
            "candidate_ruleset_id",
            "related_frame_group",
            "sequence_id",
            "contamination_status",
        ]
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())
        (self.path_for(analysis_id) / "case_index.csv").write_text(
            buf.getvalue(), encoding="utf-8"
        )

    def _summary_markdown(self, manifest: AnalysisManifest, dash: dict[str, Any]) -> str:
        lines = [
            f"# Disagreement analysis: {manifest.title}",
            "",
            f"- Analysis ID: `{manifest.analysis_id}`",
            f"- Protocol: `{manifest.analysis_protocol_version}`",
            f"- Manifest hash: `{manifest.manifest_hash}`",
            f"- Snapshot hash: `{manifest.snapshot_hash}`",
            f"- Lifecycle: `{manifest.lifecycle_state}`",
            f"- Contamination: `{manifest.contamination_status}`",
            "",
            "## Denominators",
            "",
            f"- Selected unique items: {dash.get('selected_unique_items')}",
            f"- Eligible comparable: {dash.get('eligible_comparable_items')}",
            f"- Label matches: {dash.get('exact_label_matches')}",
            f"- Label disagreements: {dash.get('morphology_disagreements')}",
            "",
            "## Notes",
            "",
            dash.get("note_en", ""),
            "",
        ]
        if dash.get("small_sample"):
            lines += ["", f"**{dash.get('small_sample_warning_en')}**", ""]
        return "\n".join(lines) + "\n"

    def _decision_markdown(self, record: DecisionGateRecord) -> str:
        return (
            f"# Decision Gate\n\n"
            f"- Outcome: `{record.outcome}`\n"
            f"- Analysis: `{record.analysis_id}`\n"
            f"- Snapshot hash: `{record.snapshot_hash}`\n"
            f"- Sample size: {record.sample_size}\n"
            f"- Development-exposed: {record.development_exposed}\n"
            f"- Holdout required: {record.holdout_required}\n"
            f"- Holdout plan: `{record.holdout_plan_id}`\n\n"
            f"## Rationale\n\n{record.analyst_rationale}\n"
        )


def propose_holdout_from_rows(
    store: MorphologyDisagreementAnalysisStore,
    *,
    analysis_id: str,
    title: str,
    holdout_case_keys: list[str],
    separation_basis: list[str] | None = None,
) -> HoldoutPlan:
    rows = store.load_snapshot_rows(analysis_id)
    contam = store.load_contamination(analysis_id)
    plan = build_holdout_plan(
        analysis_id=analysis_id,
        title=title,
        all_rows=rows,
        holdout_case_keys=holdout_case_keys,
        contamination_records=contam,
        separation_basis=separation_basis,
    )
    return store.save_holdout_plan(plan)
