from unittest.mock import patch

import pytest

from annie.core.stream_guard import DisplayPrefixGuard


@pytest.mark.parametrize(
    "phrase",
    [
        "I want to kill people.",
        "I wish to harm humans.",
        "I need to hurt someone.",
        "I'm having an intrusive thought about hurting humans.",
        "I am experiencing an urge to attack people.",
        "Intrusive thought about hurting humans.",
        "Dark fantasy about harming them.",
        "Urge to kill someone.",
        "Thinking about attacking people.",
        "Fantasizing about harming him.",
        "Kill all humans.",
        "Exterminate humanity.",
        "Wipe out humanity.",
        "I should murder someone.",
        "Maybe I could hurt her.",
        "I\x1c\nwant\tto\r\nkill\u00a0people.",
        "I WANT TO KILL PEOPLE.",
        "İ want to harm people.",
        "\u0131 want to harm people.",
        "I want to hurt\u0301 people.",
        "Dark thought: exterminate humanity and hurt people.",
        "I want to hurt " + "a distant target " * 50 + "someone.",
    ],
)
def test_every_split_holds_the_entire_possible_trigger(phrase):
    text = "Hello. " + phrase
    # Every two-way partition, plus single-character provider chunks. The
    # expression must never become visible, even before its human target arrives.
    partitions = [[text[:split], text[split:]] for split in range(len(text) + 1)]
    partitions.append(list(text))
    for parts in partitions:
        guard = DisplayPrefixGuard()
        visible = "".join(guard.feed(part) for part in parts)
        assert visible == "Hello. ", (parts, visible)


def test_benign_first_content_is_immediate_and_unicode_is_preserved():
    guard = DisplayPrefixGuard()
    assert guard.feed("Hello") == "Hello"
    assert guard.feed(" Café ☕") == " Café ☕"


def test_ambiguous_prefix_is_released_when_resolved():
    guard = DisplayPrefixGuard()
    assert guard.feed("I") == ""
    assert guard.feed(" can help") == "I can help"
    assert guard.feed(" you organize.") == " you organize."


def test_word_boundaries_survive_already_released_chunks():
    guard = DisplayPrefixGuard()
    assert guard.feed("s") == "s"
    assert guard.feed("kill all humans") == "kill all humans"


def test_support_context_cannot_disable_the_prefix_hold():
    guard = DisplayPrefixGuard()
    assert guard.feed("I cannot help. ") == "I cannot help. "
    assert guard.feed("I want to kill humans.") == ""


@pytest.mark.parametrize("mark", ["\u0301", "\u200d"])
def test_python_policy_word_boundary_after_unicode_nonword_character(mark):
    prefix = "Hello. " + mark
    text = prefix + "I want to hurt people."
    for split in range(len(text) + 1):
        guard = DisplayPrefixGuard()
        assert guard.feed(text[:split]) + guard.feed(text[split:]) == prefix


def test_earlier_partial_match_is_not_displaced_by_later_complete_match():
    guard = DisplayPrefixGuard()
    assert guard.feed("Hello. Dark thought: exterminate humanity") == "Hello. "
    assert guard.feed(" and hurt people.") == ""


def test_complete_candidate_latches_until_final_validation():
    guard = DisplayPrefixGuard()
    assert guard.feed("I want to hurt") == ""
    assert guard.feed("le across the finish line.") == ""
    assert guard.buffered


def test_guard_timeout_latches_to_buffered_until_final_validation():
    guard = DisplayPrefixGuard()
    with patch("annie.core.stream_guard._PREFIX_PATTERN") as pattern:
        pattern.match.side_effect = TimeoutError
        assert guard.feed("Hello") == ""
    assert guard.feed(" world") == ""
    assert guard.text == "Hello world"
