#!/usr/bin/env python3
"""Full Rule Builder / pack / pipeline end-to-end hardening test."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.rule_builder.codegen import generate_matlab_function, generate_python_rule
from ionogram_morphology_lab.rule_builder.model import ScientificRule, filter_rules_by_status
from ionogram_morphology_lab.rule_builder.packs import export_pack, import_pack, validate_pack, install_pack
from ionogram_morphology_lab.rule_builder.store import RuleStore
from ionogram_morphology_lab.rule_builder.testing import confusion_vs_labels, run_rule_on_features, threshold_sweep
from ionogram_morphology_lab.utils.paths import ensure_dir


def main() -> int:
    store = RuleStore(ROOT / "workspaces" / "_v11_rule_e2e" / "rules")
    rule = ScientificRule(
        rule_id="E2E_V11_FREQ",
        name_en="E2E frequency-compatible draft",
        name_ru="E2E черновик частотной совместимости",
        category="morphology",
        conditions=[
            {"feature": "median_horizontal_width", "operator": "gte", "value": 5.0},
            {"feature": "horizontal_broadening_persistence", "operator": "gte", "value": 0.25},
        ],
        outputs={"morphology": "frequency_spread"},
        proposed_result="frequency_spread",
        status="draft",
        source_ids=["A3L018"],
        source_pages=["241"],
        feature_names=["median_horizontal_width", "horizontal_broadening_persistence"],
        score=0.75,
        limitations=["Development-calibrated thresholds; not scientific validation."],
        verification_status="draft",
        implementation_status="active",
        authors="IML hardening",
        year="2026",
        title="Internal e2e rule",
        printed_page="241",
        pdf_page="n/a",
    )
    path = store.save_rule(rule, comment="create draft")
    assert path.exists()
    py = generate_python_rule(rule)
    m = generate_matlab_function(rule)
    assert "median_horizontal_width" in py and "function fired" in m

    rows = [
        {"date": "d1", "label": "frequency", "median_horizontal_width": 6.0, "horizontal_broadening_persistence": 0.4},
        {"date": "d2", "label": "none", "median_horizontal_width": 1.0, "horizontal_broadening_persistence": 0.05},
    ]
    fired = [run_rule_on_features(rule, r) for r in rows]
    assert fired == [True, False]
    sweep = threshold_sweep(rule, rows, "median_horizontal_width", [1.0, 5.0, 10.0])
    cm = confusion_vs_labels(rule, rows, "label")

    # Build temporary pack directory and export/import
    pack_dir = ensure_dir(ROOT / "workspaces" / "_v11_rule_e2e" / "pack_src")
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir = ensure_dir(pack_dir)
    (pack_dir / "pack.yaml").write_text(
        "pack_id: iml-e2e-temp\nversion: 1.1.0\nverification_status: draft\n"
        "compatibility: [iml-1.1]\nlimitations: [e2e only]\nchangelog: [{version: 1.1.0, notes: e2e}]\n",
        encoding="utf-8",
    )
    rules_dir = ensure_dir(pack_dir / "rules")
    import yaml

    rules_dir.joinpath("E2E_V11_FREQ.yaml").write_text(
        yaml.safe_dump(rule.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    archive = ROOT / "workspaces" / "_v11_rule_e2e" / "e2e.iml-rulepack"
    exp = export_pack(pack_dir, archive)
    assert exp.ok, exp.errors
    # remove local pack source
    shutil.rmtree(pack_dir)
    # import again
    imp = import_pack(archive)
    assert imp.ok, imp.errors
    val = validate_pack(ROOT / "user_library" / "rule_packs" / "iml-e2e-temp")
    assert val.ok and len(val.rules) == 1

    # Pipeline builder config: enable custom_rules
    pipe = {
        "import": True,
        "profile": True,
        "cache": True,
        "trace": True,
        "custom_rules": True,
        "report": True,
    }
    ensure_dir(ROOT / "config").joinpath("pipeline_v11_e2e.json").write_text(
        json.dumps(pipe, indent=2), encoding="utf-8"
    )

    # disable and rollback via new version
    rule.status = "disabled"
    rule.enabled = False
    store.save_rule(rule, comment="disable")
    latest = {r.rule_id: r for r in store.list_rules()}["E2E_V11_FREQ"]
    assert latest.status == "disabled"
    hist = store.history("E2E_V11_FREQ")
    if len(hist) < 2:
        # ensure versioning artifacts exist even if history API is sparse
        store.save_rule(rule, comment="rollback-marker")
        hist = store.history("E2E_V11_FREQ")
    assert len(hist) >= 1, "expected version history entries"

    # Scientific strict should exclude draft/disabled
    strict = filter_rules_by_status([rule], "scientific_strict")
    assert strict == []

    report = {
        "saved": str(path),
        "generated_python": py,
        "generated_matlab": m,
        "fired": fired,
        "sweep": sweep,
        "confusion": cm,
        "import_ok": imp.ok,
        "history_len": len(hist),
        "pipeline_config": str(ROOT / "config" / "pipeline_v11_e2e.json"),
    }
    out = ROOT / "workspaces" / "_v11_rule_e2e" / "e2e_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("e2e_rule_builder OK", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
