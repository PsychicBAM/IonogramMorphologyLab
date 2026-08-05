"""Phase 4C.2b.3 — comparison abstention / agreement semantics."""

from __future__ import annotations

from ionogram_morphology_lab.morphology_review_corpus.labels import (
    comparison_status,
    comparison_status_display,
)


def test_pending_reveal_display_not_abstained():
    text_ru = comparison_status_display("comparison_pending_reveal", "ru")
    assert "не показан" in text_ru.lower() or "не выполнен" in text_ru.lower()
    assert "воздерж" not in text_ru.lower()
    text_en = comparison_status_display("comparison_pending_reveal", "en")
    assert "not yet revealed" in text_en.lower() or "not performed" in text_en.lower()
    assert "abstain" not in text_en.lower()


def test_human_indeterminate_after_reveal():
    assert (
        comparison_status(
            human_morphology="indeterminate",
            human_assessability="partially_assessable",
            candidate_state="frequency_spread_candidate",
            candidate_available=True,
        )
        == "human_abstained"
    )
    ru = comparison_status_display("human_abstained", "ru")
    assert "воздерж" in ru.lower()
    assert "класс" in ru.lower() or "определён" in ru.lower()


def test_human_not_assessable():
    assert (
        comparison_status(
            human_morphology="not_assessable",
            human_assessability="not_assessable",
            candidate_state="frequency_spread_candidate",
            candidate_available=True,
        )
        == "not_comparable"
    )
    ru = comparison_status_display("not_comparable", "ru")
    assert "неоцениваемым" in ru.lower() or "невозможно" in ru.lower()


def test_candidate_unavailable():
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state=None,
            candidate_available=False,
        )
        == "candidate_unavailable"
    )


def test_definite_agreement_and_disagreement():
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="frequency_spread_candidate",
            candidate_available=True,
        )
        == "exact_agreement"
    )
    assert (
        comparison_status(
            human_morphology="frequency_spread",
            human_assessability="assessable",
            candidate_state="range_spread_candidate",
            candidate_available=True,
        )
        == "morphology_disagreement"
    )


def test_both_abstained():
    assert (
        comparison_status(
            human_morphology="indeterminate",
            human_assessability="not_assessable",
            candidate_state="indeterminate_candidate",
            candidate_available=True,
        )
        == "both_abstained"
    )


def test_no_generic_impossible_without_reason():
    # Display strings must carry a reason
    for code in ("not_comparable", "candidate_unavailable"):
        for lang in ("en", "ru"):
            text = comparison_status_display(code, lang)
            assert len(text) > 10
            assert text != "Comparison impossible"
            assert text != "Сравнение невозможно"
