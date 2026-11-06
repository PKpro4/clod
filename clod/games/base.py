"""Shared game plumbing.

Every game is a small text-driven state machine: the app feeds it the user's
input and renders whatever it returns (a Rich markup string or any Rich
renderable). That keeps games fully testable without a UI.
"""

from __future__ import annotations

import re

from rich.console import RenderableType

AGAIN = {"again", "yes", "y", "yeah", "yep", "sure", "play again", "another", "more", "go", "ok", "okay"}
YES = {"y", "yes", "yeah", "yep", "yup", "ya", "yah", "sure", "correct", "right", "true", "affirmative", "uh huh", "definitely", "absolutely", "si", "ja"}
NO = {"n", "no", "nope", "nah", "nay", "false", "negative", "wrong", "not really", "no way", "nein"}


def normalize(text: str) -> str:
    """Lowercase, strip quotes/punctuation noise, collapse whitespace."""
    t = text.strip().lower()
    t = re.sub(r"['`’]", "", t)  # it's -> its
    t = re.sub(r"[\",.!?;:()\[\]]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def yes_no(text: str) -> bool | None:
    t = normalize(text)
    if t in YES:
        return True
    if t in NO:
        return False
    return None


class Game:
    key = ""
    title = ""
    blurb = ""

    def __init__(self, stats: dict) -> None:
        self.stats = stats
        self.finished = False

    def start(self) -> RenderableType:  # pragma: no cover - abstract
        raise NotImplementedError

    def handle(self, text: str) -> RenderableType:  # pragma: no cover - abstract
        raise NotImplementedError

    def feed(self, text: str) -> RenderableType:
        if self.finished:
            if normalize(text) in AGAIN:
                self.finished = False
                return self.start()
            return (
                "[dim]Round's over. Type [b]again[/b] for another, "
                "pick a different game, or press [b]F1[/b] to chat.[/]"
            )
        return self.handle(text)
