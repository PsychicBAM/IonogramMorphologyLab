"""End-to-end frame analysis and batch processing."""

from __future__ import annotations

import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.database.project_db import ProjectDatabase
from ionogram_morphology_lab.disagreement.engine import DisagreementEngine
from ionogram_morphology_lab.features.extract import extract_features
from ionogram_morphology_lab.importers.adapters import load_amplitude_matrix
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
from ionogram_morphology_lab.importers.audit import audit_frame, audit_mat_path
from ionogram_morphology_lab.instrument_profiles.schema import (
    load_profile,
    frequency_axis_from_profile,
    range_axis_from_profile,
    profiles_dir,
)
from ionogram_morphology_lab.projects.model import AnalysisProject, RunLayout, new_run
from ionogram_morphology_lab.provenance.manifest import write_reproducibility_manifest
from ionogram_morphology_lab.reference_atlas.atlas import ReferenceAtlas
from ionogram_morphology_lab.rendering.ionogram_render import RenderSpec, render_raw_ionogram
from ionogram_morphology_lab.rules.engine import RuleEngine
from ionogram_morphology_lab.segmentation.trace_interference import segment_frame
from ionogram_morphology_lab.security import ForbiddenPathError, default_blocklist
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import ensure_dir


def _load_profile(profile_id: str):
    path = profiles_dir() / f"{profile_id}.yaml"
    if not path.exists():
        # try generic
        path = profiles_dir() / "generic_user_template.yaml"
    return load_profile(path)


def analyze_frame(
    frame: np.ndarray,
    *,
    project: AnalysisProject,
    run: RunLayout,
    source_path: str,
    source_sha256: str,
    frame_index: int,
    profile_id: str,
    source_variable: str = "Amp_all",
    neighbor_masks: list[np.ndarray] | None = None,
) -> dict[str, Any]:
    profile = _load_profile(profile_id)
    freq = frequency_axis_from_profile(profile)
    rng = range_axis_from_profile(profile)
    q = audit_frame(frame)
    seg = segment_frame(frame)
    feats = extract_features(frame, seg)
    engine = RuleEngine()
    rule_res = engine.evaluate(feats.values, quality_status=q["status"])
    temporal_block: dict[str, Any] = {}
    if neighbor_masks:
        from ionogram_morphology_lab.features.temporal_context import temporal_conclusion

        masks = list(neighbor_masks) + [seg.trace_mask]
        temporal_block = temporal_conclusion(
            masks, single_frame_morphology=rule_res.candidate_morphology
        )
    atlas = ReferenceAtlas()
    refs = atlas.find_nearest(feats.values, rule_res.candidate_morphology, top_k=5)
    interference_status = getattr(rule_res, "interference_assessment", None) or (
        "dominant" if feats.values.get("interference_dominance", 0) >= 0.55 else "none"
    )
    dis = DisagreementEngine().analyze(
        rule_category=rule_res.candidate_morphology,
        rule_flags=rule_res.disagreement_flags,
        reference_categories=[r.case.canonical_terminology for r in refs],
        interference_status=interference_status,
        possible_ox=feats.values.get("possible_ox_compatibility", 0) >= 0.5,
        low_signal=bool(q.get("low_signal")),
        domain_mismatch=profile.profile_verification_status == "user-defined-unverified",
    )

    frame_id = f"{Path(source_path).stem}_f{frame_index:04d}"
    # renders
    raw_path = run.root / "raw_renders" / f"{frame_id}.png"
    render_raw_ionogram(
        frame,
        freq,
        rng,
        raw_path,
        spec=RenderSpec(
            profile_source=profile_id,
            range_label_en=profile.range_axis_label_en,
            range_label_ru=profile.range_axis_label_ru,
            view_kind="raw",
            scaling_method="none",
        ),
        title=f"{frame_id} (raw)",
    )
    # save masks metadata (not overwriting raw)
    np.save(run.root / "masks" / f"{frame_id}_trace.npy", seg.trace_mask)
    np.save(run.root / "masks" / f"{frame_id}_interference.npy", seg.interference_mask)

    created = datetime.now(timezone.utc).isoformat()
    record = {
        "project_id": project.project_id,
        "run_id": run.run_id,
        "frame_id": frame_id,
        "source_path_hash": sha256_file(source_path)[:16] if Path(source_path).is_file() else "",
        "source_file_sha256": source_sha256,
        "source_variable": source_variable,
        "frame_index": frame_index,
        "profile_id": profile_id,
        "profile_verification_status": profile.profile_verification_status,
        "raw_shape": list(frame.shape),
        "frequency_axis_source": profile.frequency_variable_name or "profile_constructed",
        "range_axis_source": "nominal_virtual_height_profile",
        "data_quality_status": q["status"],
        "candidate_morphology": rule_res.candidate_morphology,
        "final_auto_status": rule_res.confidence_status,
        "confidence_score": None,
        "confidence_calibration_status": "uncalibrated",
        "top_alternative_1": rule_res.alternative_categories[0]
        if rule_res.alternative_categories
        else None,
        "top_alternative_2": rule_res.alternative_categories[1]
        if len(rule_res.alternative_categories) > 1
        else None,
        "activated_rules": rule_res.activated_rules,
        "contradicted_rules": rule_res.contradicting_rules,
        "measured_features": feats.values,
        # Single-frame persistence features live in measured_features; multi-frame
        # temporal conclusions are stored separately when neighbors are supplied.
        "temporal_features": (temporal_block.get("temporal_features") or {}),
        "temporal_conclusion": temporal_block or None,
        "nearest_references": [r.to_dict() for r in refs],
        "source_ids": [c["source_id"] for c in rule_res.source_citations],
        "source_pages": [c["source_page"] for c in rule_res.source_citations],
        "disagreement_flags": dis.flags,
        "alternative_interpretations": dis.pairs,
        "possible_ox_confusion": feats.values.get("possible_ox_compatibility", 0) >= 0.5,
        "interference_status": interference_status,
        "near_threshold_rules": getattr(rule_res, "near_threshold_rules", []),
        "abstention_reason": rule_res.abstention_reason,
        "out_of_domain_status": "outside_reference_domain" in dis.flags,
        "prohibited_causal_claims": rule_res.prohibited_causal_claims,
        "processing_version": __version__,
        "rule_pack_version": project.rule_pack_version,
        "reference_pack_version": project.reference_atlas_version,
        "model_version": "none",
        "created_at": created,
        "limitations": feats.limitations + [seg.limitations],
        "explanations_en": rule_res.explanations_en,
        "explanations_ru": rule_res.explanations_ru,
        "raw_render_path": str(raw_path),
        "segmentation_method": seg.method,
        "wording_en": "proposed classification / candidate morphology — requires expert review",
        "wording_ru": "предложенная классификация / кандидатная морфология — требуется экспертная проверка",
    }
    # v1.1 separate scientific axes — never a single overloaded "ionogram type"
    try:
        from ionogram_morphology_lab.scientific_outputs.result_schema import build_from_pipeline_record

        sci = build_from_pipeline_record(record)
        record["scientific_axes"] = sci.to_dict()
        record["layer"] = sci.layer
        record["morphology"] = sci.morphology
        record["ambiguity"] = sci.ambiguity
        # keep candidate_morphology for IML1 Results browser compatibility
        record["candidate_morphology"] = sci.morphology
    except Exception as exc:  # noqa: BLE001
        # Never leave a prior positive morphology after a serialization failure.
        record["scientific_axes_error"] = str(exc)
        record["morphology"] = "indeterminate"
        record["candidate_morphology"] = "indeterminate"
        record["layer"] = "indeterminate"
        record["ambiguity"] = "indeterminate"
        record["final_auto_status"] = "not_assessable"
        record["limitations"] = list(record.get("limitations") or []) + [
            f"scientific_axes_serialization_failed:{exc}"
        ]

    # Feature Pipeline V2 shadow store — never feeds RuleEngine / morphology.
    record["feature_pipeline_v2"] = None
    try:
        from ionogram_morphology_lab.app.settings_store import SettingsStore
        from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2

        settings = SettingsStore()
        v2_on = bool(settings.get("analysis", "scientific_feature_pipeline_v2_enabled", False))
        if v2_on:
            v2 = run_feature_pipeline_v2(
                frame,
                signal_contract_id="kfu_amp_all_v1",
                profile_id=profile_id,
                frame_index=frame_index,
                source_mat_sha256=source_sha256,
                frequency_axis=freq,
                height_axis=rng,
            )
            shadow = v2.to_serializable()
            record["feature_pipeline_v2"] = shadow
            ensure_dir(run.root / "features_v2")
            (run.root / "features_v2" / f"{frame_id}.json").write_text(
                json.dumps(shadow, indent=2, default=str), encoding="utf-8"
            )
    except Exception as exc:  # noqa: BLE001
        record["feature_pipeline_v2_error"] = str(exc)

    pred_path = run.root / "predictions" / f"{frame_id}.json"
    pred_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    (run.root / "features" / f"{frame_id}.json").write_text(
        json.dumps(feats.to_dict(), indent=2), encoding="utf-8"
    )

    morph = rule_res.candidate_morphology
    if morph not in (
        "frequency",
        "range",
        "mixed",
        "none",
        "indeterminate",
        "artifact",
        "not_assessable",
        "abstain",
    ):
        morph = "abstain"
    # copy pointer file into by_morphology (derivative only)
    pointer = run.root / "by_morphology" / morph / f"{frame_id}.json"
    pointer.write_text(json.dumps({"frame_id": frame_id, "path": str(pred_path)}), encoding="utf-8")
    if dis.flags:
        dpointer = run.root / "by_morphology" / "disagreement" / f"{frame_id}.json"
        dpointer.write_text(
            json.dumps({"frame_id": frame_id, "flags": dis.flags}), encoding="utf-8"
        )

    db = ProjectDatabase(Path(project.root) / "project.sqlite")
    db.insert_frame_result(frame_id, run.run_id, record, created)
    db.append_audit(created, "frame_analyzed", {"frame_id": frame_id, "morphology": morph})
    return record


class BatchController:
    def __init__(self):
        self._paused = False
        self._cancel = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def cancel(self) -> None:
        self._cancel = True

    @property
    def cancelled(self) -> bool:
        return self._cancel

    @property
    def paused(self) -> bool:
        return self._paused


def batch_analyze(
    project: AnalysisProject,
    mat_paths: list[Path | str],
    frame_indices: list[int] | None = None,
    frame_step: int = 10,
    max_workers: int = 1,
    progress_cb: Callable[[dict[str, Any]], None] | None = None,
    controller: BatchController | None = None,
    operations: list[str] | None = None,
    frame_store_factory: Callable[..., Any] | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    """Batch process MAT files with error isolation. Never modifies sources."""
    controller = controller or BatchController()
    run = new_run(project)
    profile = _load_profile(project.profile_id)
    ops = operations or ["full_pipeline"]
    config = {
        "profile_id": project.profile_id,
        "frame_step": frame_step,
        "frame_indices": frame_indices,
        "mat_paths": [str(p) for p in mat_paths],
        "max_workers": max_workers,
        "operations": ops,
        "selection_explanation": explanation,
        "seed": 0,
    }
    (run.root / "config" / "run_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    db = ProjectDatabase(Path(project.root) / "project.sqlite")
    db.insert_run(run.run_id, project.project_id, datetime.now(timezone.utc).isoformat(), config)

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    indices = frame_indices or list(range(1, profile.frames_per_file + 1, frame_step))
    total = max(1, len(mat_paths) * len(indices))
    done = 0
    t0 = datetime.now(timezone.utc)

    for mat_path in mat_paths:
        while controller.paused and not controller.cancelled:
            pass
        if controller.cancelled:
            break
        try:
            default_blocklist().assert_allowed(mat_path)
        except ForbiddenPathError as exc:
            errors.append({"path": str(mat_path), "error": str(exc), "status": "blocked_path"})
            continue
        if progress_cb:
            progress_cb(
                {
                    "event": "progress",
                    "file": Path(mat_path).name,
                    "operation": "audit",
                    "completed": done,
                    "total": total,
                    "percent": round(100.0 * done / total, 1),
                }
            )
        audit = audit_mat_path(mat_path, profile.to_dict())
        (run.root / "audit" / f"{Path(mat_path).stem}_audit.json").write_text(
            json.dumps(audit.to_dict(), indent=2), encoding="utf-8"
        )
        if "audit" in ops and set(ops) == {"audit"}:
            done += len(indices)
            continue
        if audit.status in ("CRC_error", "unreadable", "blocked_path", "insufficient_metadata"):
            errors.append({"path": str(mat_path), "status": audit.status, "error": audit.error})
            if progress_cb:
                progress_cb({"event": "file_failed", "path": str(mat_path), "status": audit.status})
            continue
        try:
            store = None
            loaded = None
            sha = audit.sha256 or ""
            use_store = frame_store_factory is not None and (
                "build_cache" in ops
                or "full_pipeline" in ops
                or "render" in ops
                or "features" in ops
                or "rules" in ops
            )
            if use_store:
                store = frame_store_factory(mat_path, profile.to_dict())
                if progress_cb:
                    progress_cb(
                        {
                            "event": "progress",
                            "operation": "build_cache",
                            "file": Path(mat_path).name,
                        }
                    )
                store.ensure_ready(progress_cb=progress_cb)
                sha = store.source_sha256 or sha
            else:
                loaded = load_amplitude_matrix(
                    mat_path, variable=profile.amplitude_variable_name
                )
            for idx in indices:
                while controller.paused and not controller.cancelled:
                    pass
                if controller.cancelled:
                    break
                try:
                    if store is not None:
                        frame = store.get_frame(idx)
                    elif loaded is not None and loaded.data.shape[0] % profile.height_bins == 0 and loaded.data.shape[1] == profile.frequency_bins:
                        frame, _ = extract_frame_consistent(
                            loaded.data,
                            idx,
                            height_bins=profile.height_bins,
                            frequency_bins=profile.frequency_bins,
                        )
                    elif loaded is not None:
                        frame = np.array(loaded.data, copy=True)
                        idx = 1
                    else:
                        raise RuntimeError("no_frame_source")
                    if "full_pipeline" in ops or "features" in ops or "rules" in ops or "render" in ops:
                        rec = analyze_frame(
                            frame,
                            project=project,
                            run=run,
                            source_path=str(mat_path),
                            source_sha256=sha,
                            frame_index=idx,
                            profile_id=project.profile_id,
                            source_variable=profile.amplitude_variable_name,
                        )
                        results.append(rec)
                    done += 1
                    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
                    eta = (elapsed / max(done, 1)) * (total - done)
                    if progress_cb:
                        progress_cb(
                            {
                                "event": "progress",
                                "file": Path(mat_path).name,
                                "frame": idx,
                                "completed": done,
                                "total": total,
                                "percent": round(100.0 * done / total, 1),
                                "elapsed_s": round(elapsed, 1),
                                "eta_s": round(eta, 1),
                                "operation": "analyze",
                                "cache_hits": store.stats["cache_hits"] if store else 0,
                                "cache_misses": store.stats["cache_misses"] if store else 0,
                                "errors": len(errors),
                            }
                        )
                except Exception as exc:  # noqa: BLE001 — isolate per frame
                    errors.append(
                        {
                            "path": str(mat_path),
                            "frame_index": idx,
                            "error": str(exc),
                            "trace": traceback.format_exc(),
                        }
                    )
                    done += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": str(mat_path), "error": str(exc), "status": "file_exception"})

    summary = {
        "run_id": run.run_id,
        "n_results": len(results),
        "n_errors": len(errors),
        "errors": errors,
        "run_root": str(run.root),
    }
    (run.root / "logs" / "batch_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_reproducibility_manifest(
        run.root / "exports" / "reproducibility_manifest.json",
        project=project,
        run_id=run.run_id,
        config=config,
        n_results=len(results),
    )
    return summary
