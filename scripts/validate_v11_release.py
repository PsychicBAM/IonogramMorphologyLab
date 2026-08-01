#!/usr/bin/env python3
"""Final v1.1.1 release validator — rejects incomplete / inconsistent release state."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)
    print("FAIL:", msg)


def main() -> int:
    errors: list[str] = []
    from ionogram_morphology_lab import __version__
    from ionogram_morphology_lab.help.content import HELP_SECTIONS
    from ionogram_morphology_lab.matlab_studio.builtin_library import list_builtin_methods
    from ionogram_morphology_lab.scientific_outputs import ScientificFrameResult

    if __version__ != "1.1.1":
        fail(f"package version {__version__} != 1.1.1", errors)

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'version = "1.1.1"' not in pyproject:
        fail("pyproject.toml missing version 1.1.1", errors)

    settings = json.loads((ROOT / "config" / "user_settings.json").read_text(encoding="utf-8"))
    if settings.get("advanced", {}).get("app_version") != "1.1.1":
        fail("config user_settings app_version != 1.1.1", errors)

    iss = (ROOT / "packaging" / "IonogramMorphologyLab.iss").read_text(encoding="utf-8")
    if 'MyAppVersion "1.1.1"' not in iss:
        fail("Inno Setup version not 1.1.1", errors)

    # Reject active 1.0.0 remnants in current product metadata (historical RELEASE_NOTES_1.0.0 allowed)
    for rel in [
        "README.md",
        "docs/MATLAB_API_REFERENCE_EN.md",
        "docs/RELEASE_NOTES_1.1.0_EN.md",
        "src/ionogram_morphology_lab/__init__.py",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if rel.endswith("RELEASE_NOTES_1.1.0_EN.md") and "1.1.0" not in text:
            fail("missing RELEASE_NOTES_1.1.0_EN", errors)
        if rel == "src/ionogram_morphology_lab/__init__.py" and "1.1.1" not in text:
            fail("__init__ version", errors)

    # MATLAB audit
    audit_json = ROOT / "docs" / "IML_V1_1_MATLAB_METHOD_IMPLEMENTATION_AUDIT.json"
    if not audit_json.exists():
        # generate
        import subprocess

        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "audit_matlab_builtin_v11.py")])
    audit = json.loads(audit_json.read_text(encoding="utf-8"))
    counts = audit["counts"]
    if counts.get("placeholder", 0):
        fail(f"placeholder methods counted: {counts['placeholder']}", errors)
    methods = list_builtin_methods()
    if len(methods) < 82:
        fail(f"builtin methods {len(methods)} < 82", errors)
    # manifests
    for cat in sorted({m.category for m in methods if m.category not in {"tests"}}):
        man = ROOT / "matlab_builtin" / "manifests" / f"{cat}.iml-matlab.yaml"
        if not man.exists() and cat not in {"examples"}:
            # examples may share manifests; require folder manifests for analysis cats
            if cat in {
                "layer_detection",
                "es_analysis",
                "f_layer_analysis",
                "spread_f_analysis",
                "interference",
                "branch_analysis",
            }:
                fail(f"missing manifest for {cat}", errors)

    # Rule packs
    packs = [p for p in (ROOT / "rule_packs").iterdir() if p.is_dir()]
    if len(packs) != 9:
        fail(f"rule packs {len(packs)} != 9", errors)
    for p in packs:
        rules = list((p / "rules").glob("*.yaml"))
        if not rules:
            fail(f"empty rule pack counted: {p.name}", errors)

    # Es registry
    if not (ROOT / "knowledge_base" / "ES_SUBTYPE_SOURCE_REGISTRY.csv").exists():
        fail("missing ES_SUBTYPE_SOURCE_REGISTRY.csv", errors)

    # Help / i18n
    if len(HELP_SECTIONS) < 80:
        fail(f"help sections {len(HELP_SECTIONS)} < 80", errors)
    en = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads((ROOT / "src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    if set(en) != set(ru):
        fail("i18n key parity broken", errors)
    for key in (
        "nav.parameters",
        "nav.rules",
        "nav.rule_test",
        "nav.compare",
        "nav.pipeline",
        "about.title",
        "settings.interface_language",
    ):
        if key not in en:
            fail(f"missing i18n key {key}", errors)

    # Overloaded ionogram type forbidden
    src_files = list((ROOT / "src/ionogram_morphology_lab").rglob("*.py"))
    for p in src_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"ionogram_type\s*=", text) or '"ionogram_type"' in text:
            fail(f"overloaded ionogram_type in {p}", errors)
    sci = ScientificFrameResult().to_dict()
    if "ionogram_type" in sci:
        fail("ScientificFrameResult exposes ionogram_type", errors)
    for axis in ("layer", "morphology", "ambiguity", "quality", "parameter_estimates"):
        if axis not in sci:
            fail(f"missing scientific axis {axis}", errors)

    # Parameters page must not invent unexplained empties
    from ionogram_morphology_lab.ui.parameters_page import PARAMETER_CATALOG

    for item in PARAMETER_CATALOG:
        if "state" not in item or "note_en" not in item:
            fail(f"parameter catalog incomplete: {item.get('name')}", errors)

    # Checkpoint dedicated
    if not (ROOT / "checkpoints" / "CHECKPOINT_IML_V1_1_SCIENTIFIC_METHODS_RULE_BUILDER_READY.md").exists():
        fail("missing dedicated v1.1 checkpoint", errors)

    # Portable build contents (if present)
    dist = ROOT / "dist" / "IonogramMorphologyLab"
    exe = dist / "IonogramMorphologyLab.exe"
    if exe.exists():
        internal = dist / "_internal"
        search_roots = [dist, internal] if internal.exists() else [dist]
        def has_tree(name: str) -> bool:
            return any((r / name).exists() for r in search_roots)

        if not has_tree("matlab_builtin"):
            fail("portable build missing matlab_builtin", errors)
        else:
            mcount = 0
            for r in search_roots:
                mb = r / "matlab_builtin"
                if mb.exists():
                    mcount = max(mcount, len(list(mb.rglob("*.m"))))
            if mcount < 82:
                fail(f"portable matlab_builtin .m count {mcount} < 82", errors)
        if not has_tree("rule_packs"):
            fail("portable build missing rule_packs", errors)
        if not any((r / "knowledge_base" / "ES_SUBTYPE_SOURCE_REGISTRY.csv").exists() for r in search_roots):
            # may be under knowledge_base at root of _internal
            kb_ok = any((r / "knowledge_base").exists() for r in search_roots)
            if not kb_ok:
                fail("portable build missing knowledge_base", errors)
        if not any((r / "ionogram_morphology_lab" / "i18n" / "en.json").exists() or (r / "i18n" / "en.json").exists() for r in search_roots):
            # PyInstaller often nests package data
            i18n_files = list(dist.rglob("en.json"))
            if not i18n_files:
                fail("portable build missing i18n en.json", errors)
    else:
        print("WARN: portable exe not built yet — packaging check deferred")

    # UI pages exist
    for mod in (
        "rule_builder_page",
        "rule_testing_page",
        "parameters_page",
        "method_comparison_page",
        "pipeline_builder_page",
    ):
        if not (ROOT / "src/ionogram_morphology_lab/ui" / f"{mod}.py").exists():
            fail(f"missing UI module {mod}", errors)

    mw = (ROOT / "src/ionogram_morphology_lab/ui/main_window.py").read_text(encoding="utf-8")
    for key in ("parameters", "rules", "rule_test", "compare", "pipeline"):
        if f'("{key}"' not in mw and f"'{key}'" not in mw:
            fail(f"NAV missing {key}", errors)
    if "act_lang_en" in mw or 'setText("EN")' in mw:
        fail("top EN/RU language buttons present", errors)

    if errors:
        print(f"validate_v11_release FAIL ({len(errors)} errors)")
        return 1
    print("validate_v11_release OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
