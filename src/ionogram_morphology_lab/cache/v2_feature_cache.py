"""Source-specific Feature Pipeline V2 result cache (Phase 4B.2e).

Separate from Viewer FrameStore render cache. Never modifies source MAT files.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION, PipelineV2Result
from ionogram_morphology_lab.utils.paths import ensure_dir


CACHE_FORMAT = "iml2-v2-feature-cache-v1"
EXTRACTOR_VERSION = "extract_frame_consistent_v1"


@dataclass(frozen=True)
class V2CacheKey:
    source_mat_sha256: str
    frame_index: int
    profile_id: str
    signal_contract_id: str
    feature_version: str
    algorithm_parameter_hash: str
    extractor_version: str = EXTRACTOR_VERSION

    def digest(self) -> str:
        payload = "|".join(
            [
                self.source_mat_sha256,
                str(int(self.frame_index)),
                self.profile_id,
                self.signal_contract_id,
                self.feature_version,
                self.algorithm_parameter_hash,
                self.extractor_version,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_mat_sha256": self.source_mat_sha256,
            "frame_index": int(self.frame_index),
            "profile_id": self.profile_id,
            "signal_contract_id": self.signal_contract_id,
            "feature_version": self.feature_version,
            "algorithm_parameter_hash": self.algorithm_parameter_hash,
            "extractor_version": self.extractor_version,
            "digest": self.digest(),
        }


def algorithm_parameter_hash(profile: dict[str, Any] | None = None) -> str:
    """Stable hash of parameters that affect V2 inputs (not geometry constants)."""
    profile = profile or {}
    relevant = {
        "amplitude_variable_name": profile.get("amplitude_variable_name", "Amp_all"),
        "height_bins": int(profile.get("height_bins") or 256),
        "frequency_bins": int(profile.get("frequency_bins") or 400),
        "matrix_layout": profile.get("matrix_layout", "frames_stacked_rows"),
        "feature_version": FEATURE_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
    }
    blob = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def make_cache_key(
    *,
    source_mat_sha256: str,
    frame_index: int,
    profile_id: str,
    signal_contract_id: str,
    profile: dict[str, Any] | None = None,
    feature_version: str = FEATURE_VERSION,
) -> V2CacheKey:
    return V2CacheKey(
        source_mat_sha256=source_mat_sha256,
        frame_index=int(frame_index),
        profile_id=str(profile_id or ""),
        signal_contract_id=str(signal_contract_id or ""),
        feature_version=feature_version,
        algorithm_parameter_hash=algorithm_parameter_hash(profile),
    )


class V2FeatureCache:
    """Filesystem cache under ``{cache_root}/v2_features/{digest[:24]}/``."""

    def __init__(self, cache_root: Path | str):
        self.cache_root = Path(cache_root)
        self.root = ensure_dir(self.cache_root / "v2_features")
        self._index_scan_count = 0
        self._index_hit_count = 0

    def _dir(self, key: V2CacheKey) -> Path:
        return self.root / key.digest()[:24]

    def _source_index_path(self, source_mat_sha256: str) -> Path:
        digest = hashlib.sha256(source_mat_sha256.encode("utf-8")).hexdigest()[:24]
        return self.root / "_source_index" / f"{digest}.json"

    def load_source_index(self, source_mat_sha256: str) -> dict[str, Any] | None:
        path = self._source_index_path(source_mat_sha256)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def update_source_index(self, key: V2CacheKey, *, summary_path: str = "") -> None:
        """Incremental index maintenance after a V2 result is saved."""
        path = self._source_index_path(key.source_mat_sha256)
        ensure_dir(path.parent)
        idx = self.load_source_index(key.source_mat_sha256) or {
            "schema_version": 1,
            "source_mat_sha256": key.source_mat_sha256,
            "feature_version": key.feature_version,
            "frames": {},
            "last_update": 0.0,
        }
        frames = idx.setdefault("frames", {})
        frames[str(int(key.frame_index))] = {
            "digest": key.digest(),
            "dir": key.digest()[:24],
            "summary_path": summary_path or str(self._dir(key) / "summary_index.json"),
            "profile_id": key.profile_id,
            "signal_contract_id": key.signal_contract_id,
            "algorithm_parameter_hash": key.algorithm_parameter_hash,
        }
        idx["feature_version"] = key.feature_version
        idx["last_update"] = time.time()
        path.write_text(json.dumps(idx, indent=2), encoding="utf-8")

    def lookup_frame_in_index(self, key: V2CacheKey) -> dict[str, Any] | None:
        """Direct key/path lookup — does not recursively scan cache directories."""
        idx = self.load_source_index(key.source_mat_sha256)
        if not idx:
            return None
        self._index_hit_count += 1
        entry = (idx.get("frames") or {}).get(str(int(key.frame_index)))
        if not entry:
            return None
        if entry.get("digest") != key.digest():
            return None
        return entry

    def status_for(self, key: V2CacheKey) -> str:
        return str(self.diagnose_lookup(key).get("status") or "not_computed")

    def diagnose_lookup(self, key: V2CacheKey) -> dict[str, Any]:
        """Explain cache hit/miss for a frame — never treats a bare directory as a hit."""
        d = self._dir(key)
        diag: dict[str, Any] = {
            "cache_key": key.digest(),
            "cache_root": str(self.cache_root),
            "cache_dir": str(d),
            "source_sha": key.source_mat_sha256,
            "feature_version": key.feature_version,
            "parameter_hash": key.algorithm_parameter_hash,
            "frame_index": int(key.frame_index),
            "index_found": False,
            "summary_found": False,
            "requested_quick_layers_found": [],
            "miss_reason": "",
            "invalidation_reason": "",
            "status": "not_computed",
        }
        entry = self.lookup_frame_in_index(key)
        diag["index_found"] = entry is not None
        summary_path = d / "result.json"
        if entry is not None:
            if not d.is_dir() or not summary_path.is_file():
                diag["status"] = "error"
                diag["miss_reason"] = "index_entry_without_summary"
                diag["invalidation_reason"] = "missing_result_json"
                return diag
            diag["summary_found"] = True
            diag["status"] = "cached"
            diag["miss_reason"] = ""
            return diag
        if not d.is_dir():
            diag["miss_reason"] = "no_cache_directory"
            return diag
        meta_path = d / "key.json"
        if not meta_path.is_file():
            diag["status"] = "error"
            diag["miss_reason"] = "directory_without_key_json"
            # Bare directory is never a cache hit.
            return diag
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("digest") != key.digest():
                diag["status"] = "stale"
                diag["miss_reason"] = "digest_mismatch"
                diag["invalidation_reason"] = "digest_mismatch"
                return diag
            if meta.get("feature_version") != key.feature_version:
                diag["status"] = "stale"
                diag["miss_reason"] = "feature_version_mismatch"
                diag["invalidation_reason"] = "feature_version_mismatch"
                return diag
            if not summary_path.is_file():
                diag["status"] = "error"
                diag["miss_reason"] = "missing_result_json"
                diag["invalidation_reason"] = "missing_result_json"
                return diag
            diag["summary_found"] = True
            try:
                self.update_source_index(key)
            except Exception:
                pass
            diag["status"] = "cached"
            diag["miss_reason"] = ""
            return diag
        except Exception as exc:  # noqa: BLE001
            diag["status"] = "error"
            diag["miss_reason"] = f"meta_read_error:{exc}"
            return diag

    def available_layers(self, key: V2CacheKey) -> list[str]:
        d = self._dir(key)
        # Prefer summary_index.json to avoid globbing masks/
        idx_path = d / "summary_index.json"
        if idx_path.is_file():
            try:
                data = json.loads(idx_path.read_text(encoding="utf-8"))
                layers = data.get("available_layers")
                if isinstance(layers, list):
                    return [str(x) for x in layers]
            except Exception:
                pass
        masks_dir = d / "masks"
        if not masks_dir.is_dir():
            return []
        return sorted(p.stem for p in masks_dir.glob("*.npy"))

    def load_summary(self, key: V2CacheKey) -> dict[str, Any] | None:
        """Load lightweight result JSON only — no mask arrays."""
        if self.status_for(key) != "cached":
            return None
        d = self._dir(key)
        try:
            result = json.loads((d / "result.json").read_text(encoding="utf-8"))
            layers = self.available_layers(key)
            return {
                "result": result,
                "masks": {},
                "centerlines": result.get("centerlines") or [],
                "key": key.to_dict(),
                "cache_dir": str(d),
                "loaded_from_cache": True,
                "summary_only": True,
                "available_layers": layers,
            }
        except Exception:
            return None

    def load_layer(self, key: V2CacheKey, layer_name: str) -> np.ndarray | None:
        if self.status_for(key) != "cached":
            return None
        path = self._dir(key) / "masks" / f"{layer_name}.npy"
        if not path.is_file():
            return None
        try:
            return np.load(path)
        except Exception:
            return None

    def load_layers(self, key: V2CacheKey, layer_names: list[str] | None = None) -> dict[str, np.ndarray]:
        if self.status_for(key) != "cached":
            return {}
        d = self._dir(key) / "masks"
        if not d.is_dir():
            return {}
        names = layer_names if layer_names is not None else [p.stem for p in d.glob("*.npy")]
        out: dict[str, np.ndarray] = {}
        for name in names:
            p = d / f"{name}.npy"
            if p.is_file():
                try:
                    out[name] = np.load(p)
                except Exception:
                    continue
        return out

    def load(self, key: V2CacheKey) -> dict[str, Any] | None:
        """Full load (summary + all masks). Prefer load_summary + load_layers for UI."""
        summary = self.load_summary(key)
        if summary is None:
            return None
        summary["masks"] = self.load_layers(key)
        summary["summary_only"] = False
        return summary

    def save(
        self,
        key: V2CacheKey,
        pipeline_result: PipelineV2Result,
        *,
        summary_text: str = "",
        timings: dict[str, float] | None = None,
    ) -> Path:
        d = ensure_dir(self._dir(key))
        (d / "key.json").write_text(
            json.dumps({**key.to_dict(), "format": CACHE_FORMAT, "saved_at": time.time()}, indent=2),
            encoding="utf-8",
        )
        ser = pipeline_result.to_serializable()
        # Compact summary index for fast frame selection
        feats = ser.get("features") or {}
        summary_index = {
            "quality_status": ser.get("quality_status"),
            "branch_count": len(ser.get("centerlines") or []),
            "oversegmentation_suspected": bool(ser.get("oversegmentation_suspected")),
            "available_layers": sorted((pipeline_result.masks or {}).keys()),
            "feature_ids": sorted(feats.keys()),
            "feature_version": key.feature_version,
            "source_mat_sha256": key.source_mat_sha256,
            "frame_index": key.frame_index,
        }
        (d / "summary_index.json").write_text(
            json.dumps(summary_index, indent=2, default=str), encoding="utf-8"
        )
        (d / "result.json").write_text(json.dumps(ser, indent=2, default=str), encoding="utf-8")
        if summary_text:
            (d / "summary.txt").write_text(summary_text, encoding="utf-8")
        if timings:
            (d / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
        masks_dir = ensure_dir(d / "masks")
        for name, arr in (pipeline_result.masks or {}).items():
            np.save(masks_dir / f"{name}.npy", arr)
        try:
            self.update_source_index(key, summary_path=str(d / "summary_index.json"))
        except Exception:
            pass
        return d

    def clear_for_source(self, source_mat_sha256: str) -> int:
        """Remove cache entries for one source SHA. Never touches MAT files."""
        removed = 0
        # Prefer index-driven removal; fall back to keyed dirs only
        idx = self.load_source_index(source_mat_sha256)
        if idx and isinstance(idx.get("frames"), dict):
            for _fid, entry in list(idx["frames"].items()):
                child = self.root / str(entry.get("dir") or "")
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                    removed += 1
            try:
                self._source_index_path(source_mat_sha256).unlink(missing_ok=True)
            except Exception:
                pass
            return removed
        if not self.root.is_dir():
            return 0
        self._index_scan_count += 1
        for child in list(self.root.iterdir()):
            if child.name.startswith("_"):
                continue
            key_path = child / "key.json"
            if not key_path.is_file():
                continue
            try:
                meta = json.loads(key_path.read_text(encoding="utf-8"))
                if meta.get("source_mat_sha256") == source_mat_sha256:
                    shutil.rmtree(child, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
        return removed


def cache_status_label(code: str, language: str) -> str:
    ru = language == "ru"
    mapping = {
        "not_computed": ("Не рассчитано", "Not computed"),
        "running": ("Рассчитывается", "Computing"),
        "cached": ("Загружено из кэша", "Loaded from cache"),
        "recomputed": ("Рассчитано заново", "Recomputed"),
        "stale": ("Кэш устарел", "Cache stale"),
        "error": ("Ошибка", "Error"),
    }
    pair = mapping.get(code, mapping["not_computed"])
    return pair[0] if ru else pair[1]
