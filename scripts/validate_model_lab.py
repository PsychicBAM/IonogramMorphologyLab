#!/usr/bin/env python3
from __future__ import annotations
import csv
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
def main() -> int:
    if importlib.util.find_spec("sklearn") is None:
        print("WARN scikit-learn unavailable; Model Lab training check skipped")
        print("validate_model_lab OK"); return 0
    from ionogram_morphology_lab.classifiers.model_lab import ModelLab
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tiny.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["f1", "f2", "label", "date"]); w.writeheader()
            for i in range(12): w.writerow({"f1": i % 3, "f2": i, "label": "a" if i % 2 else "b", "date": f"2025-01-{i // 2 + 1:02d}"})
        lab = ModelLab(Path(td) / "lab"); card = lab.train(lab.import_labeled_csv(p), kind="random_forest")
        saved = json.loads((Path(td) / "lab/models" / card.model_id / "model_card.json").read_text(encoding="utf-8"))
        if saved["status"] != "development" or "Development / research use only" not in saved["limitations"][0]:
            print("FAIL development model card"); return 1
        if saved["training_manifest"]["article3_labels_used"] is not False:
            print("FAIL Article 3 claim"); return 1
    print("validate_model_lab OK"); return 0
if __name__ == "__main__": sys.exit(main())
