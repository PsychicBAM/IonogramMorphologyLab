#!/usr/bin/env python3
"""Audit the 9 built-in rule packs for v1.1 hardening."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.rule_builder.model import ScientificRule

PACKS = ROOT / "rule_packs"
OUT = ROOT / "docs" / "IML_V1_1_RULE_PACK_AUDIT.md"


def main() -> int:
    dirs = sorted(p for p in PACKS.iterdir() if p.is_dir())
    lines = [
        "# IML v1.1 Built-in Rule Pack Audit",
        "",
        "**Application version:** 1.1.0",
        f"**Pack directories found:** {len(dirs)}",
        "",
    ]
    empty = []
    summaries = []
    for d in dirs:
        man = yaml.safe_load((d / "pack.yaml").read_text(encoding="utf-8")) or {}
        rules = []
        for p in sorted((d / "rules").glob("*.yaml")):
            rules.append(ScientificRule.from_dict(yaml.safe_load(p.read_text(encoding="utf-8")) or {}))
        if not rules:
            empty.append(d.name)
        active = sum(1 for r in rules if r.enabled and r.status not in {"disabled", "rejected"})
        disabled = sum(1 for r in rules if (not r.enabled) or r.status in {"disabled", "rejected"})
        source_verified = sum(1 for r in rules if r.status in {"source_verified", "externally_reviewed", "project_approved"})
        development = sum(1 for r in rules if r.threshold_origin in {"development_calibration", "provisional"} or r.status in {"draft", "user_tested", "proposed"})
        missing_source = sum(1 for r in rules if not r.source_ids)
        feats = sorted({f for r in rules for f in (r.feature_names or [c.get("feature") for c in r.conditions if isinstance(c, dict)]) if f})
        matlab_deps = man.get("matlab_dependencies") or []
        tests = list((d / "tests").glob("*")) if (d / "tests").exists() else []
        changelog = man.get("changelog") or man.get("change_log") or []
        summaries.append(
            {
                "pack_id": man.get("pack_id", d.name),
                "version": man.get("version", ""),
                "rule_count": len(rules),
                "active": active,
                "disabled": disabled,
                "source_verified": source_verified,
                "development": development,
                "missing_source": missing_source,
                "features": feats,
                "matlab_dependencies": matlab_deps,
                "tests": len(tests),
                "changelog": changelog,
            }
        )
        lines += [
            f"## {man.get('pack_id', d.name)}",
            "",
            f"- version: `{man.get('version')}`",
            f"- verification_status: `{man.get('verification_status')}`",
            f"- rule_count: **{len(rules)}**",
            f"- active_rule_count: **{active}**",
            f"- disabled_rule_count: **{disabled}**",
            f"- source-verified/approved count: **{source_verified}**",
            f"- development count: **{development}**",
            f"- missing-source count: **{missing_source}**",
            f"- feature dependencies: {', '.join(feats) or '—'}",
            f"- MATLAB dependencies: {matlab_deps or 'none'}",
            f"- tests: {len(tests)}",
            f"- changelog: {changelog or 'see pack.yaml'}",
            f"- limitations: {man.get('limitations')}",
            "",
        ]
    lines.append("## Completeness")
    lines.append("")
    if empty:
        lines.append(f"**FAIL empty packs:** {', '.join(empty)}")
    else:
        lines.append("No empty packs.")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "docs" / "IML_V1_1_RULE_PACK_AUDIT.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"packs={len(dirs)} empty={empty}")
    print("wrote", OUT)
    if len(dirs) != 9:
        print("FAIL: expected 9 packs")
        return 1
    if empty:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
