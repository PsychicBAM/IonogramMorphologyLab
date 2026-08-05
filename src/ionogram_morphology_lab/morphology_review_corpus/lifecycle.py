"""Cohort lifecycle helpers: legacy detection, workspace archive visibility (4C.2a.1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_review_corpus.constants import CORPORA_DIRNAME
from ionogram_morphology_lab.morphology_review_corpus.models import CohortManifest, ReviewItem

_PILOT_FRAME_RE = re.compile(r"^pilot_frame_\d+", re.IGNORECASE)
# Legacy 4C.2 synthetic SHA pattern: zero-padded hex of small integers
_FAKE_SHA_RE = re.compile(r"^0{48,}[0-9a-f]{1,16}$")

WORKSPACE_FILENAME = "_workspace.json"


class CorpusLifecycleError(RuntimeError):
    """Domain error with stable code for RU/EN UI mapping."""

    def __init__(self, code: str, message_en: str = ""):
        self.code = code
        super().__init__(message_en or code)


def lifecycle_state(manifest: CohortManifest) -> str:
    if getattr(manifest, "archived", False):
        # archived flag on manifest is legacy; prefer workspace
        pass
    if manifest.frozen:
        return "frozen"
    return "draft"


def is_legacy_synthetic_item(item: ReviewItem | dict[str, Any]) -> bool:
    if isinstance(item, ReviewItem):
        name = item.source_display_name or ""
        sha = (item.source_sha256 or "").lower()
        inv = item.source_inventory_id or ""
        reason = item.inclusion_reason or ""
    else:
        name = str(item.get("source_display_name") or "")
        sha = str(item.get("source_sha256") or "").lower()
        inv = str(item.get("source_inventory_id") or "")
        reason = str(item.get("inclusion_reason") or "")
    if _PILOT_FRAME_RE.match(name.strip()):
        return True
    if "synthetic" in reason.lower() or "developer" in reason.lower():
        return True
    if inv.startswith("pilot_inv_"):
        return True
    # Padded zero SHA alone is not enough (unit fixtures use it); require weak inventory
    if sha and _FAKE_SHA_RE.match(sha) and (not inv or inv.startswith("pilot_inv_")):
        return True
    return False


def is_legacy_synthetic_cohort(
    manifest: CohortManifest,
    items: list[ReviewItem] | list[dict[str, Any]],
) -> bool:
    """Detect old Phase 4C.2 placeholder corpora — not every pilot evaluation set."""
    des = (manifest.designation_en or "") + " " + (manifest.designation_ru or "")
    if "synthetic developer" in des.lower() or "developer-only synthetic" in des.lower():
        return True
    if not items:
        return False
    legacy_n = sum(1 for it in items if is_legacy_synthetic_item(it))
    # Majority of items look like pilot_frame placeholders
    return legacy_n >= max(1, (len(items) + 1) // 2) and legacy_n == len(items)


def workspace_path(project_root: Path | str) -> Path:
    return Path(project_root) / CORPORA_DIRNAME / WORKSPACE_FILENAME


def load_workspace(project_root: Path | str) -> dict[str, Any]:
    p = workspace_path(project_root)
    if not p.is_file():
        return {
            "archived_cohort_ids": [],
            "selected_cohort_id": "",
            "show_archived": False,
            "show_legacy": False,
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "archived_cohort_ids": [],
            "selected_cohort_id": "",
            "show_archived": False,
            "show_legacy": False,
        }
    if not isinstance(data, dict):
        return {
            "archived_cohort_ids": [],
            "selected_cohort_id": "",
            "show_archived": False,
            "show_legacy": False,
        }
    data.setdefault("archived_cohort_ids", [])
    data.setdefault("selected_cohort_id", "")
    data.setdefault("show_archived", False)
    data.setdefault("show_legacy", False)
    return data


def save_workspace(project_root: Path | str, data: dict[str, Any]) -> None:
    p = workspace_path(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "archived_cohort_ids": list(data.get("archived_cohort_ids") or []),
        "selected_cohort_id": str(data.get("selected_cohort_id") or ""),
        "show_archived": bool(data.get("show_archived")),
        "show_legacy": bool(data.get("show_legacy")),
    }
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_archived(project_root: Path | str, cohort_id: str, archived: bool) -> dict[str, Any]:
    ws = load_workspace(project_root)
    ids = set(ws.get("archived_cohort_ids") or [])
    if archived:
        ids.add(cohort_id)
    else:
        ids.discard(cohort_id)
    ws["archived_cohort_ids"] = sorted(ids)
    save_workspace(project_root, ws)
    return ws


def is_archived(project_root: Path | str, cohort_id: str) -> bool:
    ws = load_workspace(project_root)
    return cohort_id in set(ws.get("archived_cohort_ids") or [])


def set_selected_cohort(project_root: Path | str, cohort_id: str) -> None:
    ws = load_workspace(project_root)
    ws["selected_cohort_id"] = cohort_id or ""
    save_workspace(project_root, ws)


def get_selected_cohort(project_root: Path | str) -> str:
    return str(load_workspace(project_root).get("selected_cohort_id") or "")


def set_show_flags(
    project_root: Path | str,
    *,
    show_archived: bool | None = None,
    show_legacy: bool | None = None,
) -> dict[str, Any]:
    ws = load_workspace(project_root)
    if show_archived is not None:
        ws["show_archived"] = bool(show_archived)
    if show_legacy is not None:
        ws["show_legacy"] = bool(show_legacy)
    save_workspace(project_root, ws)
    return ws
