"""Project / global MATLAB script library with versioning metadata."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.matlab_studio.manifest import ScriptManifest, load_manifest, save_manifest
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

CATEGORIES = [
    "imported",
    "user",
    "instrument",
    "rendering",
    "feature",
    "comparison",
    "teaching",
    "templates",
    "disabled",
    "archived",
]


@dataclass
class ScriptRecord:
    script_id: str
    name: str
    author: str = ""
    institution: str = ""
    description_ru: str = ""
    description_en: str = ""
    version: str = "0.1.0"
    created_at: str = ""
    modified_at: str = ""
    matlab_release: str = ""
    octave_compatible: bool = False
    required_variables: list[str] = field(default_factory=list)
    required_toolboxes: list[str] = field(default_factory=list)
    entry_point: str = "main.m"
    source_file: str = ""
    sha256: str = ""
    license: str = ""
    citation: str = ""
    verification_status: str = "imported_unverified"
    category: str = "user"
    manifest_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScriptVersion:
    timestamp: str
    author: str
    script_sha: str
    previous_sha: str
    comment: str
    project: str
    application_version: str
    path: str


class ScriptLibrary:
    def __init__(self, root: Path | str | None = None):
        self.root = ensure_dir(root or (app_root() / "matlab_studio_library"))
        for c in CATEGORIES:
            ensure_dir(self.root / c)
        ensure_dir(self.root / "_versions")
        self.index_path = self.root / "library_index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self.index_path.exists():
            self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
        else:
            self._index = {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")

    def list_scripts(self, category: str | None = None) -> list[ScriptRecord]:
        rows = []
        for sid, payload in self._index.items():
            if category and payload.get("category") != category:
                continue
            rows.append(ScriptRecord(**{k: payload[k] for k in ScriptRecord.__dataclass_fields__ if k in payload}))
        return sorted(rows, key=lambda r: r.name.lower())

    def import_file(
        self,
        path: Path | str,
        category: str = "imported",
        author: str = "user",
        verification_status: str = "imported_unverified",
    ) -> ScriptRecord:
        src = Path(path)
        if not src.is_file():
            raise FileNotFoundError(src)
        script_id = src.stem
        dest_dir = ensure_dir(self.root / category / script_id)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        sha = sha256_file(dest)
        now = datetime.now(timezone.utc).isoformat()
        man = ScriptManifest(
            plugin_id=script_id,
            name_ru=script_id,
            name_en=script_id,
            entrypoint=src.name,
            scientific_status=verification_status,
            author=author,
        )
        man_path = save_manifest(man, dest_dir / f"{script_id}.iml-matlab.yaml")
        rec = ScriptRecord(
            script_id=script_id,
            name=script_id,
            author=author,
            created_at=now,
            modified_at=now,
            entry_point=src.name,
            source_file=str(dest),
            sha256=sha,
            verification_status=verification_status,
            category=category,
            manifest_path=str(man_path),
        )
        self._index[script_id] = rec.to_dict()
        self._save_index()
        self._store_version(rec, comment="import", previous_sha="")
        return rec

    def import_folder(self, folder: Path | str, category: str = "imported") -> list[ScriptRecord]:
        folder = Path(folder)
        out = []
        for p in sorted(folder.rglob("*.m")):
            out.append(self.import_file(p, category=category))
        return out

    def save_text(
        self,
        script_id: str,
        text: str,
        category: str = "user",
        entry_point: str = "main.m",
        comment: str = "save",
        author: str = "user",
    ) -> ScriptRecord:
        dest_dir = ensure_dir(self.root / category / script_id)
        dest = dest_dir / entry_point
        prev = ""
        if script_id in self._index:
            prev = self._index[script_id].get("sha256", "")
        dest.write_text(text, encoding="utf-8")
        sha = sha256_file(dest)
        now = datetime.now(timezone.utc).isoformat()
        rec = ScriptRecord(
            script_id=script_id,
            name=script_id,
            author=author,
            created_at=self._index.get(script_id, {}).get("created_at", now),
            modified_at=now,
            entry_point=entry_point,
            source_file=str(dest),
            sha256=sha,
            verification_status=self._index.get(script_id, {}).get(
                "verification_status", "user_tested"
            ),
            category=category,
            manifest_path=str(dest_dir / f"{script_id}.iml-matlab.yaml"),
        )
        if not Path(rec.manifest_path).exists():
            save_manifest(
                ScriptManifest(
                    plugin_id=script_id,
                    name_en=script_id,
                    name_ru=script_id,
                    entrypoint=entry_point,
                    scientific_status=rec.verification_status,
                ),
                rec.manifest_path,
            )
        self._index[script_id] = rec.to_dict()
        self._save_index()
        self._store_version(rec, comment=comment, previous_sha=prev)
        return rec

    def _store_version(self, rec: ScriptRecord, comment: str, previous_sha: str) -> None:
        from ionogram_morphology_lab import __version__

        vdir = ensure_dir(self.root / "_versions" / rec.script_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap = vdir / f"{ts}_{rec.sha256[:12]}.m"
        shutil.copy2(rec.source_file, snap)
        meta = ScriptVersion(
            timestamp=ts,
            author=rec.author,
            script_sha=rec.sha256,
            previous_sha=previous_sha,
            comment=comment,
            project="",
            application_version=__version__,
            path=str(snap),
        )
        (vdir / f"{ts}.json").write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")

    def history(self, script_id: str) -> list[dict[str, Any]]:
        vdir = self.root / "_versions" / script_id
        if not vdir.exists():
            return []
        rows = []
        for p in sorted(vdir.glob("*.json")):
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        return rows

    def restore_version(self, script_id: str, version_path: Path | str) -> ScriptRecord:
        text = Path(version_path).read_text(encoding="utf-8")
        cat = self._index.get(script_id, {}).get("category", "user")
        ep = self._index.get(script_id, {}).get("entry_point", "main.m")
        return self.save_text(script_id, text, category=cat, entry_point=ep, comment="restore")

    def diff(self, path_a: Path | str, path_b: Path | str) -> str:
        a = Path(path_a).read_text(encoding="utf-8").splitlines()
        b = Path(path_b).read_text(encoding="utf-8").splitlines()
        import difflib

        return "\n".join(difflib.unified_diff(a, b, fromfile=str(path_a), tofile=str(path_b), lineterm=""))
