"""Async Feature Pipeline V2 worker — generation-guarded, terminal states (Phase 4B.2f)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from ionogram_morphology_lab.cache.v2_feature_cache import V2FeatureCache, make_cache_key
from ionogram_morphology_lab.features.v2.pipeline import run_feature_pipeline_v2
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.scientific_outputs.signal_contracts import extract_frame_consistent
from ionogram_morphology_lab.ui.fd_frame_loader import cached_amplitude_matrix, cached_source_sha, frame_sha256
from ionogram_morphology_lab.ui.frame_diagnostic_context import next_request_generation_id


class V2DiagnosticsWorker(QThread):
    """Run V2 for one frame or a sequence without blocking the UI thread."""

    progress = Signal(dict)
    frame_done = Signal(dict)  # one completed frame row (sequence sync; not science change)
    finished_ok = Signal(dict)
    failed = Signal(dict)
    cancelled = Signal(dict)

    def __init__(
        self,
        *,
        mat_path: Path,
        frames: list[int],
        profile: dict[str, Any],
        profile_id: str,
        signal_contract_id: str,
        cache: V2FeatureCache,
        force_recompute: bool = False,
        request_generation_id: str | None = None,
        known_source_sha: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.mat_path = Path(mat_path)
        self.frames = [int(f) for f in frames]
        self.profile = profile
        self.profile_id = profile_id
        self.signal_contract_id = signal_contract_id
        self.cache = cache
        self.force_recompute = force_recompute
        self.request_generation_id = request_generation_id or next_request_generation_id()
        self.known_source_sha = known_source_sha
        self._cancel = False
        self.job_state = "idle"
        self.terminal_state: str | None = None

    def request_cancel(self) -> None:
        self._cancel = True

    def _emit_progress(self, **kwargs: Any) -> None:
        payload = {
            "request_generation_id": self.request_generation_id,
            "job_state": self.job_state,
            **kwargs,
        }
        self.progress.emit(payload)

    def _set_state(self, state: str) -> None:
        self.job_state = state
        self._emit_progress(stage=state)

    def run(self) -> None:  # noqa: N802
        gen = self.request_generation_id
        try:
            t_all = time.perf_counter()
            self._set_state("loading_frame")
            source_sha = self.known_source_sha or cached_source_sha(self.mat_path)
            try:
                source_sha = cached_source_sha(self.mat_path)
            except Exception:
                pass
            variable = str(self.profile.get("amplitude_variable_name") or "Amp_all")
            height = int(self.profile.get("height_bins") or 256)
            width = int(self.profile.get("frequency_bins") or 400)

            t0 = time.perf_counter()
            loaded = cached_amplitude_matrix(self.mat_path, variable)
            t_load_mat = time.perf_counter() - t0

            results: list[dict[str, Any]] = []
            cache_hits = 0
            recomputed = 0
            failures = 0
            n = len(self.frames)

            for i, frame_index in enumerate(self.frames):
                if self._cancel:
                    self.terminal_state = "cancelled"
                    self.job_state = "cancelled"
                    self.cancelled.emit(
                        {
                            "request_generation_id": gen,
                            "job_state": "cancelled",
                            "cache_hits": cache_hits,
                            "recomputed": recomputed,
                            "failures": failures,
                        }
                    )
                    return

                key = make_cache_key(
                    source_mat_sha256=source_sha,
                    frame_index=frame_index,
                    profile_id=self.profile_id,
                    signal_contract_id=self.signal_contract_id,
                    profile=self.profile,
                )
                pct = int(100 * i / max(1, n))
                self._set_state("checking_cache")
                self._emit_progress(
                    stage="checking_cache",
                    frame_index=frame_index,
                    frame_i=i + 1,
                    frame_n=n,
                    percent=pct,
                    cache_hits=cache_hits,
                    recomputed=recomputed,
                    failures=failures,
                    elapsed_s=time.perf_counter() - t_all,
                )

                if not self.force_recompute:
                    # Summary-only cache hit — never deserialize all masks here
                    hit = self.cache.load_summary(key)
                    if hit is not None:
                        cache_hits += 1
                        self.job_state = "loaded_from_cache"
                        self._emit_progress(
                            stage="loaded_from_cache",
                            frame_index=frame_index,
                            frame_i=i + 1,
                            frame_n=n,
                            percent=pct,
                            cache_hits=cache_hits,
                            recomputed=recomputed,
                        )
                        row = {
                            "frame_index": frame_index,
                            "status": "cached",
                            "key": key.to_dict(),
                            "result": hit["result"],
                            "masks": {},
                            "available_layers": hit.get("available_layers") or [],
                            "timings": {
                                "total_s": 0.0,
                                "from_cache": True,
                                "cache_read_s": 0.0,
                                "summary_only": True,
                            },
                            "request_generation_id": gen,
                            "source_sha256": source_sha,
                        }
                        results.append(row)
                        self.frame_done.emit(dict(row))
                        continue

                timings: dict[str, float] = {"matrix_load_s": t_load_mat}
                try:
                    self._set_state("loading_frame")
                    self._emit_progress(stage="loading_frame", frame_index=frame_index)
                    t1 = time.perf_counter()
                    frame, _rng = extract_frame_consistent(
                        loaded.data, frame_index, height_bins=height, frequency_bins=width
                    )
                    raw = np.asarray(frame)
                    timings["frame_load_s"] = time.perf_counter() - t1
                    raw_sha = frame_sha256(raw)

                    self._set_state("computing")
                    self._emit_progress(stage="computing", frame_index=frame_index)
                    t2 = time.perf_counter()
                    v2 = run_feature_pipeline_v2(
                        raw,
                        signal_contract_id=self.signal_contract_id,
                        profile_id=self.profile_id,
                        frame_index=frame_index,
                        source_mat_sha256=source_sha,
                    )
                    timings["pipeline_s"] = time.perf_counter() - t2
                    timings["total_s"] = timings["frame_load_s"] + timings["pipeline_s"]
                    timings["elapsed_pipeline_reported_s"] = float(getattr(v2, "elapsed_s", 0.0) or 0.0)

                    cache_write_ok = True
                    cache_write_error = ""
                    self._set_state("saving_cache")
                    self._emit_progress(stage="saving_cache", frame_index=frame_index)
                    t3 = time.perf_counter()
                    try:
                        self.cache.save(key, v2, timings=timings)
                    except Exception as cexc:  # noqa: BLE001
                        cache_write_ok = False
                        cache_write_error = str(cexc)
                    timings["serialize_s"] = time.perf_counter() - t3
                    recomputed += 1
                    row = {
                        "frame_index": frame_index,
                        "status": "recomputed",
                        "key": key.to_dict(),
                        "result": v2.to_serializable(),
                        "masks": dict(v2.masks),
                        "pipeline_result": v2,
                        "raw": raw,
                        "raw_frame_sha256": raw_sha,
                        "timings": timings,
                        "request_generation_id": gen,
                        "source_sha256": source_sha,
                        "cache_write_ok": cache_write_ok,
                        "cache_write_error": cache_write_error,
                    }
                    results.append(row)
                    # Emit serializable subset for UI sync (omit large pipeline/raw objects)
                    self.frame_done.emit(
                        {
                            "frame_index": frame_index,
                            "status": "recomputed",
                            "key": key.to_dict(),
                            "result": row["result"],
                            "masks": {},
                            "available_layers": sorted((v2.masks or {}).keys()),
                            "timings": timings,
                            "request_generation_id": gen,
                            "source_sha256": source_sha,
                            "cache_write_ok": cache_write_ok,
                            "cache_write_error": cache_write_error,
                            "pipeline_result": v2,
                            "raw": raw,
                            "raw_frame_sha256": raw_sha,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    row = {
                        "frame_index": frame_index,
                        "status": "failed",
                        "error": str(exc),
                        "key": key.to_dict(),
                        "request_generation_id": gen,
                        "source_sha256": source_sha,
                    }
                    results.append(row)
                    self.frame_done.emit(dict(row))

            if self._cancel:
                self.terminal_state = "cancelled"
                self.job_state = "cancelled"
                self.cancelled.emit(
                    {
                        "request_generation_id": gen,
                        "job_state": "cancelled",
                        "cache_hits": cache_hits,
                        "recomputed": recomputed,
                        "failures": failures,
                    }
                )
                return

            self.terminal_state = "completed"
            self.job_state = "completed"
            self.finished_ok.emit(
                {
                    "request_generation_id": gen,
                    "job_state": "completed",
                    "source_sha": source_sha,
                    "feature_version": FEATURE_VERSION,
                    "results": results,
                    "cache_hits": cache_hits,
                    "recomputed": recomputed,
                    "failures": failures,
                    "elapsed_s": time.perf_counter() - t_all,
                    "mat_path": str(self.mat_path),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.terminal_state = "failed"
            self.job_state = "failed"
            self.failed.emit(
                {
                    "request_generation_id": gen,
                    "job_state": "failed",
                    "error": str(exc),
                }
            )
