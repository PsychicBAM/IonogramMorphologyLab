"""Project-local store for immutable ML dataset readiness audits."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ionogram_morphology_lab.ml_dataset_readiness.constants import (
    NO_CLAIM_STATEMENT_EN,
    NO_CLAIM_STATEMENT_RU,
    READINESS_DIRNAME,
    READINESS_PROTOCOL_VERSION,
)
from ionogram_morphology_lab.ml_dataset_readiness.contracts import (
    contract_descriptor,
    validate_task_contract,
)
from ionogram_morphology_lab.ml_dataset_readiness.coverage import build_coverage_summary
from ionogram_morphology_lab.ml_dataset_readiness.holdout_feasibility import (
    assess_holdout_feasibility,
    collection_gap_plan,
)
from ionogram_morphology_lab.ml_dataset_readiness.integrity import validate_audit_dir
from ionogram_morphology_lab.ml_dataset_readiness.inventory import (
    dedupe_cohort_references,
    load_disagreement_exposure_index,
    project_cohort_inventory,
)
from ionogram_morphology_lab.ml_dataset_readiness.missingness import build_missingness_report
from ionogram_morphology_lab.ml_dataset_readiness.models import (
    HoldoutFeasibilityReport,
    InventoryItemRecord,
    ReadinessGateRecord,
    ReadinessManifest,
    ReadinessSelection,
)
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import (
    build_gate_record,
    validate_gate_record,
)
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    is_absolute_local_path,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReadinessStoreError(RuntimeError):
    pass


class MLDatasetReadinessStore:
    """Immutable readiness-audit store under project review_dataset/ml_readiness."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root)
        self.root = self.project_root / READINESS_DIRNAME
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, audit_id: str) -> Path:
        return self.root / audit_id

    def list_audits(self) -> list[ReadinessManifest]:
        out: list[ReadinessManifest] = []
        if not self.root.exists():
            return out
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and (d / "readiness_manifest.json").exists():
                out.append(self.load_manifest(d.name))
        return out

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        from ionogram_morphology_lab.morphology_review_corpus.hashing import (
            assert_no_absolute_paths,
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            assert_no_absolute_paths(payload)
        except ValueError as exc:
            raise ReadinessStoreError(str(exc)) from exc
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

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

    def load_manifest(self, audit_id: str) -> ReadinessManifest:
        return ReadinessManifest.from_dict(
            self._read_json(self.path_for(audit_id) / "readiness_manifest.json")
        )

    def _save_manifest(self, manifest: ReadinessManifest) -> None:
        manifest.manifest_hash = manifest.compute_manifest_hash()
        self._write_json(
            self.path_for(manifest.audit_id) / "readiness_manifest.json",
            manifest.to_dict(),
        )

    def load_inventory(self, audit_id: str) -> list[InventoryItemRecord]:
        rows = self._read_jsonl(self.path_for(audit_id) / "label_inventory.jsonl")
        return [InventoryItemRecord.from_dict(r) for r in rows]

    def create_draft(
        self,
        *,
        title: str,
        description: str,
        task_contract: str,
        cohort_ids: list[str],
        campaign_ids: list[str] | None = None,
        analyst_id: str = "",
        parent_audit_id: str = "",
        revision_reason: str = "",
    ) -> ReadinessManifest:
        validate_task_contract(task_contract)
        unique, _acct = dedupe_cohort_references(cohort_ids)
        aid = f"readiness_{uuid4().hex[:12]}"
        self.path_for(aid).mkdir(parents=True, exist_ok=True)
        rev = 1
        if parent_audit_id:
            try:
                parent = self.load_manifest(parent_audit_id)
                rev = int(parent.revision_number) + 1
            except Exception:
                rev = 1
        desc = contract_descriptor(task_contract)
        manifest = ReadinessManifest(
            audit_id=aid,
            title=title,
            description=description,
            created_at=_utc_now(),
            task_contract=task_contract,
            audit_protocol_version=READINESS_PROTOCOL_VERSION,
            lifecycle_state="draft",
            selection=ReadinessSelection(
                cohort_ids=list(unique),
                campaign_ids=list(campaign_ids or []),
            ),
            selected_cohort_ids=list(unique),
            selected_campaign_ids=list(campaign_ids or []),
            parent_audit_id=parent_audit_id,
            revision_number=rev,
            revision_reason=revision_reason,
            analyst_id=analyst_id,
            parameter_scaling_supported=bool(desc.get("supports_parameter_scaling")),
            contract_status_note=str(desc.get("parameter_scaling_status_en") or ""),
        )
        self._save_manifest(manifest)
        return manifest

    def preview(
        self,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        task_contract: str,
        cohort_ids: list[str],
        campaign_id_by_cohort: dict[str, str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        validate_task_contract(task_contract)
        unique, dedupe_acct = dedupe_cohort_references(cohort_ids)
        exposure = load_disagreement_exposure_index(self.project_root)
        all_rows: list[InventoryItemRecord] = []
        accounting: dict[str, int] = dict(dedupe_acct)
        warnings: list[str] = []
        revisions: dict[str, int] = {}
        cmap = campaign_id_by_cohort or {}
        total = max(len(unique), 1)
        for i, cid in enumerate(unique):
            if cancel_cb and cancel_cb():
                raise ReadinessStoreError("cancelled")
            if progress_cb:
                # Reserve 100% for freeze/write completion; projection tops out at 90.
                progress_cb(min(90, int(90 * i / total)), f"Projecting {cid}")
            rows, acct, warns = project_cohort_inventory(
                corpus_store,
                cid,
                task_contract=task_contract,
                campaign_id=cmap.get(cid, ""),
                project_id=self.project_root.name,
                exposure=exposure,
            )
            all_rows.extend(rows)
            for k, v in acct.items():
                accounting[k] = accounting.get(k, 0) + int(v)
            warnings.extend(warns)
            if rows:
                revisions[cid] = rows[0].cohort_revision
            if progress_cb:
                progress_cb(min(90, int(90 * (i + 1) / total)), f"Projected {cid}")
        coverage = build_coverage_summary(all_rows, task_contract=task_contract)
        missingness = build_missingness_report(all_rows, task_contract=task_contract)
        return {
            "rows": all_rows,
            "accounting": accounting,
            "warnings": warnings,
            "cohort_revisions": revisions,
            "coverage": coverage,
            "missingness": missingness,
            "task_contract": task_contract,
            "contract": contract_descriptor(task_contract),
            "exposure_index": {
                "development_exposed_item_keys": len(exposure.get("item_keys") or []),
                "exposed_groups": len(exposure.get("related_frame_groups") or []),
            },
        }

    def freeze_audit(
        self,
        audit_id: str,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        campaign_id_by_cohort: dict[str, str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> ReadinessManifest:
        manifest = self.load_manifest(audit_id)
        if manifest.lifecycle_state not in ("draft",):
            raise ReadinessStoreError(
                f"Cannot freeze audit in state {manifest.lifecycle_state!r}"
            )
        preview = self.preview(
            corpus_store,
            task_contract=manifest.task_contract,
            cohort_ids=list(manifest.selected_cohort_ids),
            campaign_id_by_cohort=campaign_id_by_cohort,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )
        rows: list[InventoryItemRecord] = preview["rows"]
        if not rows:
            raise ReadinessStoreError("No inventory rows to freeze")

        d = self.path_for(audit_id)
        payload = [r.to_dict() for r in rows]
        for row in payload:
            # strip any accidental absolute paths from display names
            for key in ("source_display_name",):
                val = str(row.get(key) or "")
                if is_absolute_local_path(val) or "\\" in val or val.startswith("/"):
                    row[key] = Path(val).name if val else ""
        self._write_jsonl(d / "label_inventory.jsonl", payload)
        inv_hash = deterministic_hash(payload)

        coverage = preview["coverage"]
        missingness = preview["missingness"]
        self._write_json(d / "coverage_summary.json", coverage)
        self._write_markdown_coverage(d / "coverage_summary.md", manifest, coverage)
        class_counts = coverage.get("target_label_counts") or coverage.get(
            "morphology_label_counts"
        ) or {}
        self._write_csv_dict(
            d / "class_distribution.csv",
            [{"class": k, "label_count": v} for k, v in sorted(class_counts.items())],
            ["class", "label_count"],
        )
        self._write_source_date_csv(d / "source_date_coverage.csv", rows)
        self._write_reviewer_csv(d / "reviewer_coverage.csv", rows)
        self._write_csv_dict(
            d / "missingness.csv",
            [
                {"category": k, "count": v}
                for k, v in sorted((missingness.get("categories") or {}).items())
            ],
            ["category", "count"],
        )
        contam_rows = [
            {
                "item_id": r.item_id,
                "cohort_id": r.cohort_id,
                "contamination_state": r.contamination_state,
                "related_frame_group": r.related_frame_group,
                "sequence_id": r.sequence_id,
                "source_date": r.source_date,
                "eligible_untouched_holdout": r.eligible_untouched_holdout,
            }
            for r in rows
        ]
        self._write_csv_dict(
            d / "contamination_summary.csv",
            contam_rows,
            [
                "item_id",
                "cohort_id",
                "contamination_state",
                "related_frame_group",
                "sequence_id",
                "source_date",
                "eligible_untouched_holdout",
            ],
        )

        feasibility = assess_holdout_feasibility(rows, audit_id=audit_id)
        self._write_json(d / "holdout_feasibility.json", feasibility.to_dict())
        self._write_text(
            d / "holdout_feasibility.md",
            self._feasibility_md(manifest, feasibility),
        )
        gaps = collection_gap_plan(rows, feasibility, coverage)
        self._write_json(
            d / "collection_gap_plan.json",
            {"actions": gaps, "note": "Planning targets, not validated statistical thresholds."},
        )

        manifest.lifecycle_state = "frozen"
        manifest.frozen_at = _utc_now()
        manifest.inventory_hash = inv_hash
        manifest.cohort_revisions = dict(preview.get("cohort_revisions") or {})
        manifest.compatibility_warnings = list(preview.get("warnings") or [])
        self._save_manifest(manifest)

        report = validate_audit_dir(d)
        self._write_json(d / "integrity_report.json", report)
        if not report["ok"]:
            raise ReadinessStoreError(
                "Frozen audit failed integrity validation: "
                + "; ".join(report["errors"])
            )
        if progress_cb:
            progress_cb(100, "Frozen")
        return self.load_manifest(audit_id)

    def run_holdout_feasibility(self, audit_id: str) -> HoldoutFeasibilityReport:
        manifest = self.load_manifest(audit_id)
        if manifest.lifecycle_state == "draft":
            raise ReadinessStoreError("Freeze the audit before holdout feasibility")
        rows = self.load_inventory(audit_id)
        report = assess_holdout_feasibility(rows, audit_id=audit_id)
        d = self.path_for(audit_id)
        self._write_json(d / "holdout_feasibility.json", report.to_dict())
        self._write_text(d / "holdout_feasibility.md", self._feasibility_md(manifest, report))
        return report

    def record_gate(
        self,
        audit_id: str,
        *,
        outcome: str,
        analyst_id: str,
        analyst_rationale: str,
        blockers: list[str] | None = None,
        required_next_actions: list[str] | None = None,
        limitations: list[str] | None = None,
    ) -> ReadinessGateRecord:
        manifest = self.load_manifest(audit_id)
        if manifest.lifecycle_state not in ("frozen", "reviewed", "gate_recorded"):
            raise ReadinessStoreError("Gate requires a frozen audit")
        rows = self.load_inventory(audit_id)
        coverage = build_coverage_summary(rows, task_contract=manifest.task_contract)
        missingness = build_missingness_report(rows, task_contract=manifest.task_contract)
        feasibility = assess_holdout_feasibility(rows, audit_id=audit_id)
        if required_next_actions is None:
            required_next_actions = collection_gap_plan(rows, feasibility, coverage)
        try:
            record = build_gate_record(
                manifest=manifest,
                coverage=coverage,
                missingness=missingness,
                feasibility=feasibility,
                outcome=outcome,
                blockers=blockers,
                analyst_id=analyst_id,
                analyst_rationale=analyst_rationale,
                required_next_actions=required_next_actions,
                limitations=limitations,
            )
        except ValueError as exc:
            raise ReadinessStoreError(str(exc)) from exc
        errs = validate_gate_record(record)
        if errs:
            raise ReadinessStoreError("Gate validation failed: " + "; ".join(errs))
        d = self.path_for(audit_id)
        self._write_json(d / "readiness_gate.json", record.to_dict())
        self._write_text(d / "readiness_gate.md", self._gate_md(manifest, record))
        manifest.lifecycle_state = "gate_recorded"
        manifest.gate_outcome = outcome
        self._save_manifest(manifest)
        return record

    def export_report(self, audit_id: str, export_dir: Path | None = None) -> Path:
        manifest = self.load_manifest(audit_id)
        rows = self.load_inventory(audit_id)
        d = self.path_for(audit_id)
        out = Path(export_dir) if export_dir else (
            self.project_root / "review_dataset" / "exports" / f"ml_readiness_{audit_id}"
        )
        out.mkdir(parents=True, exist_ok=True)
        coverage = build_coverage_summary(rows, task_contract=manifest.task_contract)
        missingness = build_missingness_report(rows, task_contract=manifest.task_contract)
        feasibility_path = d / "holdout_feasibility.json"
        feasibility = (
            HoldoutFeasibilityReport.from_dict(self._read_json(feasibility_path))
            if feasibility_path.exists()
            else assess_holdout_feasibility(rows, audit_id=audit_id)
        )
        gate_path = d / "readiness_gate.json"
        gate = self._read_json(gate_path) if gate_path.exists() else {}

        bundle = {
            "task_contract": manifest.task_contract,
            "audit_id": audit_id,
            "manifest_hash": manifest.manifest_hash,
            "inventory_hash": manifest.inventory_hash,
            "lifecycle_state": manifest.lifecycle_state,
            "denominators": coverage.get("denominators"),
            "class_distribution": coverage.get("target_label_counts")
            or coverage.get("morphology_label_counts"),
            "target_kind": coverage.get("target_kind"),
            "missingness": missingness,
            "contamination": {
                "development_exposed_items": (coverage.get("denominators") or {}).get(
                    "development_exposed_items"
                ),
            },
            "holdout_feasibility": feasibility.to_dict(),
            "gate_outcome": gate.get("outcome") or manifest.gate_outcome,
            "limitations": gate.get("limitations")
            or [
                "Descriptive readiness audit only.",
            ],
            "no_claim_statement_en": NO_CLAIM_STATEMENT_EN,
            "no_claim_statement_ru": NO_CLAIM_STATEMENT_RU,
            "cohort_revisions": manifest.cohort_revisions,
            "exclusion_accounting_note": (
                "See preview accounting and exclusion_reason fields on inventory rows."
            ),
        }
        self._write_json(out / "readiness_report.json", bundle)
        self._write_text(out / "readiness_report.md", self._report_md(manifest, coverage, gate, feasibility))
        for name in (
            "class_distribution.csv",
            "source_date_coverage.csv",
            "reviewer_coverage.csv",
            "missingness.csv",
            "contamination_summary.csv",
            "holdout_feasibility.json",
            "holdout_feasibility.md",
            "readiness_gate.json",
            "readiness_gate.md",
            "integrity_report.json",
        ):
            src = d / name
            if src.exists():
                (out / name).write_bytes(src.read_bytes())
        return out

    def create_revision(
        self,
        parent_audit_id: str,
        corpus_store: MorphologyReviewCorpusStore,
        *,
        revision_reason: str,
        analyst_id: str = "",
        campaign_id_by_cohort: dict[str, str] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancel_cb: Callable[[], bool] | None = None,
    ) -> ReadinessManifest:
        parent = self.load_manifest(parent_audit_id)
        if progress_cb:
            progress_cb(5, "Creating revision draft")
        draft = self.create_draft(
            title=f"{parent.title} (rev)",
            description=parent.description,
            task_contract=parent.task_contract,
            cohort_ids=list(parent.selected_cohort_ids),
            campaign_ids=list(parent.selected_campaign_ids),
            analyst_id=analyst_id or parent.analyst_id,
            parent_audit_id=parent_audit_id,
            revision_reason=revision_reason,
        )
        return self.freeze_audit(
            draft.audit_id,
            corpus_store,
            campaign_id_by_cohort=campaign_id_by_cohort,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )

    # --- writers ---

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_absolute_local_path(text):
            raise ReadinessStoreError("Refusing absolute paths in export text")
        path.write_text(text, encoding="utf-8")

    def _write_csv_dict(self, path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
        self._write_text(path, buf.getvalue())

    def _write_source_date_csv(self, path: Path, rows: list[InventoryItemRecord]) -> None:
        from collections import Counter

        from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
            is_valid_acquisition_date,
        )

        c = Counter(
            (
                r.source_display_name or r.source_sha256[:12],
                r.source_date if is_valid_acquisition_date(r.source_date) else "",
            )
            for r in rows
        )
        self._write_csv_dict(
            path,
            [
                {"source": a, "source_date": b, "label_count": n}
                for (a, b), n in sorted(c.items())
            ],
            ["source", "source_date", "label_count"],
        )

    def _write_reviewer_csv(self, path: Path, rows: list[InventoryItemRecord]) -> None:
        from collections import Counter

        c = Counter((r.reviewer_alias, r.reviewer_role) for r in rows if r.reviewer_alias)
        self._write_csv_dict(
            path,
            [
                {"reviewer_alias": a, "reviewer_role": b, "label_count": n}
                for (a, b), n in sorted(c.items())
            ],
            ["reviewer_alias", "reviewer_role", "label_count"],
        )

    def _write_markdown_coverage(
        self, path: Path, manifest: ReadinessManifest, coverage: dict[str, Any]
    ) -> None:
        dens = coverage.get("denominators") or {}
        lines = [
            f"# Coverage summary — {manifest.audit_id}",
            "",
            f"Task contract: `{manifest.task_contract}`",
            "",
            NO_CLAIM_STATEMENT_EN,
            "",
            "## Denominators",
            "",
        ]
        for k, v in dens.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append("## Morphology label counts")
        lines.append("")
        for k, v in sorted((coverage.get("morphology_label_counts") or {}).items()):
            lines.append(f"- {k}: {v}")
        for w in (coverage.get("correlation_warnings") or {}).get("en") or []:
            lines.append("")
            lines.append(f"> {w}")
        self._write_text(path, "\n".join(lines) + "\n")

    def _feasibility_md(
        self, manifest: ReadinessManifest, report: HoldoutFeasibilityReport
    ) -> str:
        return "\n".join(
            [
                f"# Holdout feasibility assessment — {manifest.audit_id}",
                "",
                f"Task contract: `{manifest.task_contract}`",
                "",
                report.note_en,
                "",
                f"Appears possible: {report.class_aware_group_separated_holdout_appears_possible}",
                f"Untouched groups: {len(report.untouched_eligible_groups)}",
                f"Exposed groups: {len(report.development_exposed_groups)}",
                f"Classes absent from untouched: {', '.join(report.classes_absent_from_untouched) or '(none)'}",
                "",
                NO_CLAIM_STATEMENT_EN,
                "",
            ]
        )

    def _gate_md(self, manifest: ReadinessManifest, record: ReadinessGateRecord) -> str:
        return "\n".join(
            [
                f"# Readiness Gate — {manifest.audit_id}",
                "",
                f"Outcome: `{record.outcome}`",
                f"Task contract: `{record.task_contract}`",
                f"Authorizes ML-B planning only: {record.authorizes_mlb_manifest_planning_only}",
                f"Authorizes training: {record.authorizes_training}",
                "",
                record.analyst_rationale,
                "",
                NO_CLAIM_STATEMENT_EN,
                "",
            ]
        )

    def _report_md(
        self,
        manifest: ReadinessManifest,
        coverage: dict[str, Any],
        gate: dict[str, Any],
        feasibility: HoldoutFeasibilityReport,
    ) -> str:
        dens = coverage.get("denominators") or {}
        return "\n".join(
            [
                f"# ML-A.1 Readiness Report — {manifest.audit_id}",
                "",
                f"Task contract: `{manifest.task_contract}`",
                f"Manifest hash: `{manifest.manifest_hash}`",
                f"Inventory hash: `{manifest.inventory_hash}`",
                f"Gate outcome: `{gate.get('outcome') or manifest.gate_outcome or '(none)'}`",
                "",
                NO_CLAIM_STATEMENT_EN,
                "",
                NO_CLAIM_STATEMENT_RU,
                "",
                f"Unique items: {dens.get('unique_current_items')}",
                f"Unique related-frame groups: {dens.get('unique_related_frame_groups')}",
                f"Unique sequences: {dens.get('unique_sequences')}",
                f"Holdout feasibility appears possible: "
                f"{feasibility.class_aware_group_separated_holdout_appears_possible}",
                "",
            ]
        )
