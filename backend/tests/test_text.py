"""The shared description cap."""

from __future__ import annotations

from app.core.text import clip_description


def test_short_text_is_returned_unchanged() -> None:
    assert clip_description("A short description.", 300) == "A short description."


def test_whitespace_is_collapsed() -> None:
    assert clip_description("  one\n\ntwo   three  ", 300) == "one two three"


def test_long_text_is_cut_at_a_word_boundary_within_the_limit() -> None:
    clipped = clip_description("alpha " * 100, 300)

    assert len(clipped) <= 300
    assert clipped.endswith("…")
    assert clipped[:-1].split()[-1] == "alpha"


def test_the_ellipsis_counts_towards_the_limit() -> None:
    clipped = clip_description("word " * 200, 50)

    assert len(clipped) <= 50
    assert clipped.endswith("…")


def test_a_text_at_the_limit_is_untouched() -> None:
    text = "x" * 300
    assert clip_description(text, 300) == text


def test_a_zero_limit_returns_nothing() -> None:
    assert clip_description("anything", 0) == ""
