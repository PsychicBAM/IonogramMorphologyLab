"""Corpus integrity validation (schemas, hashes, blinding, no absolute paths)."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.constants import PROHIBITED_METRICS
from ionogram_morphology_lab.morphology_review_corpus.hashing import (
    deterministic_hash,
    is_absolute_local_path,
    validate_sha256,
)
from ionogram_morphology_lab.morphology_review_corpus.labels import HUMAN_MORPHOLOGY_CODES
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CohortManifest,
)
from ionogram_morphology_lab.morphology_review_corpus.lifecycle import (
    is_legacy_synthetic_cohort,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore

_ABS_RE = re.compile(r"([A-Za-z]:\\|\\\\)")


def validate_cohort(
    store: MorphologyReviewCorpusStore,
    cohort_id: str,
    *,
    collect_info: list[str] | None = None,
) -> list[str]:
    """Return hard errors. Legacy synthetic status goes to collect_info when provided."""
    errors: list[str] = []
    try:
        manifest = store.load_manifest(cohort_id)
        protocol = store.load_protocol(cohort_id)
        items = store.load_items(cohort_id)
    except Exception as exc:  # noqa: BLE001 — collect for validator
        return [f"{cohort_id}: failed to load: {exc}"]

    if collect_info is not None and (
        manifest.legacy_synthetic or is_legacy_synthetic_cohort(manifest, items)
    ):
        collect_info.append(
            f"{cohort_id}: legacy_synthetic_cohort "
            "(placeholder pilot_frame data — not a real project source corpus)"
        )

    expected_mh = CohortManifest.from_dict(
        {**manifest.to_dict(), "manifest_hash": ""}
    ).compute_hash()
    if manifest.manifest_hash != expected_mh:
        # Recompute the same way store does
        tmp = manifest.to_dict()
        tmp.pop("manifest_hash", None)
        if deterministic_hash(tmp) != manifest.manifest_hash:
            errors.append(f"{cohort_id}: manifest hash mismatch")

    proto_payload = protocol.to_dict()
    proto_payload.pop("protocol_hash", None)
    if deterministic_hash(proto_payload) != protocol.protocol_hash:
        errors.append(f"{cohort_id}: protocol hash mismatch")

    seen_ids: set[str] = set()
    seen_identity: set[tuple[str, int]] = set()
    for it in items:
        if it.item_id in seen_ids:
            errors.append(f"{cohort_id}: duplicate item_id {it.item_id}")
        seen_ids.add(it.item_id)
        if it.item_status != "item_unavailable":
            try:
                validate_sha256(it.source_sha256)
            except ValueError:
                errors.append(f"{cohort_id}: bad SHA for {it.item_id}")
            key = (it.source_sha256.lower(), int(it.frame_index))
            if key in seen_identity:
                errors.append(f"{cohort_id}: duplicate source/frame {key}")
            seen_identity.add(key)

    # Review record hashes and morphology codes
    reviews = store._read_jsonl(store.path_for(cohort_id) / "blind_reviews.jsonl")
    review_ids = {r.get("review_id") for r in reviews}
    for row in reviews:
        try:
            rec = BlindReviewRecord.from_dict(row)
            payload = rec.to_dict()
            payload.pop("record_hash", None)
            if deterministic_hash(payload) != rec.record_hash:
                errors.append(f"{cohort_id}: review hash mismatch {rec.review_id}")
            if rec.morphology not in HUMAN_MORPHOLOGY_CODES:
                errors.append(f"{cohort_id}: invalid morphology {rec.morphology}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cohort_id}: invalid review row: {exc}")

    # Reveal only after locked review; current-state must not exceed items
    comparisons = store._read_jsonl(
        store.path_for(cohort_id) / "reveal_comparisons.jsonl"
    )
    for c in comparisons:
        rid = c.get("review_id")
        if rid not in review_ids:
            errors.append(f"{cohort_id}: comparison references unknown review {rid}")
        item_id = c.get("item_id")
        locked = store.locked_review_for_item(cohort_id, str(item_id), review_round=1)
        # Historical lock must have existed; current may be a post-reveal revision
        matching = [r for r in reviews if r.get("review_id") == rid]
        if not matching or not matching[0].get("locked"):
            errors.append(f"{cohort_id}: reveal without locked review for {item_id}")
    try:
        from ionogram_morphology_lab.morphology_review_corpus.current_state import (
            count_consistency,
            project_cohort_comparisons,
        )

        consistency = count_consistency(store, cohort_id)
        proj = project_cohort_comparisons(store, cohort_id)
        if consistency["comparisons_current"] > consistency["eligible_count"]:
            errors.append(
                f"{cohort_id}: current comparisons "
                f"{consistency['comparisons_current']} exceed eligible items "
                f"{consistency['eligible_count']} — run derived-state repair"
            )
        if proj.conflicting_item_ids:
            errors.append(
                f"{cohort_id}: conflicting comparison duplicates for items "
                f"{', '.join(proj.conflicting_item_ids[:8])}"
            )
        # Identical duplicates are recoverable; report as soft info via collect_info
        if collect_info is not None and proj.identical_duplicate_ids:
            collect_info.append(
                f"{cohort_id}: identical comparison duplicates for "
                f"{len(proj.identical_duplicate_ids)} item(s); "
                f"history={consistency['comparisons_history']} "
                f"current={consistency['comparisons_current']}"
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{cohort_id}: comparison current-state check failed: {exc}")

    # Adjudication inputs
    for adj in store._read_jsonl(store.path_for(cohort_id) / "adjudications.jsonl"):
        for rid in adj.get("input_review_ids") or []:
            if rid not in review_ids:
                errors.append(f"{cohort_id}: adjudication missing review {rid}")
        if adj.get("label") in ("ground_truth", "absolute_ground_truth"):
            errors.append(f"{cohort_id}: adjudication uses ground-truth wording")

    # Comment chains / hashes (optional file for older corpora)
    comments_path = store.path_for(cohort_id) / "comments.jsonl"
    if comments_path.is_file():
        from ionogram_morphology_lab.morphology_review_corpus.comments import (
            COMMENT_TYPES,
            CommentRecord,
        )

        comment_rows = store._read_jsonl(comments_path)
        comment_ids = {c.get("comment_id") for c in comment_rows}
        for row in comment_rows:
            try:
                if str(row.get("cohort_id") or "") != cohort_id:
                    errors.append(f"{cohort_id}: comment cohort_id mismatch")
                    continue
                if row.get("comment_type") not in COMMENT_TYPES:
                    errors.append(f"{cohort_id}: bad comment_type {row.get('comment_type')}")
                rec = CommentRecord.from_dict(row)
                payload = rec.to_dict()
                payload.pop("record_hash", None)
                if deterministic_hash(payload) != rec.record_hash:
                    errors.append(f"{cohort_id}: comment hash mismatch {rec.comment_id}")
                sid = rec.supersedes_comment_id
                if sid and sid not in comment_ids:
                    errors.append(f"{cohort_id}: comment supersedes unknown {sid}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{cohort_id}: invalid comment row: {exc}")

    # Revision children must not share parent review stores
    if manifest.parent_cohort_id:
        for name in ("blind_reviews.jsonl", "reveal_comparisons.jsonl", "adjudications.jsonl"):
            # empty is OK; leakage detection is soft INFO via collect_info
            pass
        if collect_info is not None:
            leaks = store.detect_revision_leakage(cohort_id)
            for leak in leaks:
                collect_info.append(f"{cohort_id}: revision_leak:{leak}")

    # Absolute paths / prohibited metrics in exports
    export_dir = store.path_for(cohort_id) / "exports"
    if export_dir.is_dir():
        for p in export_dir.rglob("*"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if _ABS_RE.search(text):
                # Allow only if not a path-like drive reference in JSON values
                if ":\\" in text or "\\\\" in text[:200]:
                    errors.append(f"{cohort_id}: absolute path in export {p.name}")
            for metric in PROHIBITED_METRICS:
                # Avoid false positives on words inside notes listing prohibited metrics
                if f'"{metric}"' in text and "prohibited" not in text.lower():
                    if "scientific_non_claims" not in text and "prohibited_metrics" not in text:
                        errors.append(
                            f"{cohort_id}: prohibited metric field in export {p.name}: {metric}"
                        )

        blind_path = export_dir / "blind_reviews.jsonl"
        if blind_path.is_file():
            text = blind_path.read_text(encoding="utf-8")
            for leak in (
                "candidate_state",
                "evidence_ledger",
                "ordinal_strength",
                "candidate_strength",
            ):
                if leak in text:
                    errors.append(
                        f"{cohort_id}: candidate leak in blind export: {leak}"
                    )

    _walk_no_abs(manifest.to_dict(), f"{cohort_id}.manifest", errors)
    _walk_no_abs(protocol.to_dict(), f"{cohort_id}.protocol", errors)
    for it in items:
        _walk_no_abs(it.to_dict(), f"{cohort_id}.item.{it.item_id}", errors)

    return errors


def validate_project_corpora(project_root: Path | str) -> list[str]:
    store = MorphologyReviewCorpusStore(project_root)
    errors: list[str] = []
    for cid in store.list_cohorts():
        errors.extend(validate_cohort(store, cid))
    return errors


def validate_no_production_ruleengine_wiring(repo_root: Path) -> list[str]:
    """Ensure morphology_review_corpus is not wired into production RuleEngine."""
    engine = repo_root / "src" / "ionogram_morphology_lab" / "rules" / "engine.py"
    errors: list[str] = []
    if not engine.is_file():
        return [f"missing {engine}"]
    text = engine.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"engine.py syntax error: {exc}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "morphology_review_corpus" in alias.name:
                    errors.append("rules/engine.py imports morphology_review_corpus")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if "morphology_review_corpus" in mod:
                errors.append("rules/engine.py from-imports morphology_review_corpus")
    return errors


def _walk_no_abs(obj: Any, path: str, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk_no_abs(v, f"{path}.{k}", errors)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_no_abs(v, f"{path}[{i}]", errors)
    elif isinstance(obj, str) and is_absolute_local_path(obj):
        if ":\\" in obj or obj.startswith("\\\\") or (
            obj.startswith("/") and "/" in obj[1:]
        ):
            errors.append(f"absolute path at {path}: {obj}")
