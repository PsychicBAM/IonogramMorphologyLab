#!/usr/bin/env python3
"""Write BUILD_MANIFEST.json for the portable dist tree (not for Git tracking)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "IonogramMorphologyLab"
REQUIRED_REL = [
    "IonogramMorphologyLab.exe",
    "_internal/ionogram_morphology_lab/i18n/en.json",
    "_internal/ionogram_morphology_lab/i18n/ru.json",
    "_internal/docs/USER_GUIDE_EN.md",
    "_internal/matlab_builtin",
    "_internal/rule_packs",
    "_internal/knowledge_base",
    "_internal/synthetic_data",
    "_internal/config",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not DIST.exists():
        print("dist missing", file=sys.stderr)
        return 1
    resources = {}
    missing = []
    for rel in REQUIRED_REL:
        p = DIST / rel
        if not p.exists():
            missing.append(rel)
            continue
        if p.is_file():
            resources[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
        else:
            # directory: hash file list + count
            files = sorted(x for x in p.rglob("*") if x.is_file())
            h = hashlib.sha256()
            for f in files:
                h.update(f.relative_to(p).as_posix().encode())
                h.update(sha256(f).encode())
            resources[rel] = {"type": "dir", "file_count": len(files), "tree_sha256": h.hexdigest()}
    exe = DIST / "IonogramMorphologyLab.exe"
    manifest = {
        "product": "Ionogram Morphology Lab",
        "version": "1.1.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "exe_sha256": sha256(exe) if exe.exists() else None,
        "exe_bytes": exe.stat().st_size if exe.exists() else None,
        "resources": resources,
        "missing_required": missing,
        "note": "Portable build evidence. dist/ is gitignored unless release policy tracks binaries separately.",
    }
    out = DIST / "BUILD_MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(out)
    print("missing:", missing)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
