"""Display-ready layer cache for Feature Diagnostics (Phase 4B.2f).

Invalidated when FrameDiagnosticContext identity changes. Zoom/opacity/presets
only recomposite — they never rewrite the V2 scientific cache.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ionogram_morphology_lab.ui.fd_display import (
    jet_like_rgb,
    prepare_centerline_mask,
    prepare_overlay_mask,
    scientific_to_display_gray,
)
from ionogram_morphology_lab.ui.frame_diagnostic_context import FrameDiagnosticContext


class DisplayLayerCache:
    def __init__(self) -> None:
        self._ctx_id: str | None = None
        self._layers: dict[str, np.ndarray] = {}
        self._hits = 0
        self._misses = 0

    def clear(self) -> None:
        self._ctx_id = None
        self._layers.clear()

    def bind_context(self, ctx: FrameDiagnosticContext | None) -> None:
        cid = None if ctx is None else f"{ctx.cache_key_digest}:{ctx.raw_frame_sha256}:{ctx.request_generation_id}"
        if cid != self._ctx_id:
            self.clear()
            self._ctx_id = cid

    def get(self, key: str) -> np.ndarray | None:
        hit = self._layers.get(key)
        if hit is not None:
            self._hits += 1
            return hit
        self._misses += 1
        return None

    def put(self, key: str, arr: np.ndarray) -> np.ndarray:
        self._layers[key] = arr
        return arr

    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "layers": len(self._layers)}

    def ensure_bases(self, raw: np.ndarray, masks: dict[str, np.ndarray], result: Any) -> None:
        if self.get("base_jet") is None:
            self.put("base_jet", jet_like_rgb(raw))
        if self.get("base_gray") is None:
            self.put("base_gray", scientific_to_display_gray(raw))
        if self.get("base_norm") is None:
            sci = raw
            if result is not None and hasattr(result, "representations"):
                dn = result.representations.get("diagnostic_normalized")
                if dn is not None and hasattr(dn, "array"):
                    sci = dn.array
            elif masks.get("diagnostic_normalized") is not None:
                sci = masks["diagnostic_normalized"]
            self.put("base_norm", scientific_to_display_gray(sci))

    def ensure_mask_layer(
        self,
        key: str,
        masks: dict[str, np.ndarray],
        *,
        centerlines: list | None = None,
        shape: tuple[int, int] | None = None,
    ) -> np.ndarray | None:
        cached = self.get(f"mask:{key}")
        if cached is not None:
            return cached
        h, w = shape or (0, 0)
        if key == "centerline":
            if not shape:
                return None
            arr = prepare_centerline_mask(centerlines or [], h, w)
            return self.put(f"mask:{key}", arr)
        m = masks.get(key)
        if m is None:
            return None
        if key == "branch_labels":
            md = prepare_overlay_mask(np.asarray(m) > 0)
        elif key in ("vertical_width_map", "horizontal_width_map"):
            md = prepare_overlay_mask(np.isfinite(m))
        else:
            md = prepare_overlay_mask(m)
        return self.put(f"mask:{key}", md)
