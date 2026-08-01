"""Optional Protected Scientific Study mode — disabled by default.

Ordinary user-selected MAT files are allowed whenever the OS permits read access.
Protection applies only when a project/user enables Protected Scientific Study
and configures paths/hashes/dates/project IDs manually.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


class ForbiddenPathError(PermissionError):
    """Raised when a path is protected by an enabled Protected Scientific Study."""


@dataclass
class ProtectedStudyConfig:
    """Per-project / user-configurable protection. Never auto-reads secret mappings."""

    enabled: bool = False
    protected_path_fragments: list[str] = field(default_factory=list)
    protected_absolute_paths: list[str] = field(default_factory=list)
    protected_file_hashes: list[str] = field(default_factory=list)
    protected_dates: list[str] = field(default_factory=list)
    protected_project_ids: list[str] = field(default_factory=list)
    display_name: str = "Protected Scientific Study"
    note_en: str = (
        "Protection is user-configured. The application does not auto-import "
        "secret study mappings from other projects."
    )
    note_ru: str = (
        "Защита настроена пользователем. Приложение не импортирует автоматически "
        "секретные соответствия из других проектов."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ProtectedStudyConfig":
        if not data:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> "ProtectedStudyConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


@dataclass
class PathBlocklist:
    """Optional protection gate. Disabled by default — allows all readable paths."""

    config: ProtectedStudyConfig = field(default_factory=ProtectedStudyConfig)

    @property
    def enabled(self) -> bool:
        return bool(self.config.enabled)

    def is_blocked(self, path: Path | str, file_sha256: str | None = None) -> bool:
        if not self.config.enabled:
            return False
        try:
            resolved = str(Path(path).resolve()).replace("/", "\\").lower()
        except OSError:
            resolved = str(path).replace("/", "\\").lower()
        for frag in self.config.protected_path_fragments:
            if frag.replace("/", "\\").lower() in resolved:
                return True
        for abs_p in self.config.protected_absolute_paths:
            if abs_p.replace("/", "\\").lower() in resolved:
                return True
        if file_sha256 and file_sha256.lower() in {h.lower() for h in self.config.protected_file_hashes}:
            return True
        # date token in filename
        name = Path(path).name
        for d in self.config.protected_dates:
            if d and d in name:
                return True
        return False

    def assert_allowed(self, path: Path | str, file_sha256: str | None = None) -> Path:
        p = Path(path)
        if self.is_blocked(p, file_sha256=file_sha256):
            raise ForbiddenPathError(
                "Protected Scientific Study is enabled for this project and blocks "
                "the selected path. Disable the mode or edit the protection list "
                "in Settings → Privacy and Security / Project protection."
            )
        return p


_ACTIVE: PathBlocklist | None = None


def default_blocklist() -> PathBlocklist:
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = PathBlocklist(ProtectedStudyConfig(enabled=False))
    return _ACTIVE


def set_active_protection(config: ProtectedStudyConfig) -> PathBlocklist:
    global _ACTIVE
    _ACTIVE = PathBlocklist(config)
    return _ACTIVE


def reset_protection() -> PathBlocklist:
    """Reset to disabled default (for tests / new sessions)."""
    return set_active_protection(ProtectedStudyConfig(enabled=False))
