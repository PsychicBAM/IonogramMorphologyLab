#!/usr/bin/env python3
"""Validate Phase 4C.3 morphology review campaign contracts (synthetic fixtures)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ionogram_morphology_lab.morphology_review_campaign.constants import (
    CAMPAIGN_INTEGRITY_CONTRACT_VERSION,
    CAMPAIGN_PROTOCOL_SCHEMA_VERSION,
    CAMPAIGN_SCHEMA_VERSION,
)
from ionogram_morphology_lab.morphology_review_campaign.exports import (
    export_campaign_readiness,
)
from ionogram_morphology_lab.morphology_review_campaign.integrity import validate_campaign
from ionogram_morphology_lab.morphology_review_campaign.models import (
    ReviewerPlan,
    SamplingPlan,
    SourceScopeEntry,
    TimeWindow,
)
from ionogram_morphology_lab.morphology_review_campaign.store import (
    MorphologyReviewCampaignStore,
)
from ionogram_morphology_lab.morphology_review_corpus.integrity import (
    validate_no_production_ruleengine_wiring,
)


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def main() -> int:
    issues: list[str] = []
    with tempfile.TemporaryDirectory(prefix="iml_campaign_val_") as tmp:
        project = Path(tmp)
        store = MorphologyReviewCampaignStore(project)
        a = store.preview_sampling(
            sources=[
                SourceScopeEntry(_sha(1), "a.mat", "ia", "2014-01", True),
                SourceScopeEntry(_sha(2), "b.mat", "ib", "2014-02", True),
            ],
            windows=[TimeWindow(300, 420, 10, "morning")],
            plan=SamplingPlan(method="deterministic_random", seed=42, target_count=6),
        )
        b = store.preview_sampling(
            sources=[
                SourceScopeEntry(_sha(1), "a.mat", "ia", "2014-01", True),
                SourceScopeEntry(_sha(2), "b.mat", "ib", "2014-02", True),
            ],
            windows=[TimeWindow(300, 420, 10, "morning")],
            plan=SamplingPlan(method="deterministic_random", seed=42, target_count=6),
        )
        if a["fingerprints"] != b["fingerprints"]:
            issues.append("sampling_not_deterministic")

        manifest = store.create_campaign(
            campaign_id="fixture_campaign_4c3",
            display_name="Fixture campaign",
            sources=[
                SourceScopeEntry(_sha(1), "a.mat", "ia", "2014-01", True),
                SourceScopeEntry(_sha(2), "b.mat", "ib", "2014-02", True),
            ],
            windows=[TimeWindow(300, 420, 10, "morning")],
            sampling_plan=SamplingPlan(
                method="deterministic_random", seed=42, target_count=6
            ),
            reviewer_plan=ReviewerPlan(
                first_reviewer_id="r1",
                first_reviewer_alias="A",
                second_reviewer_optional=True,
            ),
            create_linked_cohort=True,
            freeze_cohort=False,
        )
        report = validate_campaign(store, manifest.campaign_id)
        if not report["ok"]:
            issues.extend(report["issues"])

        exp = export_campaign_readiness(store, manifest.campaign_id)
        md = Path(exp["md_path"]).read_text(encoding="utf-8")
        for bad in ("accuracy", "f1_score", "E:\\", "C:\\Users"):
            if bad.lower() in md.lower() and bad.startswith(("E:", "C:")):
                issues.append(f"absolute_path_in_export:{bad}")
            if bad in ("accuracy", "f1_score") and f"**{bad}**" in md.lower():
                issues.append(f"metric_claim:{bad}")

        re_issues = validate_no_production_ruleengine_wiring(ROOT)
        issues.extend(re_issues)

    if CAMPAIGN_SCHEMA_VERSION != 1:
        issues.append("unexpected_campaign_schema")
    if CAMPAIGN_PROTOCOL_SCHEMA_VERSION != 1:
        issues.append("unexpected_protocol_schema")
    if CAMPAIGN_INTEGRITY_CONTRACT_VERSION != 1:
        issues.append("unexpected_integrity_contract")

    if issues:
        print("Morphology review campaign validator FAILED")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("Morphology review campaign validator OK")
    print(f"  schemas: campaign={CAMPAIGN_SCHEMA_VERSION} protocol={CAMPAIGN_PROTOCOL_SCHEMA_VERSION}")
    print(f"  integrity_contract={CAMPAIGN_INTEGRITY_CONTRACT_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
