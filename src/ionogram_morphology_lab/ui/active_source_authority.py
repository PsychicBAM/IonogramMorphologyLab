"""Authoritative active-source identity for all scientific consumers (Phase 4C.2a).

Batch, Viewer, Diagnostics, Sequence, and Expert Review Corpus must resolve the
active MAT through this contract — never by silently picking the first inventory
entry.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.ui.active_source import (
    ActiveSourceSnapshot,
    SourceStatus,
    paths_equal,
    resolve_active_source,
)

_LOG = logging.getLogger("iml.active_source")


@dataclass(frozen=True)
class AuthoritativeActiveSource:
    """Canonical active-source identity shared by all consumers."""

    project_open: bool
    inventory_id: str
    source_path: Path | None
    display_name: str
    source_sha256: str
    source_generation: int
    activation_revision: int
    available: bool
    is_active: bool
    status: str
    reason_code: str
    date_hint: str = ""
    frame_count: int = 0

    @property
    def short_sha(self) -> str:
        return (self.source_sha256 or "")[:12]


def resolve_project_source_path(
    project: Any | None, path_str: str | Path | None
) -> Path | None:
    """Resolve a persisted source path from project root when needed."""
    if path_str is None or str(path_str).strip() == "":
        return None
    p = Path(path_str)
    try:
        if p.is_file():
            return p
    except OSError:
        pass
    root = getattr(project, "root", None) or getattr(project, "path", None)
    if root is not None:
        # Relative to project root
        cand = Path(root) / p
        try:
            if cand.is_file():
                return cand
        except OSError:
            pass
        # Basename match under project (portability)
        try:
            by_name = Path(root) / p.name
            if by_name.is_file():
                return by_name
        except OSError:
            pass
    return p


def inventory_id_for_path(path: Path | str | None, sha: str = "") -> str:
    if sha and len(sha) >= 12:
        return f"inv_{sha[:12].lower()}"
    if path is None:
        return ""
    key = os.path.normcase(os.path.normpath(str(path)))
    digest = abs(hash(key)) % (10**10)
    return f"inv_{Path(path).stem}_{digest:010d}"


def authoritative_active_source(session: Any, *, force_rebuild: bool = False) -> AuthoritativeActiveSource:
    """Single resolver used by Viewer / Batch / FD / Corpus."""
    snap = resolve_active_source(session, force_rebuild=force_rebuild)
    rev = int(getattr(session, "_snapshot_generation", 0) or snap.snapshot_generation or 0)
    active = getattr(session, "active_mat", None)
    project = getattr(session, "project", None)
    resolved = resolve_project_source_path(project, active) if active is not None else None
    available = bool(resolved is not None and resolved.is_file() and snap.is_active)
    sha = str(snap.source_sha256 or "")
    if not sha and hasattr(session, "get_source_sha"):
        try:
            sha = str(session.get_source_sha(allow_compute=False) or "")
        except Exception:
            sha = ""
    path = resolved if resolved is not None else (Path(active) if active is not None else None)
    if snap.status == SourceStatus.MISSING or (path is not None and not path.is_file()):
        available = False
    date_hint = _date_hint_from_name(snap.mat_filename or (path.name if path else ""))
    auth = AuthoritativeActiveSource(
        project_open=bool(project is not None),
        inventory_id=inventory_id_for_path(path, sha),
        source_path=path if snap.is_active else None,
        display_name=snap.mat_filename or (path.name if path else ""),
        source_sha256=sha,
        source_generation=int(snap.source_mtime_ns or 0),
        activation_revision=rev,
        available=available and snap.is_active,
        is_active=bool(snap.is_active and path is not None),
        status=snap.status.value,
        reason_code=snap.reason_code or "",
        date_hint=date_hint,
        frame_count=int(snap.frame_count or 0),
    )
    _LOG.debug(
        "active_source resolve id=%s sha=%s path=%s rev=%s available=%s status=%s",
        auth.inventory_id,
        auth.short_sha,
        auth.source_path,
        auth.activation_revision,
        auth.available,
        auth.status,
    )
    return auth


def active_source_label(auth: AuthoritativeActiveSource, lang: str = "en") -> str:
    """RU/EN compact active-source label."""
    if not auth.project_open:
        return "Проект не открыт" if lang == "ru" else "No project open"
    if not auth.is_active or not auth.display_name:
        return (
            "Активный MAT-источник не выбран."
            if lang == "ru"
            else "No active MAT source selected."
        )
    date = (
        format_active_source_date_ru(auth.display_name)
        if lang == "ru"
        else (auth.date_hint or auth.display_name)
    )
    if auth.available:
        avail_ru, avail_en = "доступен", "available"
    else:
        avail_ru, avail_en = "недоступен", "unavailable"
    if lang == "ru":
        return f"Активный источник: {date} — {avail_ru}"
    return f"Active source: {date} — {avail_en}"


def batch_mats_from_active(session: Any) -> tuple[list[Path], str]:
    """Return mats for Batch Analysis — active source only.

    Returns (mats, error_code). error_code empty on success.
    Never falls back to inventory registration order.
    """
    auth = authoritative_active_source(session)
    if not auth.project_open:
        return [], "project_not_open"
    if not auth.is_active or auth.source_path is None:
        inv = list(getattr(session, "selected_mats", []) or [])
        if len(inv) > 1:
            return [], "active_source_required"
        if len(inv) == 1 and Path(inv[0]).is_file() and getattr(session, "active_mat", None) is None:
            return [], "active_source_required"
        return [], "mat_not_active"
    if not auth.available:
        return [], "active_source_unavailable"
    return [Path(auth.source_path)], ""


def freeze_batch_source_snapshot(session: Any) -> dict[str, Any]:
    """Freeze active source identity for a running batch (no mid-run switch)."""
    auth = authoritative_active_source(session)
    return {
        "inventory_id": auth.inventory_id,
        "display_name": auth.display_name,
        "source_path": str(auth.source_path) if auth.source_path else "",
        "source_sha256": auth.source_sha256,
        "activation_revision": auth.activation_revision,
        "source_generation": auth.source_generation,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
    }


def _date_hint_from_name(name: str) -> str:
    """Best-effort ISO date from filename (e.g. Amp_all_2014-10-15.mat)."""
    import re

    m = re.search(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return name


def format_active_source_date_ru(name: str) -> str:
    """Prefer DD.MM.YYYY when ISO date is embedded in the name."""
    import re

    m = re.search(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})", name)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return name
