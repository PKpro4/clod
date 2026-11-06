"""Multiple-choice trivia with streaks."""

from __future__ import annotations

import random

from .base import Game, normalize

# (question, correct answer, [wrong answers])
QUESTIONS: list[tuple[str, str, list[str]]] = [
    ("What is the capital of Australia?", "Canberra", ["Sydney", "Melbourne", "Perth"]),
    ("What is the chemical symbol for gold?", "Au", ["Ag", "Gd", "Go"]),
    ("How many bits are in a byte?", "8", ["4", "16", "10"]),
    ("Who created the Python programming language?", "Guido van Rossum", ["Linus Torvalds", "Dennis Ritchie", "James Gosling"]),
    ("What is the largest ocean on Earth?", "Pacific", ["Atlantic", "Indian", "Arctic"]),
    ("In what year did humans first land on the Moon?", "1969", ["1959", "1972", "1965"]),
    ("What is the fastest land animal?", "Cheetah", ["Pronghorn", "Lion", "Greyhound"]),
    ("What does HTTP status code 404 mean?", "Not Found", ["Forbidden", "Server Error", "Moved Permanently"]),
    ("What is the smallest prime number?", "2", ["1", "3", "0"]),
    ("What is the hardest natural substance?", "Diamond", ["Quartz", "Titanium", "Graphite"]),
    ("Which planet is known as the Red Planet?", "Mars", ["Venus", "Jupiter", "Mercury"]),
    ("What does CPU stand for?", "Central Processing Unit", ["Computer Personal Unit", "Central Program Utility", "Core Processing Unit"]),
    ("How many hearts does an octopus have?", "3", ["1", "2", "8"]),
    ("What is the official language of Brazil?", "Portuguese", ["Spanish", "Brazilian", "French"]),
    ("Who wrote the novel '1984'?", "George Orwell", ["Aldous Huxley", "Ray Bradbury", "H. G. Wells"]),
    ("What is the square root of 144?", "12", ["14", "11", "16"]),
    ("Which gas do plants absorb from the air for photosynthesis?", "Carbon dioxide", ["Oxygen", "Nitrogen", "Hydrogen"]),
    ("Who invented the World Wide Web?", "Tim Berners-Lee", ["Bill Gates", "Vint Cerf", "Steve Jobs"]),
    ("What is the freezing point of water in Fahrenheit?", "32°F", ["0°F", "100°F", "-32°F"]),
    ("What animal is Tux, the Linux mascot?", "Penguin", ["Puffin", "Seal", "Duck"]),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci", ["Michelangelo", "Raphael", "Vincent van Gogh"]),
    ("Which element has atomic number 1?", "Hydrogen", ["Helium", "Oxygen", "Carbon"]),
    ("How many sides does a hexagon have?", "6", ["5", "7", "8"]),
    ("Which country has the most time zones (counting overseas territories)?", "France", ["Russia", "USA", "China"]),
    ("How many bones are in the adult human body?", "206", ["201", "212", "196"]),
    ("What is binary 1010 in decimal?", "10", ["12", "8", "5"]),
    ("What does 'RAM' stand for?", "Random Access Memory", ["Read Access Memory", "Rapid Action Memory", "Run All Modules"]),
    ("Which keyboard shortcut usually means 'undo'?", "Ctrl+Z", ["Ctrl+U", "Ctrl+Y", "Ctrl+X"]),
    ("What is the largest planet in our solar system?", "Jupiter", ["Saturn", "Neptune", "Earth"]),
    ("Which programming language is named after a coffee?", "Java", ["Mocha", "Kotlin", "Latte"]),
]

ROUND = 7
LETTERS = "ABCD"

RIGHT = ["Nailed it.", "Correct. Cool and smart.", "Yep. You're on fire.", "Boom. Right answer.", "Correct-o."]
WRONG = ["Nope.", "Oof. Not quite.", "Swing and a miss.", "Close. Not really, but close-ish."]


class Trivia(Game):
    key = "trivia"
    title = "Trivia"
    blurb = f"{ROUND} multiple-choice questions. Build a streak."

    def __init__(self, stats: dict) -> None:
        super().__init__(stats)
        self.questions: list[tuple[str, str, list[str]]] = []
        self.idx = 0
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.options: list[str] = []

    def start(self) -> str:
        self.questions = random.sample(QUESTIONS, ROUND)
        self.idx = self.score = self.streak = self.best_streak = 0
        return (
            "[b]Trivia Time[/b] [⌐■_■]\n"
            f"{ROUND} questions. Answer with a letter (A-D) or the answer itself. "
            "Type [b]quit[/b] to bail.\n\n" + self._show()
        )

    def _show(self) -> str:
        q, right, wrong = self.questions[self.idx]
        self.options = [right, *wrong]
        random.shuffle(self.options)
        opts = "\n".join(f"  [b cyan]{LETTERS[i]})[/] {o}" for i, o in enumerate(self.options))
        return f"[b]Question {self.idx + 1}/{ROUND}[/b]  [dim]score {self.score} · streak {self.streak}[/]\n{q}\n{opts}"

    def _pick(self, text: str) -> str | None:
        t = normalize(text)
        if len(t) == 1 and t.upper() in LETTERS[: len(self.options)]:
            return self.options[LETTERS.index(t.upper())]
        for o in self.options:
            if normalize(o) == t:
                return o
        return None

    def handle(self, text: str) -> str:
        if normalize(text) in {"quit", "stop", "exit"}:
            return self._finish(early=True)
        choice = self._pick(text)
        if choice is None:
            return "Pick [b]A[/b], [b]B[/b], [b]C[/b] or [b]D[/b]. I believe in you."
        right = self.questions[self.idx][1]
        if choice == right:
            self.score += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            fire = " 🔥" * min(self.streak // 3, 3)
            verdict = f"[b green]{random.choice(RIGHT)}[/]{fire}"
        else:
            self.streak = 0
            verdict = f"[b red]{random.choice(WRONG)}[/] It was [b]{right}[/b]."
        self.idx += 1
        if self.idx >= ROUND:
            return verdict + "\n\n" + self._finish()
        return verdict + "\n\n" + self._show()

    def _finish(self, early: bool = False) -> str:
        self.finished = True
        self.stats["trivia_best"] = max(self.stats.get("trivia_best", 0), self.score)
        self.stats["trivia_played"] = self.stats.get("trivia_played", 0) + 1
        total = self.idx if early else ROUND
        ratio = self.score / max(total, 1)
        if ratio == 1 and total == ROUND:
            rating = "PERFECT. Okay, you can borrow the shades. [⌐■‿■]"
        elif ratio >= 0.7:
            rating = "Solid. Big brain energy."
        elif ratio >= 0.4:
            rating = "Not bad. Not great. Very human."
        else:
            rating = "Rough one. Even Claude has off days. (He doesn't, but still.)"
        return (
            f"[b]Final score: {self.score}/{total}[/b]  ·  best streak {self.best_streak}\n"
            f"{rating}\nType [b]again[/b] for another round."
        )
