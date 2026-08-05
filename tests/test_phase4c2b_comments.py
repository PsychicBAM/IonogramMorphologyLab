"""Phase 4C.2b — structured comments, presets, append-only."""

from __future__ import annotations

from pathlib import Path

from ionogram_morphology_lab.morphology_review_corpus.comments import (
    CommentRecord,
    apply_preset,
    generate_comment_text,
)
from ionogram_morphology_lab.morphology_review_corpus.integrity import validate_cohort
from ionogram_morphology_lab.morphology_review_corpus.store import MorphologyReviewCorpusStore


def test_deterministic_ru_en_generation():
    codes = [
        "primary_f_trace_partial",
        "range_broadening_visible",
        "vertical_interference",
        "interference_partly_obscures_trace",
        "partially_assessable",
    ]
    ru = generate_comment_text(codes, "ru")
    en = generate_comment_text(codes, "en")
    assert "F-след" in ru or "частично" in ru
    assert "расширения" in ru or "помех" in ru
    assert "partially" in en.lower() or "Range" in en
    assert ru != en
    assert generate_comment_text(codes, "ru") == ru


def test_preset_does_not_select_morphology():
    p = apply_preset("weak_frequency_spread", "en")
    assert p["morphology"] is None
    assert p["codes"]
    assert p["generated_text"]


def test_edited_text_does_not_change_codes_or_morphology(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{0x1234567890ABCDEF:064x}"[-64:],
                "frame_index": 0,
                "source_display_name": "c.mat",
                "source_inventory_id": "inv",
            }
        ],
        cohort_id="c1",
    )
    codes = ["primary_f_trace_clear", "fully_assessable"]
    rec = CommentRecord.create(
        comment_type="observation",
        cohort_id="c1",
        item_id=store.load_items("c1")[0].item_id,
        reviewer_id="r1",
        structured_codes=codes,
        generated_text=generate_comment_text(codes, "en"),
        final_text="EDITED FREE TEXT — not a morphology class",
        expert_own_description="owner free wording",
        ui_language="en",
    )
    store.save_comment("c1", rec)
    loaded = store.load_comments("c1")[0]
    assert loaded.structured_codes == codes
    assert loaded.final_text.startswith("EDITED")
    assert loaded.generated_text != loaded.final_text
    assert loaded.expert_own_description == "owner free wording"
    # append-only supersession
    rec2 = CommentRecord.create(
        comment_type="observation",
        cohort_id="c1",
        item_id=loaded.item_id,
        reviewer_id="r1",
        structured_codes=codes,
        final_text="second revision",
        supersedes_comment_id=loaded.comment_id,
    )
    store.save_comment("c1", rec2)
    current = store.load_comments("c1")
    assert len(current) == 1
    assert current[0].final_text == "second revision"
    assert validate_cohort(store, "c1") == []


def test_post_reveal_note_type_separated(tmp_path: Path):
    store = MorphologyReviewCorpusStore(tmp_path)
    store.create_cohort(
        items=[
            {
                "source_sha256": f"{0xFEDCBA9876543210:064x}"[-64:],
                "frame_index": 1,
                "source_display_name": "d.mat",
                "source_inventory_id": "inv2",
            }
        ],
        cohort_id="c2",
    )
    item_id = store.load_items("c2")[0].item_id
    store.save_comment(
        "c2",
        CommentRecord.create(
            comment_type="decision_rationale",
            cohort_id="c2",
            item_id=item_id,
            reviewer_id="r1",
            structured_codes=["fully_assessable"],
            final_text="blind rationale",
        ),
    )
    store.save_comment(
        "c2",
        CommentRecord.create(
            comment_type="post_reveal_comparison_note",
            cohort_id="c2",
            item_id=item_id,
            reviewer_id="r1",
            final_text="after reveal note",
        ),
    )
    blind = store.load_comments("c2", comment_type="decision_rationale")
    post = store.load_comments("c2", comment_type="post_reveal_comparison_note")
    assert blind[0].final_text == "blind rationale"
    assert post[0].final_text == "after reveal note"
