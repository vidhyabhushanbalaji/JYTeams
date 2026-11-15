"""Mention markers: parsing, cleaning and the marker the composer writes."""

from __future__ import annotations

from app.chat.mentions import clean_label, extract, has_marker, marker, targets_of


def test_a_marker_round_trips_through_the_parser() -> None:
    body = f"read {marker('file', 'f-1', 'auth.md')} before you deploy"

    [mention] = extract(body)

    assert mention.kind == "file"
    assert mention.id == "f-1"
    assert mention.label == "auth.md"


def test_every_kind_is_recognised() -> None:
    body = " ".join(
        [
            marker("file", "f-1", "auth.md"),
            marker("directory", "d-1", "guides"),
            marker("ticket", "t-1", "Fix the redirect"),
        ]
    )

    assert [mention.kind for mention in extract(body)] == ["file", "directory", "ticket"]


def test_mentions_are_distinct_and_in_the_order_they_appear() -> None:
    file_marker = marker("file", "f-1", "auth.md")
    ticket_marker = marker("ticket", "t-1", "Fix the redirect")

    mentions = extract(f"{ticket_marker} then {file_marker} then {ticket_marker} again")

    assert [mention.key for mention in mentions] == [("ticket", "t-1"), ("file", "f-1")]


def test_labels_lose_the_characters_that_would_break_a_marker() -> None:
    assert clean_label("  auth [draft]\n.md  ") == "auth draft .md"


def test_an_empty_label_falls_back_to_something_readable() -> None:
    assert clean_label("   ") == "item"


def test_text_that_only_looks_like_a_mention_is_ignored() -> None:
    assert extract("email me at ada@example.com (@not a mention)") == []
    assert not has_marker("a plain message about @mentions")


def test_targets_of_collects_one_kind_without_duplicates() -> None:
    mentions = extract(
        f"{marker('file', 'f-1', 'a.md')} {marker('file', 'f-1', 'a.md')} "
        f"{marker('file', 'f-2', 'b.md')} {marker('ticket', 't-1', 'One')}"
    )

    assert targets_of(mentions, "file") == ["f-1", "f-2"]
    assert targets_of(mentions, "ticket") == ["t-1"]
