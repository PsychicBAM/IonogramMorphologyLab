"""Production vs test cache-root resolution (Phase 4B.2j).

Frozen packaged EXE must never use pytest fixture temp directories that may have
leaked into ``user_settings.json`` (including bundled config copies).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_PYTEST_MARKERS = (
    "pytest-of-",
    "pytest-",
    "test_cache_",
    "\\pytest\\",
    "/pytest/",
    "pytest_cache",
)


@dataclass(frozen=True)
class CacheRootResolution:
    path: Path
    resolution_source: str
    rejected_path: str = ""
    production_mode: bool = True
    warning: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "resolved_cache_root": str(self.path),
            "cache_resolution_source": self.resolution_source,
            "rejected_cache_path": self.rejected_path,
            "production_mode": self.production_mode,
            "cache_root_warning": self.warning,
        }


def is_pytest_environment() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    if os.environ.get("IML_ALLOW_TEST_CACHE", "").strip().lower() in ("1", "true", "yes"):
        return True
    # Heuristic: running under pytest collector
    return "pytest" in sys.modules and not getattr(sys, "frozen", False)


def is_frozen_production() -> bool:
    return bool(getattr(sys, "frozen", False)) and not is_pytest_environment()


def looks_like_test_cache_path(path: Path | str | None) -> bool:
    if not path:
        return False
    s = str(path).replace("/", "\\").lower()
    if "pytest-of-" in s:
        return True
    if "\\pytest-" in s or "/pytest-" in s:
        return True
    if "test_cache_" in s:
        return True
    # Common pytest tmp roots
    if "\\pytest\\" in s or "appdata\\local\\temp\\pytest" in s:
        return True
    return False


def production_cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "IonogramMorphologyLab" / "cache"


def production_settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "IonogramMorphologyLab" / "user_settings.json"


def resolve_cache_root(
    configured: Path | str | None = None,
    *,
    force_frozen: bool | None = None,
) -> CacheRootResolution:
    """Resolve a safe cache root.

    ``force_frozen`` overrides detection for unit tests of frozen policy.
    """
    frozen = is_frozen_production() if force_frozen is None else bool(force_frozen)
    configured_s = str(configured or "").strip()
    configured_p = Path(configured_s) if configured_s else None

    if frozen:
        if configured_p is not None and looks_like_test_cache_path(configured_p):
            prod = production_cache_root()
            prod.mkdir(parents=True, exist_ok=True)
            return CacheRootResolution(
                path=prod,
                resolution_source="production_fallback_rejected_test_path",
                rejected_path=str(configured_p),
                production_mode=True,
                warning=(
                    "Rejected test/pytest cache path in frozen EXE; "
                    f"using production cache: {prod}"
                ),
            )
        if configured_p is not None and configured_s:
            # Allow explicit user-chosen non-test path
            if not looks_like_test_cache_path(configured_p):
                configured_p.mkdir(parents=True, exist_ok=True)
                return CacheRootResolution(
                    path=configured_p.resolve(),
                    resolution_source="user_settings_cache_location",
                    production_mode=True,
                )
        prod = production_cache_root()
        prod.mkdir(parents=True, exist_ok=True)
        return CacheRootResolution(
            path=prod.resolve(),
            resolution_source="localappdata_default",
            production_mode=True,
        )

    # Dev / pytest: honour configured path (including pytest tmp)
    if configured_p is not None and configured_s:
        configured_p.mkdir(parents=True, exist_ok=True)
        return CacheRootResolution(
            path=configured_p.resolve(),
            resolution_source="dev_or_test_configured",
            production_mode=False,
        )
    from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

    default = ensure_dir(app_root() / "workspaces" / "_cache")
    return CacheRootResolution(
        path=default.resolve(),
        resolution_source="dev_workspaces_cache",
        production_mode=False,
    )
