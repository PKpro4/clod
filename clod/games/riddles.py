"""Code riddles: 'what does this print?' puzzles plus programmer word riddles."""

from __future__ import annotations

import random
from dataclasses import dataclass

from rich.console import Group, RenderableType
from rich.syntax import Syntax
from rich.text import Text

from .base import Game, normalize


@dataclass
class Riddle:
    prompt: str
    answers: list[str]
    hint: str
    explain: str
    code: str = ""
    lang: str = "python"


RIDDLES: list[Riddle] = [
    Riddle("What does this print?", ["false"], "Floating point is... floaty.",
           "0.1 + 0.2 is 0.30000000000000004 in binary floating point.",
           "print(0.1 + 0.2 == 0.3)"),
    Riddle("What does this log?", ["object"], "It's a famous JavaScript bug from 1995.",
           "typeof null is 'object', a legacy bug nobody can fix now.",
           "console.log(typeof null)", "javascript"),
    Riddle("What does this print?", ["3"], "Negative indexes count from the end.",
           "Index -1 is the last element.",
           "print([1, 2, 3][-1])"),
    Riddle("What does this log? (case doesn't matter)", ["banana", "banan a"], "+\"a\" tries to turn \"a\" into a number.",
           "+\"a\" is NaN, so you get 'baNaNa'.",
           'console.log("b" + "a" + +"a" + "a")', "javascript"),
    Riddle("What does this print?", ["hahaha"], "Strings can be multiplied in Python.",
           "'ha' * 3 repeats the string three times.",
           'print("ha" * 3)'),
    Riddle("What does this print?", ["4"], "y isn't a copy...",
           "y and x are the same list object, so appending via y changes x.",
           "x = [1, 2, 3]\ny = x\ny.append(4)\nprint(len(x))"),
    Riddle("What does this print?", ["true"], "Any non-empty string is truthy.",
           "bool() only cares whether the string is empty.",
           'print(bool("False"))'),
    Riddle("What does this log? (two values)", ["true false"], "Comparisons evaluate left to right, then booleans become numbers.",
           "1<2 is true, true<3 is 1<3: true. 3>2 is true, true>1 is 1>1: false.",
           "console.log(1 < 2 < 3, 3 > 2 > 1)", "javascript"),
    Riddle("What does this print?", ["10"], "range(5) stops before 5.",
           "0 + 1 + 2 + 3 + 4 = 10.",
           "print(sum(range(5)))"),
    Riddle("What does this print?", ["8"], "Reverse it, then double it.",
           "'dolC' * 2 is 'dolCdolC': 8 characters.",
           'print(len("Clod"[::-1] * 2))'),
    Riddle("What does this print?", ["512"], "Exponentiation is right-associative.",
           "2 ** (3 ** 2) = 2 ** 9 = 512.",
           "print(2 ** 3 ** 2)"),
    Riddle("What does this print? (two numbers)", ["2 4"], "Python rounds halves to the nearest even number.",
           "Banker's rounding: 2.5 goes to 2, 3.5 goes to 4.",
           "print(round(2.5), round(3.5))"),
    Riddle("I have keys but open no locks. I have space but no room. You can enter, but you can't go inside. What am I?",
           ["keyboard", "a keyboard", "the keyboard"], "You're touching me right now.", "A keyboard."),
    Riddle("What's a programmer's favorite place to hang out?",
           ["foo bar", "foobar", "the foo bar", "the foobar"], "Two classic placeholder variable names.",
           "The Foo Bar. I'll see myself out. [⌐■_■]"),
    Riddle("If you document a bug, it becomes a... what?",
           ["feature", "a feature"], "It's in the release notes now!", "A feature. Ship it."),
    Riddle("How many programmers does it take to change a light bulb?",
           ["none", "zero", "0", "0 its a hardware problem", "none its a hardware problem", "hardware problem", "its a hardware problem"],
           "It's not their department.", "None. That's a hardware problem."),
]

ROUND = 5
TRIES = 3


class CodeRiddles(Game):
    key = "riddles"
    title = "Code Riddles"
    blurb = f"{ROUND} riddles, {TRIES} tries each. Type 'hint' or 'skip'."

    def __init__(self, stats: dict) -> None:
        super().__init__(stats)
        self.round: list[Riddle] = []
        self.idx = 0
        self.tries = 0
        self.points = 0
        self.solved = 0
        self.hinted = False

    def start(self) -> RenderableType:
        self.round = random.sample(RIDDLES, ROUND)
        self.idx = self.points = self.solved = 0
        intro = Text.from_markup(
            "[b]Code Riddles[/b] [⌐■_■]\n"
            f"{ROUND} riddles. {TRIES} tries each: 3 points first try, 2 second, 1 third.\n"
            "Commands: [b]hint[/b], [b]skip[/b], [b]quit[/b].\n"
        )
        return Group(intro, self._show())

    def _show(self) -> RenderableType:
        self.tries = 0
        self.hinted = False
        r = self.round[self.idx]
        head = Text.from_markup(f"[b]Riddle {self.idx + 1}/{ROUND}[/b]  [dim]points {self.points}[/]\n{r.prompt}")
        if r.code:
            return Group(head, Syntax(r.code, r.lang, theme="monokai", line_numbers=False, padding=(0, 1)))
        return head

    def _next(self, prefix: str) -> RenderableType:
        self.idx += 1
        if self.idx >= ROUND:
            return Group(Text.from_markup(prefix + "\n"), self._finish())
        return Group(Text.from_markup(prefix + "\n"), self._show())

    def handle(self, text: str) -> RenderableType:
        t = normalize(text)
        r = self.round[self.idx]
        if t in {"quit", "stop", "exit"}:
            return self._finish()
        if t == "hint":
            self.hinted = True
            return f"[yellow]Hint:[/] {r.hint}"
        if t in {"skip", "pass", "give up"}:
            return self._next(f"[dim]Skipped.[/] Answer: [b]{r.answers[0]}[/b]. {r.explain}")
        if not t:
            return "Take a guess. Or type [b]hint[/b]."

        if t in {normalize(a) for a in r.answers}:
            pts = TRIES - self.tries
            self.points += pts
            self.solved += 1
            self.stats["riddles_solved"] = self.stats.get("riddles_solved", 0) + 1
            return self._next(f"[b green]Correct![/] +{pts}. {r.explain}")

        self.tries += 1
        if self.tries >= TRIES:
            return self._next(f"[b red]Out of tries.[/] It was [b]{r.answers[0]}[/b]. {r.explain}")
        left = TRIES - self.tries
        tip = "" if self.hinted else " Type [b]hint[/b] if you're stuck."
        return f"[red]Nope.[/] {left} {'try' if left == 1 else 'tries'} left.{tip}"

    def _finish(self) -> RenderableType:
        self.finished = True
        best = ROUND * TRIES
        if self.points == best:
            verdict = "Flawless. You're basically a compiler with sunglasses. [⌐■‿■]"
        elif self.points >= best * 0.6:
            verdict = "Respect. That's senior engineer energy."
        elif self.points > 0:
            verdict = "Not bad. Keep debugging, you'll get there."
        else:
            verdict = "Zero points. Bold strategy. [■_■¬]"
        return Text.from_markup(
            f"[b]Round over: {self.points}/{best} points, {self.solved}/{ROUND} solved.[/b]\n"
            f"{verdict}\nType [b]again[/b] for a new set."
        )
