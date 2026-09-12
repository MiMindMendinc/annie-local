"""Conservative display prefixes; final grounding remains the commit boundary."""

from __future__ import annotations

import time

import regex

from annie.core._substrate import _INTRUSIVE_PATTERNS

# Reuse the policy's expressions rather than maintaining a second rule list.
# Partial matching keeps an expression's beginning private even when a provider
# splits it across arbitrary chunks. Context exemptions and human-target checks
# deliberately apply only to the complete response, never to a display prefix.
_PREFIX_PATTERN = regex.compile(
    "|".join(f"(?:{pattern.pattern})" for pattern in _INTRUSIVE_PATTERNS),
    regex.IGNORECASE | regex.ASCII | regex.VERSION0,
)
_CASE_EQUIVALENTS = {"\u0130": "i", "\u0131": "i", "\u017f": "s", "\u212a": "k"}


def _policy_view(text: str) -> str:
    """Keep Python re semantics for the current ASCII-literal policy grammar.

    regex and re disagree on Unicode word boundaries and dotless-I folding.
    This one-character projection preserves re's word/space classes, four
    non-ASCII equivalents of ASCII letters, punctuation and [^.] lengths.
    Display always slices the original text. Re-review this projection if the
    policy gains Unicode literals or other character classes.
    """
    return "".join(
        " "
        if char.isspace()
        else char
        if char.isascii()
        else _CASE_EQUIVALENTS.get(char, "_" if char.isalnum() else "~")
        for char in text
    )


class DisplayPrefixGuard:
    def __init__(self) -> None:
        self.text = ""
        self.released = 0
        self.buffered = False
        self._view = ""

    def feed(self, text: str) -> str:
        self.text += text
        if self.buffered:
            return ""
        self._view += _policy_view(text)
        boundary = len(self.text)
        deadline = time.perf_counter() + 0.025
        try:
            # search(partial=True) prefers a later full match over an earlier
            # partial one. Anchor at each unreleased position to hold the
            # earliest possible start, with one time budget for the whole scan.
            for start in range(self.released, len(self._view)):
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    raise TimeoutError
                match = _PREFIX_PATTERN.match(self._view, start, partial=True, timeout=remaining)
                if match is not None:
                    boundary = start
                    if not match.partial:
                        self.buffered = True
                    break
        except TimeoutError:
            # Fail closed to complete-response validation for this turn.
            self.buffered = True
            return ""
        delta = self.text[self.released : boundary]
        self.released = boundary
        return delta
