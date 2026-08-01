#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    errors = []
    rules = (ROOT / "src/ionogram_morphology_lab/rules").glob("*.py")
    features = (ROOT / "src/ionogram_morphology_lab/features").glob("*.py")
    text = "\n".join(p.read_text(encoding="utf-8") for p in [*rules, *features])
    if not any(token in text.lower() for token in ("provenance", "source_citations", "citation_class")): errors.append("feature/rule provenance")
    model = (ROOT / "src/ionogram_morphology_lab/classifiers/model_lab.py").read_text(encoding="utf-8")
    if "abstain" not in model: errors.append("abstention")
    presenters = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src/ionogram_morphology_lab").rglob("*presenter*.py"))
    if "confidence" not in presenters.lower() or "is none" not in presenters.lower(): errors.append("confidence null messaging")
    if errors: print("FAIL", "; ".join(errors)); return 1
    print("validate_scientific_provenance OK"); return 0
if __name__ == "__main__": sys.exit(main())
