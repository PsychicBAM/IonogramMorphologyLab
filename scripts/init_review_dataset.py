#!/usr/bin/env python3
"""Initialize the owner-review dataset workspace under app_root()/review_dataset/."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.review_dataset import ReviewDatasetStore  # noqa: E402


def main() -> int:
    store = ReviewDatasetStore()
    store.ensure_layout(write_readme=True)
    index = json.loads(store.index_path.read_text(encoding="utf-8"))
    print(f"review_dataset initialized at {store.root}")
    print(f"index.json label count: {len(index.get('label_ids', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
