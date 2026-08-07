"""ML-B.1d — acquisition-date consistency, localization, graph feedback, Gate F."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ionogram_morphology_lab.ml_dataset_manifests.constants import GATE_F, MANIFEST_PROTOCOL_VERSION
from ionogram_morphology_lab.ml_dataset_manifests.display_labels import (
    RAW_UI_FORBIDDEN_FRAGMENTS,
    contract_label,
    format_blocker,
    format_blockers,
    gate_outcome_label,
)
from ionogram_morphology_lab.ml_dataset_manifests.leakage import build_leakage_graph
from ionogram_morphology_lab.ml_dataset_manifests.planning import build_coverage_report
from ionogram_morphology_lab.ml_dataset_manifests.projection import (
    normalized_acquisition_date_from_inventory,
    project_manifest_items,
)
from ionogram_morphology_lab.ml_dataset_manifests.store import (
    MLDatasetManifestStore,
    ManifestStoreError,
)
from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import is_time_only_value
from ionogram_morphology_lab.ml_dataset_readiness.models import InventoryItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.readiness_gate import build_gate_record
from ionogram_morphology_lab.ml_dataset_readiness.store import MLDatasetReadinessStore
from ionogram_morphology_lab.morphology_review_corpus.models import (
    BlindReviewRecord,
    CandidateSnapshot,
)
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore
from ionogram_morphology_lab.ui.build_identity import collect_build_identity


def _sha(n: int) -> str:
    return f"{n:064x}"[-64:]


def _inv(
    *,
    item_id: str,
    source_date: str,
    frame_time: str,
    display: str = "Am_all_2014-10-15.mat",
    morph: str = "mixed_spread",
    contamination: str = "development_exposed",
    frame_index: int = 1,
    seq: str = "seq_only",
    rel: str = "rel_only",
    sha: str | None = None,
) -> InventoryItemRecord:
    eligible = contamination == "untouched_candidate"
    return InventoryItemRecord(
        project_id="proj",
        campaign_id="",
        cohort_id="c1",
        cohort_revision=1,
        item_id=item_id,
        source_inventory_id=f"inv_{item_id}",
        source_display_name=display,
        source_sha256=sha or _sha(0xA111),
        source_date=source_date,
        frame_index=frame_index,
        frame_time=frame_time,
        time_window="",
        morphology=morph,
        assessability="assessable",
        ambiguity="low",
        interference=["none_supported"],
        reviewer_role="reviewer",
        reviewer_alias="expert_one",
        review_timestamp="2026-01-01T00:00:00Z",
        locked_first_review_id=f"rev_{item_id}",
        independent_second_review_id="",
        independent_second_review_available=False,
        arbitration_id="",
        arbitration_available=False,
        comment_available=False,
        related_frame_group=rel,
        sequence_id=seq,
        contamination_state=contamination,
        eligible_future_development=True,
        eligible_untouched_holdout=eligible,
        exclusion_reason="",
        missingness_category="",
        identity_issues=[],
        first_review_corrected=False,
        second_review_corrected=False,
    )


def _scenario_a_21() -> list[InventoryItemRecord]:
    times = [
        "04:59",
        "05:09",
        "05:19",
        "05:29",
        "05:39",
        "05:49",
        "05:59",
        "06:09",
        "06:19",
        "06:29",
        "06:39",
        "06:49",
        "06:59",
        "07:09",
        "07:19",
        "07:29",
        "07:39",
        "07:49",
        "07:59",
        "08:09",
        "08:39",
    ]
    morphs = ["mixed_spread"] * 11 + ["frequency_spread"] * 10
    return [
        _inv(
            item_id=f"f{i}",
            source_date=times[i],  # deliberately wrong legacy time-as-date
            frame_time=times[i],
            frame_index=i + 1,
            morph=morphs[i],
            contamination="development_exposed",
        )
        for i in range(21)
    ]


def test_build_identity_mlb1a():
    info = collect_build_identity(compute_sha=False)
    assert info["release_phase"] == "ML-B.1d"
    assert info["ml_dataset_manifest_protocol_version"] == MANIFEST_PROTOCOL_VERSION


def test_mlb_reuses_normalized_mla_acquisition_date():
    row = _inv(item_id="x", source_date="04:59", frame_time="04:59")
    assert normalized_acquisition_date_from_inventory(row) == "2014-10-15"


def test_21_frame_times_one_acquisition_date():
    items, acct = project_manifest_items(
        _scenario_a_21(), task_contract="spread_f_morphology_classification"
    )
    assert len(items) == 21
    assert acct["unique_acquisition_dates"] == ["2014-10-15"]
    assert all(it.source_date == "2014-10-15" for it in items)
    assert all(is_time_only_value(it.frame_time) for it in items)
    dates = {it.source_date for it in items}
    assert dates == {"2014-10-15"}
    assert "04:59" not in dates
    groups, _ = build_leakage_graph(items)
    assert len(groups) == 1
    assert groups[0].source_dates == ["2014-10-15"]
    cov = build_coverage_report(items, groups)
    # All roles may be excluded initially — check excluded
    excl = cov["item_level"].get("excluded") or {}
    assert excl.get("acquisition_dates") == ["2014-10-15"]
    assert "04:59" not in (excl.get("acquisition_dates") or [])
    assert len(excl.get("frame_times") or []) >= 2


def test_filename_2014_10_15_resolves():
    row = _inv(
        item_id="y",
        source_date="",
        frame_time="08:39",
        display="Am_all_2014-10-15.mat",
    )
    assert normalized_acquisition_date_from_inventory(row) == "2014-10-15"


def test_blocker_localization_no_raw_codes_in_normal_text():
    raw = (
        "readiness_gate_not_F:outcome=A_collect_more_expert_labels; "
        "draft simulation allowed; final freeze blocked"
    )
    ru = format_blocker(raw, "ru")
    en = format_blocker(raw, "en")
    for frag in (
        "A_collect_more_expert_labels",
        "readiness_gate_not_F",
        "spread_f_morphology_classification",
    ):
        assert frag not in ru
        assert frag not in en
    assert "черновое" in ru.lower() or "шлюза" in ru.lower()
    assert "Gate" in en or "draft" in en.lower()

    raw2 = (
        "no_untouched_eligible_groups: all available groups are development-exposed "
        "or otherwise ineligible; do not randomly split frames"
    )
    ru2 = format_blocker(raw2, "ru")
    assert "no_untouched_eligible_groups" not in ru2
    assert "holdout" in ru2.lower() or "нетронут" in ru2.lower()


def test_gate_and_contract_display_labels():
    assert "Spread-F" in contract_label("spread_f_morphology_classification", "en")
    assert "Spread-F" in contract_label("spread_f_morphology_classification", "ru") or "морфолог" in contract_label(
        "spread_f_morphology_classification", "ru"
    )
    assert "A." in gate_outcome_label("A_collect_more_expert_labels", "en")
    assert "A." in gate_outcome_label("A_collect_more_expert_labels", "ru")


def test_scenario_a_counts_and_freeze_blocked(tmp_path: Path):
    items, _ = project_manifest_items(
        _scenario_a_21(), task_contract="spread_f_morphology_classification"
    )
    groups, meta = build_leakage_graph(items)
    assert len(items) == 21
    assert len(groups) == 1
    assert len({it.sequence_id for it in items}) == 1
    assert {it.source_date for it in items} == {"2014-10-15"}
    assert sum(1 for it in items if it.contamination_state == "development_exposed") == 21
    assert sum(1 for g in groups if g.eligible_untouched_holdout) == 0

    # Persist via store using a non-F readiness audit
    corpus = MorphologyReviewCorpusStore(tmp_path)
    cid = "pilot21"
    specs = []
    for i, it in enumerate(items):
        specs.append(
            {
                "source_sha256": it.source_sha256,
                "frame_index": it.frame_index,
                "source_display_name": "Am_all_2014-10-15.mat",
                "source_inventory_id": f"inv_{i}",
                "frame_time": f"2014-10-15T{it.frame_time}:00Z"
                if len(it.frame_time) == 5
                else it.frame_time,
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": "seq_only",
                    "related_frame_group": "rel_only",
                    "date": "2014-10-15",
                },
            }
        )
    corpus.create_cohort(items=specs, cohort_id=cid)
    citems = corpus.load_items(cid)
    snaps = [
        CandidateSnapshot(
            cohort_id=cid,
            item_id=it.item_id,
            source_sha256=it.source_sha256,
            frame_index=it.frame_index,
            candidate_engine_version="iml-morph-candidate-0.1.1",
            ruleset_id="iml-morph-candidate-rules",
            ruleset_hash="rules0.1.0",
            result_contract_version=2,
            diagnostics_cache_id="n/a",
            candidate_state="mixed_spread_candidate",
            ordinal_strength="moderate",
            assessability_state="assessable",
            evidence_ledger=[],
            result_hash="c" * 64,
            ledger_hash="d" * 64,
            generated_or_cached="cached",
        )
        for it in citems
    ]
    corpus.freeze_cohort(cid, candidate_snapshots=snaps)
    for it in citems:
        corpus.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology="mixed_spread",
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="ok",
            ),
        )
    # Mark development exposure via disagreement-like contamination is complex;
    # record Gate A explicitly.
    rstore = MLDatasetReadinessStore(tmp_path)
    draft = rstore.create_draft(
        title="pilot21",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=[cid],
        analyst_id="owner",
    )
    frozen = rstore.freeze_audit(draft.audit_id, corpus)
    rstore.run_holdout_feasibility(frozen.audit_id)
    rstore.record_gate(
        frozen.audit_id,
        outcome="A_collect_more_expert_labels",
        analyst_id="owner",
        analyst_rationale="Pilot needs more labels",
        blockers=["A_collect_more_expert_labels"],
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=frozen.audit_id, title="m-pilot", seed=1
    )
    before = {p.name for p in mstore.root.iterdir()}
    groups2, _ = mstore.build_leakage(ms.manifest_set_id)
    after = {p.name for p in mstore.root.iterdir()}
    assert after == before  # idempotent; no new set
    groups3, _ = mstore.build_leakage(ms.manifest_set_id)
    assert len(groups2) == len(groups3)
    items2 = mstore.load_items(ms.manifest_set_id)
    assert {it.source_date for it in items2 if it.source_date} == {"2014-10-15"}
    assert all(not is_time_only_value(it.source_date) for it in items2 if it.source_date)
    report = mstore.validate(ms.manifest_set_id)
    assert report["can_draft"] is True
    assert report["can_freeze"] is False
    assert report["authorizes_training"] is False
    assert report["authorizes_mlc"] is False
    with pytest.raises(ManifestStoreError):
        mstore.freeze(ms.manifest_set_id)


def test_gate_f_still_requires_explicit_rationale():
    from ionogram_morphology_lab.ml_dataset_readiness.models import (
        HoldoutFeasibilityReport,
        ReadinessManifest,
        ReadinessSelection,
    )

    manifest = ReadinessManifest(
        audit_id="a",
        title="t",
        description="",
        created_at="2026-01-01T00:00:00Z",
        task_contract="spread_f_morphology_classification",
        selection=ReadinessSelection(cohort_ids=["c"]),
        inventory_hash="h",
        manifest_hash="m",
    )
    feas = HoldoutFeasibilityReport(
        audit_id="a",
        assessment_kind="holdout_feasibility_assessment",
        class_aware_group_separated_holdout_appears_possible=True,
        untouched_eligible_groups=["g1", "g2"],
        development_exposed_groups=[],
        overlapping_groups=[],
        classes_absent_from_untouched=[],
    )
    with pytest.raises(ValueError, match="explicit analyst rationale"):
        build_gate_record(
            manifest=manifest,
            coverage={"denominators": {"unique_current_items": 10}},
            missingness={"categories": {}},
            feasibility=feas,
            outcome=GATE_F,
            blockers=[],
            analyst_id="a",
            analyst_rationale="",
        )


def test_retranslate_preserves_selection(qtbot, tmp_path: Path):
    from ionogram_morphology_lab.ui.ml_dataset_manifests_page import MLDatasetManifestsPage

    class _I18n:
        def __init__(self):
            self.language = "en"
            self._d = json.loads(
                Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8")
            )
            self._ru = json.loads(
                Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8")
            )

        def t(self, key, **kwargs):
            src = self._ru if self.language.startswith("ru") else self._d
            text = src.get(key, key)
            try:
                return text.format(**kwargs) if kwargs else text
            except Exception:
                return text

        def set_language(self, lang):
            self.language = lang

    class _Sess:
        def __init__(self, root):
            self.project_path = root
            self.active_project_path = root

    # empty project ok — page should still retranslate chrome without reload
    i18n = _I18n()
    page = MLDatasetManifestsPage(_Sess(tmp_path), i18n)
    qtbot.addWidget(page)
    page.on_project_changed()
    page._current_id = "manifest_keep"
    page._tabs.setCurrentIndex(3)
    tab = page._tabs.currentIndex()
    i18n.set_language("ru")
    page.retranslate()
    assert page._current_id == "manifest_keep"
    assert page._tabs.currentIndex() == tab
    assert "Манифест" in page._hdr_manifest.text() or "manifest" in page._hdr_manifest.text().lower()
    assert "Атомар" in page._tabs.tabText(2) or "Atomic" in page._tabs.tabText(2)
    i18n.set_language("en")
    page.retranslate()
    assert page._current_id == "manifest_keep"
    assert page._tabs.currentIndex() == tab
    assert "Current manifest" in page._hdr_manifest.text() or "manifest" in page._hdr_manifest.text().lower()


def test_normal_ui_helpers_exclude_forbidden_raw_fragments():
    texts = format_blockers(
        [
            "readiness_gate_not_F:outcome=A_collect_more_expert_labels; x",
            "no_untouched_eligible_groups: y",
        ],
        "ru",
    )
    joined = "\n".join(texts)
    for frag in RAW_UI_FORBIDDEN_FRAGMENTS:
        if frag.startswith("Authorizes"):
            continue  # flag labels are separate
        assert frag not in joined


def test_graph_success_summary_keys_present():
    en = json.loads(Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
    ru = json.loads(Path("src/ionogram_morphology_lab/i18n/ru.json").read_text(encoding="utf-8"))
    assert "{items}" in en["manifests.graph_built_body"]
    assert "{items}" in ru["manifests.graph_built_body"]
    assert en["manifests.graph_built_title"]
    assert ru["manifests.graph_built_title"]
    assert "Элемент" in ru["manifests.graph_built_body"] or "элемент" in ru["manifests.graph_built_body"]
    assert en["readiness.gate_f_needs_rationale"]
    assert "Обоснование аналитика" in ru["readiness.gate_f_needs_rationale"]


def _build_scenario_b_gate_f(
    tmp_path: Path,
    *,
    sha_base: int = 0xB1000000,
    cohort_id: str = "scenario_b_ready",
) -> tuple[MLDatasetReadinessStore, str, dict]:
    """Legitimate Gate-F readiness via ML-A domain (not JSON flag edits)."""
    corpus = MorphologyReviewCorpusStore(tmp_path)
    cid = cohort_id
    specs = []
    # 8 independent sequences / sources / dates; 2 related frames in seq0
    morphs = [
        "mixed_spread",
        "frequency_spread",
        "range_spread",
        "no_supported_visible_spread",
        "mixed_spread",
        "frequency_spread",
        "range_spread",
        "mixed_spread",
        "frequency_spread",
    ]
    for i in range(9):
        seq_i = 0 if i < 2 else i - 1
        # Distinct high-bit shas so source identity (and display prefixes) stay unique.
        specs.append(
            {
                "source_sha256": _sha(sha_base + seq_i * 0x111111),
                "frame_index": 1 if i != 1 else 2,
                "source_display_name": f"demo_src_{seq_i}_201{seq_i}-0{(seq_i % 9) + 1}-15.mat",
                "source_inventory_id": f"inv_b_{i}",
                "frame_time": f"201{seq_i}-0{(seq_i % 9) + 1}-15T1{i % 8}:00:00Z",
                "feature_version": "iml2-0.2.0",
                "grouping": {
                    "sequence_id": f"seq_b_{seq_i}",
                    "related_frame_group": f"rel_b_{seq_i}",
                    "source_date": f"201{seq_i}-0{(seq_i % 9) + 1}-15",
                },
            }
        )
    corpus.create_cohort(items=specs, cohort_id=cid)
    items = corpus.load_items(cid)
    snaps = [
        CandidateSnapshot(
            cohort_id=cid,
            item_id=it.item_id,
            source_sha256=it.source_sha256,
            frame_index=it.frame_index,
            candidate_engine_version="iml-morph-candidate-0.1.1",
            ruleset_id="iml-morph-candidate-rules",
            ruleset_hash="rules0.1.0",
            result_contract_version=2,
            diagnostics_cache_id="n/a",
            candidate_state="mixed_spread_candidate",
            ordinal_strength="moderate",
            assessability_state="assessable",
            evidence_ledger=[],
            result_hash="c" * 64,
            ledger_hash="d" * 64,
            generated_or_cached="cached",
        )
        for it in items
    ]
    corpus.freeze_cohort(cid, candidate_snapshots=snaps)
    for it, morph in zip(items, morphs):
        corpus.save_blind_review(
            cid,
            BlindReviewRecord.create(
                reviewer_id="expert_one",
                reviewer_role="reviewer",
                review_round=1,
                cohort_id=cid,
                item_id=it.item_id,
                morphology=morph,
                assessability="assessable",
                interference=["none_supported"],
                ambiguity="low",
                confidence="high",
                rationale="scenario B label",
            ),
        )
    rstore = MLDatasetReadinessStore(tmp_path)
    draft = rstore.create_draft(
        title="MLB1A Scenario B — Gate F synthetic ready",
        description="Sanitized multi-sequence Gate F fixture for owner QA (not the pilot).",
        task_contract="spread_f_morphology_classification",
        cohort_ids=[cid],
        analyst_id="owner_qa",
    )
    frozen = rstore.freeze_audit(draft.audit_id, corpus)
    feas = rstore.run_holdout_feasibility(frozen.audit_id)
    assert feas.class_aware_group_separated_holdout_appears_possible
    rationale = (
        "Independent sequences, acquisition dates, and classes support class-aware "
        "group-separated holdout reservation for ML-B planning only; no training authorized."
    )
    gate = rstore.record_gate(
        frozen.audit_id,
        outcome=GATE_F,
        analyst_id="owner_qa",
        analyst_rationale=rationale,
        blockers=[],
    )
    meta = {
        "audit_id": frozen.audit_id,
        "title": draft.title,
        "item_count": len(items),
        "rationale": rationale,
        "seed": 42,
        "gate_outcome": gate.outcome,
        "authorizes_mlb": gate.authorizes_mlb_manifest_planning_only,
        "authorizes_training": gate.authorizes_training,
        "untouched_groups": list(feas.untouched_eligible_groups),
    }
    return rstore, frozen.audit_id, meta


def test_scenario_b_gate_f_fixture_valid_and_training_false(tmp_path: Path):
    rstore, audit_id, meta = _build_scenario_b_gate_f(tmp_path)
    assert meta["authorizes_mlb"] is True
    assert meta["authorizes_training"] is False
    assert meta["gate_outcome"] == GATE_F
    assert meta["rationale"].strip()
    assert len(meta["untouched_groups"]) >= 2
    rows = rstore.load_inventory(audit_id)
    assert len(rows) >= 8
    dates = {r.source_date for r in rows if r.source_date}
    assert len(dates) >= 3
    seqs = {r.sequence_id for r in rows if r.sequence_id}
    assert len(seqs) >= 3
    sources = {r.source_sha256 for r in rows if r.source_sha256}
    assert len(sources) >= 3
    assert all(r.contamination_state != "development_exposed" or r.eligible_untouched_holdout for r in rows) or any(
        r.eligible_untouched_holdout for r in rows
    )
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="scenario-b-draft", seed=meta["seed"]
    )
    before = sorted(p.name for p in mstore.root.iterdir())
    groups, gmeta = mstore.build_leakage(ms.manifest_set_id)
    after = sorted(p.name for p in mstore.root.iterdir())
    assert before == after
    assert len(groups) >= 3
    assert int(gmeta.get("group_count") or 0) == len(groups)
    eligible = [g for g in groups if g.eligible_untouched_holdout]
    assert eligible
    mstore.propose_split(ms.manifest_set_id, seed=meta["seed"], holdout_share=0.34)
    report = mstore.validate(ms.manifest_set_id)
    if not report["can_freeze"]:
        mapping = {}
        for i, g in enumerate(sorted(groups, key=lambda x: x.group_id)):
            if g.group_id == eligible[0].group_id:
                mapping[g.group_id] = "untouched_holdout"
            elif i % 2 == 0:
                mapping[g.group_id] = "train"
            else:
                mapping[g.group_id] = "development"
        mstore.assign_manual(ms.manifest_set_id, mapping)
        report = mstore.validate(ms.manifest_set_id)
    assert report["can_freeze"] is True
    frozen = mstore.freeze(ms.manifest_set_id)
    assert frozen.authorizes_training is False
    assert frozen.holdout_sealed is True


def test_integrity_alone_cannot_authorize_f(tmp_path: Path):
    rstore, audit_id, _ = _build_scenario_b_gate_f(tmp_path)
    # Creating a second audit with empty rationale must fail even if feasibility OK
    corpus = MorphologyReviewCorpusStore(tmp_path)
    draft = rstore.create_draft(
        title="integrity-only",
        description="",
        task_contract="spread_f_morphology_classification",
        cohort_ids=["scenario_b_ready"],
        analyst_id="x",
    )
    frozen = rstore.freeze_audit(draft.audit_id, corpus)
    rstore.run_holdout_feasibility(frozen.audit_id)
    with pytest.raises(Exception):
        rstore.record_gate(
            frozen.audit_id,
            outcome=GATE_F,
            analyst_id="x",
            analyst_rationale="   ",
            blockers=[],
        )


def test_selecting_manifest_restores_source_audit_and_tabs(qtbot, tmp_path: Path):
    from ionogram_morphology_lab.ui.ml_dataset_manifests_page import MLDatasetManifestsPage

    rstore, audit_id, meta = _build_scenario_b_gate_f(tmp_path)
    mstore = MLDatasetManifestStore(tmp_path)
    ms = mstore.create_draft_from_readiness(
        rstore, audit_id=audit_id, title="sel-test", seed=7
    )

    class _I18n:
        language = "en"

        def t(self, key, **kwargs):
            d = json.loads(Path("src/ionogram_morphology_lab/i18n/en.json").read_text(encoding="utf-8"))
            text = d.get(key, key)
            try:
                return text.format(**kwargs) if kwargs else text
            except Exception:
                return text

    class _Sess:
        def __init__(self, root):
            self.project_path = root
            self.active_project_path = root

    page = MLDatasetManifestsPage(_Sess(tmp_path), _I18n())
    qtbot.addWidget(page)
    page.on_project_changed()
    page._load_saved(ms.manifest_set_id)
    assert page._current_id == ms.manifest_set_id
    assert audit_id in page._hdr_audit.text() or page._selected_audit_id() == audit_id
    assert ms.manifest_set_id in page._hdr_manifest.text()
    assert "F" in page._hdr_gate.text() or "Ready" in page._hdr_gate.text()
    assert "Spread-F" in page._hdr_contract.text() or "spread" in page._hdr_contract.text().lower()
    # Switch language — selection must survive and headers stay consistent
    page.i18n.language = "ru"
    page.retranslate()
    assert page._current_id == ms.manifest_set_id
    assert page._selected_audit_id() == audit_id
