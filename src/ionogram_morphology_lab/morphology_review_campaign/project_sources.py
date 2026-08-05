"""Authoritative project inventory for campaign source selection (Phase 4C.3a.1)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_review_campaign.models import SourceScopeEntry
from ionogram_morphology_lab.ui.active_source_authority import (
    authoritative_active_source,
    inventory_id_for_path,
    resolve_project_source_path,
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

# Issue codes that may never appear raw in normal UI (must be localized by callers).
ISSUE_NO_SOURCES_SELECTED = "no_sources_selected"
ISSUE_PROJECT_NOT_OPEN = "project_not_open"
ISSUE_INVENTORY_LOAD_FAILED = "inventory_load_failed"


@dataclass(frozen=True)
class RegisteredProjectSource:
    """One registered project inventory MAT — never free-text invented."""

    source_path: Path
    display_name: str
    source_sha256: str
    inventory_id: str
    date_hint: str
    available: bool
    is_active: bool
    frame_count: int = 0
    reason_code: str = ""

    @property
    def short_sha(self) -> str:
        return (self.source_sha256 or "")[:12]


@dataclass
class SourceValidationResult:
    ok: bool
    sources: list[SourceScopeEntry] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)


def _date_hint(name: str) -> str:
    m = re.search(r"(20\d{2})[-_.](\d{2})[-_.](\d{2})", name or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def format_date_display(date_hint: str, *, lang: str = "en") -> str:
    """Display date; RU uses DD.MM.YYYY when ISO-like hint is present."""
    m = re.match(r"(20\d{2})-(\d{2})-(\d{2})", date_hint or "")
    if m and str(lang).startswith("ru"):
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return date_hint or "—"


def compute_file_sha256(path: Path, *, limit_mb: int | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        read = 0
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
            if limit_mb is not None and read >= limit_mb * 1024 * 1024:
                break
    return h.hexdigest().lower()


def _sha_for_path(session: Any, path: Path, *, allow_compute: bool = True) -> str:
    """Prefer session / FD cache / active store; optionally hash the file."""
    try:
        from ionogram_morphology_lab.ui.fd_frame_loader import peek_cached_source_sha

        peeked = peek_cached_source_sha(path)
        if peeked and _SHA_RE.match(peeked):
            return peeked.lower()
    except Exception:
        pass

    try:
        active = getattr(session, "active_mat", None)
        if active is not None:
            try:
                same = Path(active).resolve() == path.resolve()
            except OSError:
                same = Path(active) == path
            if same:
                if hasattr(session, "get_source_sha"):
                    sha = str(session.get_source_sha(allow_compute=allow_compute) or "")
                    if _SHA_RE.match(sha):
                        return sha.lower()
                store = getattr(session, "frame_store", None)
                if store is not None and getattr(store, "source_sha256", ""):
                    return str(store.source_sha256).lower()
    except OSError:
        pass

    cache = getattr(session, "_source_sha_cache", "") or ""
    if cache and _SHA_RE.match(str(cache)):
        try:
            active = getattr(session, "active_mat", None)
            if active is not None and Path(active).resolve() == path.resolve():
                return str(cache).lower()
        except OSError:
            pass

    if not allow_compute or not path.is_file():
        return ""
    try:
        from ionogram_morphology_lab.ui.fd_frame_loader import cached_source_sha

        sha = cached_source_sha(path, allow_compute=True)
        if _SHA_RE.match(sha or ""):
            if hasattr(session, "remember_source_sha"):
                try:
                    session.remember_source_sha(path, sha)
                except Exception:
                    pass
            return sha.lower()
    except Exception:
        pass
    try:
        sha = compute_file_sha256(path)
        if hasattr(session, "remember_source_sha"):
            try:
                session.remember_source_sha(path, sha)
            except Exception:
                pass
        return sha
    except OSError:
        return ""


def _candidate_inventory_paths(session: Any, project: Any) -> list[Path]:
    """Union of persisted source_paths and live session.selected_mats (+ active)."""
    raw: list[Any] = []
    raw.extend(list(getattr(project, "source_paths", None) or []))
    raw.extend(list(getattr(session, "selected_mats", None) or []))
    active = getattr(session, "active_mat", None)
    if active is not None:
        raw.append(active)
    out: list[Path] = []
    seen: set[str] = set()
    for sp in raw:
        path = resolve_project_source_path(project, sp)
        if path is None:
            continue
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def list_registered_project_sources(
    session: Any,
    *,
    allow_compute_sha: bool = True,
) -> list[RegisteredProjectSource]:
    """Enumerate registered project MAT sources with authoritative SHA identities.

    Uses the union of ``project.source_paths`` and live ``session.selected_mats``.
    Never invents free-text sources. Never falls back to “first MAT” as implicit
    selection — callers decide selection; active source is flagged via ``is_active``.

    Active source is always listed when present, even if SHA is still resolving
    (then ``available=False`` / ``reason_code=sha_unavailable``).
    """
    project = getattr(session, "project", None)
    if project is None:
        return []
    auth = authoritative_active_source(session, force_rebuild=False)
    # Ensure active SHA is available when the store already knows it / compute allowed.
    if allow_compute_sha and auth.is_active and not auth.source_sha256:
        if hasattr(session, "get_source_sha"):
            try:
                session.get_source_sha(allow_compute=True)
                auth = authoritative_active_source(session, force_rebuild=False)
            except Exception:
                pass

    out: list[RegisteredProjectSource] = []
    seen: set[str] = set()
    for path in _candidate_inventory_paths(session, project):
        try:
            key = str(path.resolve()).lower()
        except OSError:
            key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        available = bool(path.is_file())
        sha = _sha_for_path(session, path, allow_compute=allow_compute_sha) if available else ""
        inv = inventory_id_for_path(path, sha)
        is_active = False
        if auth.is_active and auth.source_path is not None and path.is_file():
            try:
                is_active = (
                    (auth.source_sha256 and sha and auth.source_sha256.lower() == sha)
                    or str(auth.source_path.resolve()) == str(path.resolve())
                )
            except OSError:
                is_active = str(auth.source_path) == str(path)
        reason = ""
        if not available:
            reason = "source_missing"
        elif not _SHA_RE.match(sha):
            reason = "sha_unavailable"
            available = False
        out.append(
            RegisteredProjectSource(
                source_path=path,
                display_name=path.name,
                source_sha256=sha,
                inventory_id=inv,
                date_hint=_date_hint(path.name),
                available=available,
                is_active=is_active,
                frame_count=auth.frame_count if is_active else 0,
                reason_code=reason,
            )
        )

    # Ensure active source appears even if path resolution missed it.
    if auth.is_active and auth.source_path is not None:
        try:
            akey = str(auth.source_path.resolve()).lower()
        except OSError:
            akey = str(auth.source_path).lower()
        if akey not in seen:
            sha = (auth.source_sha256 or "").lower()
            if not _SHA_RE.match(sha) and allow_compute_sha:
                sha = _sha_for_path(session, Path(auth.source_path), allow_compute=True)
            avail = bool(auth.available and _SHA_RE.match(sha))
            reason = ""
            if not Path(auth.source_path).is_file():
                reason = "source_missing"
                avail = False
            elif not _SHA_RE.match(sha):
                reason = "sha_unavailable"
                avail = False
            out.insert(
                0,
                RegisteredProjectSource(
                    source_path=Path(auth.source_path),
                    display_name=auth.display_name or Path(auth.source_path).name,
                    source_sha256=sha if _SHA_RE.match(sha) else "",
                    inventory_id=auth.inventory_id or inventory_id_for_path(auth.source_path, sha),
                    date_hint=auth.date_hint or _date_hint(auth.display_name),
                    available=avail,
                    is_active=True,
                    frame_count=auth.frame_count,
                    reason_code=reason or auth.reason_code or "",
                ),
            )
    return out


def find_path_by_sha(session: Any, source_sha256: str) -> Path | None:
    sha = (source_sha256 or "").lower()
    if not _SHA_RE.match(sha):
        return None
    for reg in list_registered_project_sources(session):
        if reg.source_sha256 == sha and reg.available:
            return reg.source_path
    return None


def validate_selected_sources(
    session: Any,
    selected_shas: list[str],
    *,
    allow_unavailable: bool = False,
) -> SourceValidationResult:
    """Validate selected inventory SHAs before preview/create."""
    try:
        inventory = {r.source_sha256: r for r in list_registered_project_sources(session)}
    except Exception:
        result = SourceValidationResult(ok=False)
        result.issues.append(ISSUE_INVENTORY_LOAD_FAILED)
        return result
    result = SourceValidationResult(ok=True)
    if getattr(session, "project", None) is None:
        result.ok = False
        result.issues.append(ISSUE_PROJECT_NOT_OPEN)
        return result
    # Drop empty SHA selections (unchecked / unavailable rows)
    selected_shas = [s for s in selected_shas if s]
    if not selected_shas:
        result.ok = False
        result.issues.append(ISSUE_NO_SOURCES_SELECTED)
        return result
    for raw in selected_shas:
        sha = (raw or "").lower()
        if not _SHA_RE.match(sha):
            result.ok = False
            result.issues.append(f"invalid_sha:{sha[:16]}")
            continue
        reg = inventory.get(sha)
        if reg is None:
            result.ok = False
            result.issues.append(f"sha_not_in_inventory:{sha[:12]}")
            continue
        if not reg.available and not allow_unavailable:
            result.ok = False
            result.issues.append(f"source_unavailable:{reg.display_name}")
            continue
        if not reg.inventory_id:
            result.ok = False
            result.issues.append(f"missing_inventory_id:{sha[:12]}")
            continue
        result.sources.append(
            SourceScopeEntry(
                source_sha256=reg.source_sha256,
                source_display_name=reg.display_name,
                source_inventory_id=reg.inventory_id,
                date_hint=reg.date_hint,
                available=reg.available,
            )
        )
    result.ok = not result.issues
    return result


def reject_free_text_source_identity(
    display_name: str, source_sha256: str, session: Any
) -> list[str]:
    """Guard: arbitrary display/SHA pairs cannot invent inventory identity."""
    issues: list[str] = []
    sha = (source_sha256 or "").lower()
    if not _SHA_RE.match(sha):
        issues.append("sha_not_hex64")
        return issues
    inventory = list_registered_project_sources(session)
    by_sha = {r.source_sha256: r for r in inventory}
    reg = by_sha.get(sha)
    if reg is None:
        issues.append("sha_not_registered")
        return issues
    name = (display_name or "").strip()
    if name and name != reg.display_name and name.lower() != reg.display_name.lower():
        issues.append("display_name_not_registered_source")
    return issues


def detect_invalid_campaign_sources(
    session: Any, source_scope: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Find campaign source_scope rows that do not match project inventory."""
    inventory = {r.source_sha256: r for r in list_registered_project_sources(session)}
    bad: list[dict[str, Any]] = []
    for row in source_scope or []:
        sha = str(row.get("source_sha256") or "").lower()
        name = str(row.get("source_display_name") or "")
        if not _SHA_RE.match(sha) or sha not in inventory:
            bad.append(
                {
                    "source_sha256": sha,
                    "source_display_name": name,
                    "reason": "not_in_inventory",
                    "candidates": [
                        {
                            "display_name": r.display_name,
                            "short_sha": r.short_sha,
                            "source_sha256": r.source_sha256,
                            "inventory_id": r.inventory_id,
                        }
                        for r in inventory.values()
                        if r.available
                    ],
                }
            )
    return bad


def localize_validation_issue(code: str, *, lang: str = "en") -> str:
    """Map internal validation codes to owner-facing RU/EN strings."""
    ru = str(lang).startswith("ru")
    base = (code or "").split(":", 1)[0]
    mapping_ru = {
        ISSUE_NO_SOURCES_SELECTED: "Выберите хотя бы один доступный источник.",
        ISSUE_PROJECT_NOT_OPEN: "Сначала откройте проект.",
        ISSUE_INVENTORY_LOAD_FAILED: "Не удалось загрузить список источников проекта.",
        "invalid_sha": "Некорректный SHA источника.",
        "sha_not_in_inventory": "SHA источника отсутствует в инвентаре проекта.",
        "source_unavailable": "Выбранный источник недоступен.",
        "missing_inventory_id": "У источника отсутствует ID инвентаря.",
        "source_missing": "Файл источника не найден.",
        "sha_unavailable": "SHA источника ещё не вычислен.",
    }
    mapping_en = {
        ISSUE_NO_SOURCES_SELECTED: "Select at least one available source.",
        ISSUE_PROJECT_NOT_OPEN: "Open a project first.",
        ISSUE_INVENTORY_LOAD_FAILED: "Failed to load the project source inventory.",
        "invalid_sha": "Invalid source SHA.",
        "sha_not_in_inventory": "Source SHA is not in the project inventory.",
        "source_unavailable": "Selected source is unavailable.",
        "missing_inventory_id": "Source is missing an inventory ID.",
        "source_missing": "Source file not found.",
        "sha_unavailable": "Source SHA is not yet available.",
    }
    table = mapping_ru if ru else mapping_en
    if base in table:
        detail = code.split(":", 1)[1] if ":" in code else ""
        if detail and base in ("source_unavailable", "sha_not_in_inventory", "invalid_sha", "missing_inventory_id"):
            return f"{table[base]} ({detail})"
        return table[base]
    # Never return a known raw code unchanged when we can avoid it
    if code == ISSUE_NO_SOURCES_SELECTED:
        return table[ISSUE_NO_SOURCES_SELECTED]
    return code


def localize_campaign_state(state: str, *, lang: str = "en") -> str:
    """Localized campaign state for UI; canonical codes stay in storage."""
    ru = str(lang).startswith("ru")
    key = (state or "").strip().lower()
    ru_map = {
        "ready": "Готова",
        "draft": "Черновик",
        "active": "Активна",
        "paused": "Приостановлена",
        "completed": "Завершена",
        "archived": "Архивная",
    }
    en_map = {
        "ready": "Ready",
        "draft": "Draft",
        "active": "Active",
        "paused": "Paused",
        "completed": "Completed",
        "archived": "Archived",
    }
    table = ru_map if ru else en_map
    return table.get(key, state)
