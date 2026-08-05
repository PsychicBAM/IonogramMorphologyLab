"""Packaged EXE / runtime build identity for Technical Details (Phase 4B.2i)."""

from __future__ import annotations

import hashlib
import platform
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab import __version__
from ionogram_morphology_lab.features.v2.types import FEATURE_VERSION
from ionogram_morphology_lab.rendering.display_transform import TRANSFORM_VERSION

_SHA_LOCK = threading.Lock()
_SHA_CACHE: dict[str, tuple[int, int, str]] = {}  # path -> (mtime_ns, size, sha)


def _sha256_file_cached(path: Path) -> str:
    """Hash EXE once per path+mtime+size — never on every language/page switch."""
    try:
        st = path.stat()
        meta = (int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))), int(st.st_size))
    except OSError:
        return ""
    key = str(path.resolve())
    with _SHA_LOCK:
        hit = _SHA_CACHE.get(key)
        if hit is not None and hit[0] == meta[0] and hit[1] == meta[1]:
            return hit[2]
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    sha = h.hexdigest().upper()
    with _SHA_LOCK:
        _SHA_CACHE[key] = (meta[0], meta[1], sha)
    return sha


def executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve() if sys.argv else Path(sys.executable).resolve()


def collect_build_identity(
    *,
    cache_root: Path | str | None = None,
    workspace_root: Path | str | None = None,
    active_project_path: Path | str | None = None,
    compute_sha: bool = True,
    cache_root_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ionogram_morphology_lab.morphology_candidate.types import (
        CANDIDATE_CACHE_SCHEMA_VERSION,
        CANDIDATE_ENGINE_VERSION,
        EVIDENCE_LEDGER_SCHEMA_VERSION,
    )
    from ionogram_morphology_lab.morphology_review_campaign.constants import (
        CAMPAIGN_SCHEMA_VERSION,
    )
    from ionogram_morphology_lab.morphology_review_corpus.constants import (
        ADJUDICATION_SCHEMA_VERSION,
        CORPUS_INTEGRITY_CONTRACT_VERSION,
        PROTOCOL_SCHEMA_VERSION,
        REVIEW_CORPUS_SCHEMA_VERSION,
        REVIEW_RECORD_SCHEMA_VERSION,
    )
    from ionogram_morphology_lab.ui.sequence_frame_state import (
        FD_LAYOUT_SCHEMA_VERSION,
        SEQUENCE_STATE_CONTRACT_VERSION,
    )

    exe = executable_path()
    sha = ""
    build_date = ""
    try:
        if exe.is_file():
            if compute_sha:
                sha = _sha256_file_cached(exe)
            else:
                # Peek cache only — never block UI for first paint
                key = str(exe.resolve())
                with _SHA_LOCK:
                    hit = _SHA_CACHE.get(key)
                    sha = hit[2] if hit else "(pending)"
            build_date = datetime.fromtimestamp(exe.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        pass
    info = dict(cache_root_info or {})
    return {
        "executable_path": str(exe),
        "executable_sha256": sha,
        "build_date": build_date,
        "application_version": __version__,
        "python_runtime": sys.version.split()[0],
        "python_full": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "feature_version": FEATURE_VERSION,
        "display_transform_version": TRANSFORM_VERSION,
        # Phase / packaging identity — Phase 4C.2 expert morphology review corpus
        "release_phase": "4C.4a",
        "candidate_engine_version": CANDIDATE_ENGINE_VERSION,
        "candidate_cache_schema_version": CANDIDATE_CACHE_SCHEMA_VERSION,
        "evidence_ledger_schema_version": EVIDENCE_LEDGER_SCHEMA_VERSION,
        "fd_layout_schema_version": FD_LAYOUT_SCHEMA_VERSION,
        "sequence_state_contract_version": SEQUENCE_STATE_CONTRACT_VERSION,
        "review_corpus_schema_version": REVIEW_CORPUS_SCHEMA_VERSION,
        "review_record_schema_version": REVIEW_RECORD_SCHEMA_VERSION,
        "adjudication_schema_version": ADJUDICATION_SCHEMA_VERSION,
        "protocol_schema_version": PROTOCOL_SCHEMA_VERSION,
        "corpus_integrity_contract_version": CORPUS_INTEGRITY_CONTRACT_VERSION,
        "campaign_schema_version": CAMPAIGN_SCHEMA_VERSION,
        "shadow_only": True,
        "scientifically_validated": False,
        "cache_root": str(cache_root or info.get("resolved_cache_root") or ""),
        "resolved_cache_root": info.get("resolved_cache_root", str(cache_root or "")),
        "cache_resolution_source": info.get("cache_resolution_source", ""),
        "rejected_cache_path": info.get("rejected_cache_path", ""),
        "production_mode": info.get("production_mode"),
        "cache_root_warning": info.get("cache_root_warning", ""),
        "workspace_root": str(workspace_root or ""),
        "active_project_path": str(active_project_path or ""),
    }


def warm_executable_sha_async() -> None:
    """Background hash so Technical Details is instant later."""

    def _run() -> None:
        try:
            p = executable_path()
            if p.is_file():
                _sha256_file_cached(p)
        except Exception:
            pass

    threading.Thread(target=_run, name="iml-exe-sha", daemon=True).start()


def format_build_identity(identity: dict[str, Any], language: str = "en") -> str:
    ru = language == "ru"
    lines = [
        "=== " + ("Идентификация сборки" if ru else "Build Identity") + " ===",
        f"{'Путь EXE' if ru else 'Executable'}: {identity.get('executable_path', '')}",
        f"SHA-256: {identity.get('executable_sha256', '')}",
        f"{'Дата сборки' if ru else 'Build date'}: {identity.get('build_date', '')}",
        f"{'Фаза' if ru else 'Phase'}: {identity.get('release_phase', '')}",
        f"{'Версия приложения' if ru else 'Application version'}: {identity.get('application_version', '')}",
        f"Python: {identity.get('python_runtime', '')}",
        f"{'Версия признаков' if ru else 'Feature version'}: {identity.get('feature_version', '')}",
        f"{'Движок кандидата' if ru else 'Candidate engine'}: {identity.get('candidate_engine_version', '')}",
        f"{'Схема кэша кандидата' if ru else 'Candidate cache schema'}: {identity.get('candidate_cache_schema_version', '')}",
        f"{'Схема evidence ledger' if ru else 'Evidence ledger schema'}: {identity.get('evidence_ledger_schema_version', '')}",
        f"{'Схема макета Diagnostics' if ru else 'Diagnostics layout schema'}: {identity.get('fd_layout_schema_version', '')}",
        f"{'Контракт состояний последовательности' if ru else 'Sequence-state contract'}: {identity.get('sequence_state_contract_version', '')}",
        f"{'Схема корпуса рецензий' if ru else 'Review corpus schema'}: {identity.get('review_corpus_schema_version', '')}",
        f"{'Схема записи рецензии' if ru else 'Review record schema'}: {identity.get('review_record_schema_version', '')}",
        f"{'Схема арбитража' if ru else 'Adjudication schema'}: {identity.get('adjudication_schema_version', '')}",
        f"{'Схема протокола' if ru else 'Protocol schema'}: {identity.get('protocol_schema_version', '')}",
        f"{'Контракт целостности корпуса' if ru else 'Corpus integrity contract'}: {identity.get('corpus_integrity_contract_version', '')}",
        f"{'Только shadow' if ru else 'Shadow-only'}: {identity.get('shadow_only', True)}",
        f"{'Display transform'}: {identity.get('display_transform_version', '')}",
        f"{'Корень кэша' if ru else 'Cache root'}: {identity.get('resolved_cache_root') or identity.get('cache_root', '')}",
        f"{'Источник пути кэша' if ru else 'Cache resolution source'}: {identity.get('cache_resolution_source', '')}",
        f"{'Отклонённый путь' if ru else 'Rejected path'}: {identity.get('rejected_cache_path', '') or '—'}",
        f"{'Режим' if ru else 'Mode'}: {'production' if identity.get('production_mode') else 'dev/test'}",
        f"{'Предупреждение кэша' if ru else 'Cache warning'}: {identity.get('cache_root_warning', '') or '—'}",
        f"{'Рабочая область' if ru else 'Workspace root'}: {identity.get('workspace_root', '')}",
        f"{'Активный проект' if ru else 'Active project'}: {identity.get('active_project_path', '')}",
        f"Frozen: {identity.get('frozen', False)}",
        f"Platform: {identity.get('platform', '')}",
    ]
    return "\n".join(lines)
