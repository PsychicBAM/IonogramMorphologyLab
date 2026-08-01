#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.security import (
    ForbiddenPathError,
    ProtectedStudyConfig,
    default_blocklist,
    reset_protection,
    set_active_protection,
)


def main() -> int:
    samples = [
        r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\09_blinded_review_package\secret\x.csv",
        r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\11_rendered_frames\a.png",
        r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\12_rendered_contact_sheets\a.png",
        r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\21_review_progress\x.csv",
        r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\20_blinded_review_app\app.py",
    ]
    reset_protection()
    bl = default_blocklist()
    for s in samples:
        if bl.is_blocked(s):
            print("FAIL blocked while optional protection is disabled:", s)
            return 1
        bl.assert_allowed(s)

    bl = set_active_protection(
        ProtectedStudyConfig(
            enabled=True,
            protected_path_fragments=[
                "09_blinded_review_package",
                "11_rendered_frames",
                "12_rendered_contact_sheets",
                "21_review_progress",
                "20_blinded_review_app",
            ],
        )
    )
    for s in samples:
        if not bl.is_blocked(s):
            print("FAIL not blocked:", s)
            return 1
        try:
            bl.assert_allowed(s)
            print("FAIL assert_allowed passed:", s)
            return 1
        except ForbiddenPathError:
            pass
    # Synthetic data remains allowed under configured protection.
    ok = ROOT / "synthetic_data"
    bl.assert_allowed(ok)
    reset_protection()
    print("validate_forbidden_path_isolation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
