"""Verify that the v1.1 scientific-extension assets are present."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    from ionogram_morphology_lab import __version__
    from ionogram_morphology_lab.help.content import HELP_SECTIONS

    errors: list[str] = []
    check(__version__ == "1.1.1", f"expected version 1.1.1, got {__version__}", errors)

    builtin = list((ROOT / "matlab_builtin").rglob("*.m"))
    check(len(builtin) >= 70, f"expected >=70 MATLAB methods, got {len(builtin)}", errors)
    packs = [p for p in (ROOT / "rule_packs").iterdir() if p.is_dir()]
    check(len(packs) == 9, f"expected 9 rule packs, got {len(packs)}", errors)
    check(len(HELP_SECTIONS) >= 80, f"expected >=80 help sections, got {len(HELP_SECTIONS)}", errors)
    check(
        (ROOT / "knowledge_base" / "ES_SUBTYPE_SOURCE_REGISTRY.csv").is_file(),
        "missing ES_SUBTYPE_SOURCE_REGISTRY.csv",
        errors,
    )

    for module in (
        "ionogram_morphology_lab.scientific_outputs",
        "ionogram_morphology_lab.ui.parameters_page",
        "ionogram_morphology_lab.ui.rule_builder_page",
        "ionogram_morphology_lab.ui.rule_testing_page",
        "ionogram_morphology_lab.ui.method_comparison_page",
        "ionogram_morphology_lab.ui.pipeline_builder_page",
    ):
        try:
            __import__(module)
        except Exception as exc:  # noqa: BLE001 - validation should list every broken import
            errors.append(f"cannot import {module}: {exc}")

    if errors:
        print("FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "OK: v1.1.1; "
        f"{len(builtin)} MATLAB methods; {len(packs)} rule packs; {len(HELP_SECTIONS)} help sections."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
