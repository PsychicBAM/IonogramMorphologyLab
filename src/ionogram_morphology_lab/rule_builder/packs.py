"""Rule-pack install/export with ZIP safety limits."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

from .model import ScientificRule

MAX_ENTRIES = 500
MAX_COMPRESSED_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 80 * 1024 * 1024
MAX_SINGLE_ENTRY = 10 * 1024 * 1024


@dataclass
class PackResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    pack_id: str = ""
    rules: list[ScientificRule] = field(default_factory=list)


def installed_packs_dir() -> Path:
    return ensure_dir(app_root() / "user_library" / "rule_packs")


def _unsafe_zip_name(name: str) -> str | None:
    p = Path(name)
    if p.is_absolute():
        return "absolute path"
    parts = p.parts
    if ".." in parts:
        return "path traversal (..)"
    # Windows drive / UNC style inside archive
    if len(parts) and (":" in parts[0] or parts[0].startswith("\\\\") or parts[0].startswith("//")):
        return "drive or UNC path"
    if name.startswith("/") or name.startswith("\\"):
        return "rooted path"
    return None


def _read(directory: Path) -> PackResult:
    try:
        manifest = yaml.safe_load((directory / "pack.yaml").read_text(encoding="utf-8")) or {}
        if not manifest.get("pack_id") or not manifest.get("version"):
            return PackResult(False, ["pack.yaml requires pack_id and version"])
        rules = []
        for path in sorted((directory / "rules").glob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            rules.append(ScientificRule.from_dict(raw))
        return PackResult(True, pack_id=manifest["pack_id"], rules=rules)
    except Exception as exc:  # noqa: BLE001
        return PackResult(False, [str(exc)])


def validate_pack(path: Path | str) -> PackResult:
    return _read(Path(path))


def install_pack(path: Path | str) -> PackResult:
    result = _read(Path(path))
    if not result.ok:
        return result
    target = installed_packs_dir() / result.pack_id
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(path, target)
    return result


def enable_rule(pack_id: str, rule_id: str) -> PackResult:
    return _set_enabled(pack_id, rule_id, True)


def disable_rule(pack_id: str, rule_id: str) -> PackResult:
    return _set_enabled(pack_id, rule_id, False)


def _set_enabled(pack_id: str, rule_id: str, enabled: bool) -> PackResult:
    directory = installed_packs_dir() / pack_id
    result = _read(directory)
    if not result.ok:
        return result
    for p in (directory / "rules").glob("*.yaml"):
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if raw.get("rule_id") == rule_id:
            raw["enabled"] = enabled
            p.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
            return _read(directory)
    return PackResult(False, [f"Unknown rule: {rule_id}"], pack_id)


def export_pack(path: Path | str, archive: Path | str) -> PackResult:
    result = _read(Path(path))
    if not result.ok:
        return result
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for item in Path(path).rglob("*"):
            if item.is_file():
                z.write(item, item.relative_to(path).as_posix())
    return result


def import_pack(archive: Path | str) -> PackResult:
    archive_path = Path(archive)
    try:
        if archive_path.stat().st_size > MAX_COMPRESSED_BYTES:
            return PackResult(False, [f"Archive exceeds {MAX_COMPRESSED_BYTES} compressed bytes"])
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(archive_path) as z:
                infos = z.infolist()
                if len(infos) > MAX_ENTRIES:
                    return PackResult(False, [f"Too many entries (>{MAX_ENTRIES})"])
                total_uncomp = 0
                for info in infos:
                    reason = _unsafe_zip_name(info.filename)
                    if reason:
                        return PackResult(False, [f"Unsafe archive path ({reason}): {info.filename}"])
                    if info.file_size > MAX_SINGLE_ENTRY:
                        return PackResult(False, [f"Entry too large: {info.filename}"])
                    total_uncomp += int(info.file_size)
                    if total_uncomp > MAX_UNCOMPRESSED_BYTES:
                        return PackResult(False, ["Uncompressed size limit exceeded"])
                    # Reject symlink-like external attrs on Unix when present
                    if info.external_attr >> 16 and (info.external_attr >> 16) & 0o170000 == 0o120000:
                        return PackResult(False, [f"Symlink rejected: {info.filename}"])
                z.extractall(tmp)
            # Prefer directory that contains pack.yaml
            tmp_path = Path(tmp)
            candidates = [tmp_path] + [p for p in tmp_path.iterdir() if p.is_dir()]
            for cand in candidates:
                if (cand / "pack.yaml").exists():
                    return install_pack(cand)
            return PackResult(False, ["pack.yaml not found in archive"])
    except Exception as exc:  # noqa: BLE001
        return PackResult(False, [f"Broken pack: {exc}"])
