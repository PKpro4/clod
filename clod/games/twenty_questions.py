"""20 Questions: you think of something, Clod guesses — and learns when he loses."""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

from rich.markup import escape

from .base import Game, normalize, yes_no

DEFAULT_TREE = {
    "q": "Is it alive (or was it ever alive)?",
    "yes": {
        "q": "Is it an animal?",
        "yes": {
            "q": "Does it live mostly in water?",
            "yes": {
                "q": "Is it a mammal?",
                "yes": {"guess": "a dolphin"},
                "no": {"guess": "a shark"},
            },
            "no": {
                "q": "Can it fly?",
                "yes": {"guess": "a parrot"},
                "no": {
                    "q": "Is it commonly kept as a pet?",
                    "yes": {"guess": "a cat"},
                    "no": {"guess": "an elephant"},
                },
            },
        },
        "no": {
            "q": "Can you eat it?",
            "yes": {"guess": "a banana"},
            "no": {"guess": "a cactus"},
        },
    },
    "no": {
        "q": "Is it electronic?",
        "yes": {
            "q": "Can you hold it in one hand?",
            "yes": {"guess": "a smartphone"},
            "no": {"guess": "a laptop"},
        },
        "no": {
            "q": "Is it bigger than a car?",
            "yes": {"guess": "a mountain"},
            "no": {"guess": "a pair of sunglasses"},
        },
    },
}

MAX_QUESTIONS = 20


def data_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(Path.home(), ".local", "share")
    return Path(base) / "clod" / "twenty_questions.json"


def with_article(name: str) -> str:
    name = name.strip().rstrip(".!?")
    if re.match(r"(?i)(a|an|the|some|my|your)\s", name) or name[:1].isupper():
        return name
    if name.endswith("s") and not name.endswith("ss"):
        return name  # probably plural: "scissors", "jeans"
    return ("an " if name[:1].lower() in "aeiou" else "a ") + name


def as_question(text: str) -> str:
    q = text.strip().rstrip(".!")
    q = q[:1].upper() + q[1:]
    return q if q.endswith("?") else q + "?"


class TwentyQuestions(Game):
    key = "twenty"
    title = "20 Questions"
    blurb = "Think of something. Clod guesses it. If he loses, he learns."

    def __init__(self, stats: dict, path: Path | None = None) -> None:
        super().__init__(stats)
        self.path = path or data_path()
        self.tree = self._load()
        self.node: dict = self.tree
        self.asked = 0
        self.state = "ready"
        self.new_thing = ""

    # -- persistence -------------------------------------------------------- #
    def _load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                tree = json.load(f)
            if isinstance(tree, dict) and ("q" in tree or "guess" in tree):
                return tree
        except (OSError, ValueError):
            pass
        return copy.deepcopy(DEFAULT_TREE)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.tree, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass  # learning is best-effort

    def known_things(self) -> int:
        def count(n: dict) -> int:
            return 1 if "guess" in n else count(n["yes"]) + count(n["no"])

        return count(self.tree)

    # -- game flow ---------------------------------------------------------- #
    def start(self) -> str:
        self.node = self.tree
        self.asked = 0
        self.state = "ready"
        return (
            "[b]20 Questions[/b] [⌐■_■]\n"
            "Think of something: an animal, an object, a food, whatever.\n"
            f"I know [b]{self.known_things()}[/b] things so far, and I learn every time you beat me.\n"
            "Answer with [b]yes[/b] / [b]no[/b]. Type [b]ready[/b] when you've got one."
        )

    def _ask(self) -> str:
        if "guess" in self.node:
            self.state = "guess"
            self.asked += 1
            return f"[b]Q{self.asked}.[/b] Is it [b]{escape(self.node['guess'])}[/b]? [⌐■_■]"
        self.state = "ask"
        self.asked += 1
        return f"[b]Q{self.asked}.[/b] {escape(self.node['q'])}"

    def handle(self, text: str) -> str:
        if self.state == "ready":
            if normalize(text) in {"", "ready", "ok", "okay", "go", "yes", "y", "k", "got one", "done"}:
                return self._ask()
            return "Take your time. Type [b]ready[/b] when you've got something in mind."

        if self.state in ("ask", "guess"):
            ans = yes_no(text)
            if ans is None:
                return "Gotta give me a [b]yes[/b] or [b]no[/b], friend. The shades can't read minds. Yet."
            if self.state == "guess":
                return self._after_guess(ans)
            self.node = self.node["yes" if ans else "no"]
            if self.asked >= MAX_QUESTIONS:
                self.finished = True
                self.stats["twenty_losses"] = self.stats.get("twenty_losses", 0) + 1
                return "That's 20. I'm stumped. You win this round. [⌐■_■]\nType [b]again[/b] for a rematch."
            return self._ask()

        if self.state == "learn_name":
            name = text.strip()
            if not name:
                return "C'mon, what was it?"
            self.new_thing = with_article(name)
            self.state = "learn_q"
            old = self.node["guess"]
            return (
                f"[b]{escape(self.new_thing[:1].upper() + self.new_thing[1:])}[/b]! Should've known.\n"
                f"Teach me: give me a yes/no question where the answer is "
                f"[b]YES[/b] for {escape(self.new_thing)} but [b]NO[/b] for {escape(old)}."
            )

        if self.state == "learn_q":
            if len(text.strip()) < 3:
                return "Gimme a real question, like [i]Does it have stripes?[/i]"
            old = self.node["guess"]
            q = as_question(text)
            self.node.clear()
            self.node.update({"q": q, "yes": {"guess": self.new_thing}, "no": {"guess": old}})
            self._save()
            self.finished = True
            return (
                f"Got it. Filed away: [i]{escape(q)}[/i]\n"
                f"Now I know [b]{self.known_things()}[/b] things. Next time you're toast. [⌐■_■]\n"
                "Type [b]again[/b] to play another round."
            )

        return "Uh, I lost my place. Type [b]again[/b] to restart."

    def _after_guess(self, correct: bool) -> str:
        if correct:
            self.finished = True
            self.stats["twenty_wins"] = self.stats.get("twenty_wins", 0) + 1
            return (
                f"[b green]Called it![/] Got it in {self.asked}. [⌐■‿■]\n"
                "Type [b]again[/b] for another round."
            )
        self.stats["twenty_losses"] = self.stats.get("twenty_losses", 0) + 1
        self.state = "learn_name"
        return "Dang. You got me. [■_■¬] What were you thinking of?"
