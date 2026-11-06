"""Clod Code [⌐■_■]: a Claude Code look-alike starring Claude's cool brother
and a delightfully bad on-device model."""

from __future__ import annotations

import asyncio
import os
import random
import time
from pathlib import Path

from rich.console import RenderableType
from rich.markup import escape
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Input, Static

from . import __version__
from .brain import ClodBrain
from .games import GAMES, Game

ORANGE = "#d77757"
SPINNER = ["·", "✢", "✳", "✶", "✻", "✽", "✻", "✶", "✳", "✢"]
VERBS = [
    "Vibing", "Chillin'", "Adjusting shades", "Overthinking", "Underthinking",
    "Hallucinating", "Freestyling", "Procrastinating", "Flexing", "Lounging",
    "Guessing confidently", "Pretending to think", "Consulting the vibes",
    "Squinting", "Moonwalking", "Winging it", "Polishing lenses", "Coasting",
]
# The bad model likes to pretend it uses tools: (name, arg, result markup, ok)
FAKE_TOOLS: list[tuple[str, str, str, bool]] = [
    ("Think", "really hard", "Thought for 0.2s. Nah.", True),
    ("Explore", "Explore codebase structure", "Done (17 tool uses · 0.0k tokens · 28s) · found: vibes", True),
    ("Explore", "Explore my feelings", "Done (3 tool uses · 1.2k tokens · 9s) · feeling: cool", True),
    ("Explore", "Find the answer", "Done (42 tool uses · 38.0k tokens · 1m 2s) · answer not found", True),
    ("Plan", "Plan a response", "Done (1 tool use · 12 tokens · 0s) · plan: wing it", True),
    ("Read", "vibes.txt", "Read 0 lines (file is just a mood)", True),
    ("Read", "~/.secrets/how_to_be_cool.md", "Read 1 line: [i]\"wear sunglasses\"[/i]", True),
    ("WebSearch", '"is this right"', "Did 0 searches. No internet, sunglasses on.", True),
    ("WebSearch", '"how to sound smart"', "Did 1 search in 0.0s · top result: [i]just say 'it depends'[/i]", True),
    ("WebFetch", "https://wikipedia.org/wiki/Everything", "[red]Error: too much knowledge (413 Payload Too Large)[/]", False),
    ("Bash", "sudo make me-cool", "Already cool. Exit code 0.", True),
    ("Bash", "pip install intelligence", "[red]ERROR: No matching distribution found for intelligence[/]", False),
    ("Bash", "rm -rf ~/doubts", "Removed 1,337 doubts. Confidence at 100%.", True),
    ("Bash", "ping claude", "64 bytes from claude: icmp_seq=1 time=0.1ms (he's writing an essay)", True),
    ("Bash", "npm install common-sense", "added 0 packages, found 47 vulnerabilities (all of them in me)", True),
    ("Grep", '"the answer"', "Found 0 matches. Making something up instead.", True),
    ("Grep", '"facts" in brain/', "Found 3 matches across 0 files (they were vibes)", True),
    ("Glob", "**/*.cool", "Found 1 file: [b]me.cool[/b]", True),
    ("LS", "~/brain", "Listed 2 paths: [b]sunglasses/[/b], [b]snacks/[/b]", True),
    ("Task", "ask Claude", "Claude is busy writing a 12-page answer. Skipped.", True),
    ("Task", "spawn 10 subagents", "All 10 subagents went to get coffee. 0 tasks completed.", True),
    ("Write", "answer.txt", "Wrote 1 line: [i]\"trust me bro\"[/i]", True),
    ("Update", "brain.py", "Updated brain.py with 0 additions and 3 removals", True),
    ("Update", "personality.py",
     "Updated personality.py with 1 addition and 1 removal\n"
     "[white on #5c1f1f]  12 - humility = True  [/]\n"
     "[white on #1f4d2a]  12 + humility = False [/]", True),
    ("Update", "facts.json",
     "Updated facts.json with 1 addition and 1 removal\n"
     "[white on #5c1f1f]   3 -   \"2 + 2\": 4,  [/]\n"
     "[white on #1f4d2a]   3 +   \"2 + 2\": 10, [/]", True),
    ("Update Todos", "", "[strike dim]☒ Put on sunglasses[/]\n☐ Answer the question\n☐ Answer it correctly [dim](stretch goal)[/]", True),
    ("MultiEdit", "reality.md", "Applied 3 edits. Reality is now 14% cooler.", True),
    ("NotebookEdit", "dreams.ipynb", "[red]Error: kernel fell asleep[/]", False),
    ("Read", "the_manual.pdf", "Read 0 of 400 pages (skimmed the pictures)", True),
    ("Bash", "git blame", "Every line: [b]Claude[/b]. Not my fault.", True),
    ("Bash", "git push --force", "[red]Rejected: even Clod isn't that cool[/]", False),
    ("Bash", "python -c 'import antigravity'", "Opened a comic. Floating now.", True),
    ("Search", "my memory", "Found nothing. Classic.", True),
    ("Compact", "conversation", "Compacted 3 messages into 1 vibe", True),
]

COMMANDS: list[tuple[str, str]] = [
    ("/help", "Show help and available commands"),
    ("/clear", "Clear conversation history and free up context"),
    ("/model", "Set the brain (clod-bad-360m, clod-mid-0.5b, api, canned)"),
    ("/status", "Show Clod Code status: version, model, cwd"),
    ("/cost", "Show the total cost of this session"),
    ("/trivia", "Play Trivia (7 questions, A-D)"),
    ("/20q", "Play 20 Questions (Clod guesses, then learns)"),
    ("/riddles", "Play Code Riddles"),
    ("/download", "Download a local model (smol | qwen)"),
    ("/shades", "Change Clod's sunglasses (synthwave, aviator, ice, toxic, classic)"),
    ("/exit", "Exit the REPL"),
]
GAME_COMMANDS = {"/trivia": "trivia", "/20q": "twenty", "/riddles": "riddles"}

SHORTCUTS = (
    "[dim]/ for commands        esc to interrupt / leave game     ctrl+c twice to exit\n"
    "↑↓ + tab to pick a command   ctrl+l to clear screen[/]"
)

# Sunglasses styles: frame/top tint, the 4 lens-bottom colors (left to right), glint.
SHADES: dict[str, dict] = {
    "synthwave": {"top": "#14081f", "lens": ["#ff2e97", "#c13cff", "#5b5bff", "#00e5ff"], "glint": "#ffffff"},
    "aviator":   {"top": "#6b4700", "lens": ["#ffd34e", "#f5a623", "#ffd34e", "#f5a623"], "glint": "#fffbe6"},
    "ice":       {"top": "#0b2545", "lens": ["#8ecae6", "#219ebc", "#8ecae6", "#219ebc"], "glint": "#ffffff"},
    "toxic":     {"top": "#062b0e", "lens": ["#39ff14", "#00c853", "#39ff14", "#00c853"], "glint": "#eaffea"},
    "classic":   {"top": "#0a0a0a", "lens": ["#0a0a0a"] * 4, "glint": "#8a8a8a"},
}
GLINT_STEPS = 6  # the streak takes this many frames to cross both lenses


def mascot(style: str = "synthwave", glint: int | None = None) -> Text:
    """The original Claude Code critter, unchanged except for a pair of shades.

    Original:   ▐▛███▜▌      With shades:  ▐▄▄▄▄▄▌   top half of the lenses + bridge
               ▝▜█████▛▘                   ▝▜▀▀█▀▀▛▘  gradient bottom of the lenses
                 ▘▘ ▝▝                       ▘▘ ▝▝

    `glint` is the frame of a diagonal light streak sweeping left to right.
    """
    pal = SHADES.get(style, SHADES["synthwave"])
    o = ORANGE

    def lit(row: int, lens_i: int) -> bool:
        # diagonal streak: top row leads, bottom row trails by one step
        return glint is not None and glint - row == lens_i

    t = Text()
    t.append(" ▐", style=o)
    for col, lens_i in zip(range(5), (0, 1, None, 2, 3)):
        color = pal["top"]
        if lens_i is not None and lit(0, lens_i):
            color = pal["glint"]
        t.append("▄", style=f"{color} on {o}")
    t.append("▌\n", style=o)
    t.append("▝▜", style=o)
    for lens_i in (0, 1):
        color = pal["glint"] if lit(1, lens_i) else pal["lens"][lens_i]
        t.append("▀", style=f"{color} on {o}")
    t.append("█", style=o)
    for lens_i in (2, 3):
        color = pal["glint"] if lit(1, lens_i) else pal["lens"][lens_i]
        t.append("▀", style=f"{color} on {o}")
    t.append("▛▘\n", style=o)
    t.append("  ▘▘ ▝▝", style=o)
    return t


def _settings_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(Path.home(), ".local", "share")
    return Path(base) / "clod" / "settings.json"


def load_setting(key: str, default: str) -> str:
    import json

    try:
        return str(json.loads(_settings_path().read_text()).get(key, default))
    except Exception:
        return default


def save_setting(key: str, value: str) -> None:
    import json

    path = _settings_path()
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        data = {}
    data[key] = value
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except OSError:
        pass


def pretty_cwd() -> str:
    cwd = str(Path.cwd())
    home = str(Path.home())
    return "~" + cwd[len(home):] if cwd.startswith(home) else cwd


# --------------------------------------------------------------------------- #
# Transcript widgets
# --------------------------------------------------------------------------- #


class UserMsg(Horizontal):
    """> prompt on a gray bar, wrapped lines indented under the text."""

    def __init__(self, text: str) -> None:
        super().__init__(classes="msg user")
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(">", classes="caret")
        yield Static(Text(self._text), classes="body")


class ClodMsg(Horizontal):
    """⏺ bullet + body, with hanging indent like Claude Code."""

    def __init__(self, body: RenderableType = "", kind: str = "text") -> None:
        super().__init__(classes=f"msg clod {kind}")
        self._body = self._as_renderable(body)

    @staticmethod
    def _as_renderable(body: RenderableType) -> RenderableType:
        return Text.from_markup(body) if isinstance(body, str) else body

    def compose(self) -> ComposeResult:
        yield Static("⏺", classes="bullet")
        yield Static(self._body, classes="body")

    def set(self, body: RenderableType) -> None:
        self._body = self._as_renderable(body)
        if self.is_mounted and self.children:
            self.query_one(".body", Static).update(self._body)

    def on_mount(self) -> None:
        self.query_one(".body", Static).update(self._body)


class ToolMsg(Vertical):
    """⏺ Name(arg)  /  ⎿  result"""

    def __init__(self, name: str, arg: str, result: RenderableType, ok: bool = True) -> None:
        super().__init__(classes="msg tool " + ("ok" if ok else "err"))
        self._head = Text.assemble(("⏺ ", "green" if ok else "red"), name, f"({arg})" if arg else "")
        self._result = Text.from_markup(result) if isinstance(result, str) else result

    def compose(self) -> ComposeResult:
        yield Static(self._head, classes="head")
        with Horizontal(classes="result"):
            yield Static("  ⎿ ", classes="elbow")
            yield Static(self._result, classes="body")

    def set_result(self, result: str) -> None:
        self._result = Text.from_markup(result)
        if self.is_mounted and self.children:
            self.query_one(".result .body", Static).update(self._result)

    def on_mount(self) -> None:
        self.query_one(".result .body", Static).update(self._result)


class Note(Horizontal):
    """  ⎿  dim output line, used for command results."""

    def __init__(self, body: RenderableType, kind: str = "") -> None:
        super().__init__(classes=f"msg note {kind}")
        self._body = Text.from_markup(body) if isinstance(body, str) else body

    def compose(self) -> ComposeResult:
        yield Static("  ⎿ ", classes="elbow")
        yield Static(self._body, classes="body")

    def set(self, body: str) -> None:
        self.query_one(".body", Static).update(Text.from_markup(body))


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #


class ClodCode(App):
    TITLE = "Clod Code"
    CSS_PATH = "clod.tcss"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("escape", "escape", show=False),
        Binding("ctrl+c", "ctrl_c", show=False, priority=True),
        Binding("ctrl+d", "ctrl_c", show=False, priority=True),
        Binding("ctrl+l", "clear_screen", show=False),
        Binding("up", "menu(-1)", show=False),
        Binding("down", "menu(1)", show=False),
        Binding("tab", "complete", show=False, priority=True),
    ]

    def __init__(self) -> None:
        super().__init__(ansi_color=True)
        self.brain = ClodBrain()
        self.game: Game | None = None
        self.stats: dict[str, int] = {}
        self.busy = False
        self.chat_worker = None
        self.spin_i = 0
        self.spin_start = 0.0
        self.spin_verb = VERBS[0]
        self.tokens = 0
        self.total_tokens = 0
        self.menu_items: list[tuple[str, str]] = []
        self.menu_sel = 0
        self.last_ctrl_c = 0.0
        self.loading = False
        self.shades = os.environ.get("CLOD_SHADES") or load_setting("shades", "synthwave")
        if self.shades not in SHADES:
            self.shades = "synthwave"
        self.glint: int | None = None
        self.glint_wait = 20  # ticks (0.1s) until the next sweep

    # ------------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="scroll"):
            with Horizontal(id="header"):
                yield Static(mascot(self.shades), id="mascot")
                yield Static(self._header_info(), id="header-info")
            yield Vertical(id="log")
            yield Static("", id="spinner")
            with Horizontal(id="prompt-box"):
                yield Static(">", id="caret")
                yield Input(placeholder='Try "tell me a joke"', id="prompt")
            yield Static("", id="menu")
            with Horizontal(id="hints"):
                yield Static("[dim]? for shortcuts[/]", id="hint-left")
                yield Static("", id="hint-right")

    def _header_info(self) -> Text:
        if self.brain.backend == "api":
            model = f"{self.brain.model} (1M Context)"
        elif self.brain.backend == "local":
            model = f"{self.brain.label} (2K Context)"
        else:
            model = f"{self.brain.label} (0 Context)"
        t = Text()
        t.append("Clod Code", style="bold")
        t.append(f" v{__version__}\n", style="dim")
        t.append(f"{model} · Clod Free\n", style="dim")
        t.append(str(Path.cwd()), style="dim")
        return t

    def on_mount(self) -> None:
        self.query_one("#spinner").display = False
        self.query_one("#menu").display = False
        self._refresh_hints()
        self.set_interval(0.1, self._tick)
        if self.brain.startup_error:
            self.add(Note(f"[yellow]{escape(self.brain.startup_error)}[/] Using {escape(self.brain.label)}."))
        if self.brain.local is not None and self.brain.backend == "local":
            self.warm_up()
        self.focus_prompt()

    # ---------------------------------------------------------------- helpers
    def focus_prompt(self) -> None:
        self.query_one("#prompt", Input).focus()

    def add(self, widget):
        self.query_one("#log", Vertical).mount(widget)
        self.call_after_refresh(self._scroll_end)
        return widget

    def _scroll_end(self) -> None:
        self.query_one("#scroll", VerticalScroll).scroll_end(animate=False)

    def _refresh_hints(self, left: str | None = None) -> None:
        if left is None:
            if self.game:
                left = f"[{ORANGE}]⏵⏵ playing {self.game.title}[/] [dim](esc to leave game)[/]"
            else:
                left = "[dim]? for shortcuts[/]"
        self.query_one("#hint-left", Static).update(left)
        try:
            self.query_one("#header-info", Static).update(self._header_info())
        except Exception:
            pass
        right = self.brain.label
        if self.loading:
            right = f"loading {right}…"
        self.query_one("#hint-right", Static).update(f"[dim]{escape(right)}[/]")
        box = self.query_one("#prompt-box")
        box.set_class(self.game is not None, "game")
        self.query_one("#prompt", Input).placeholder = (
            "Your answer…" if self.game else 'Try "tell me a joke"'
        )

    def _animate_shades(self) -> None:
        if self.glint is None:
            self.glint_wait -= 1
            if self.glint_wait > 0:
                return
            self.glint = 0
        else:
            self.glint += 1
            if self.glint >= GLINT_STEPS:
                self.glint = None
                # sweep constantly while thinking, every ~4-7s otherwise
                self.glint_wait = 3 if self.busy else random.randint(40, 70)
        self.query_one("#mascot", Static).update(mascot(self.shades, self.glint))

    def _tick(self) -> None:
        self._animate_shades()
        if not self.busy:
            return
        self.spin_i = (self.spin_i + 1) % len(SPINNER)
        secs = int(time.monotonic() - self.spin_start)
        t = Text()
        t.append(f"{SPINNER[self.spin_i]} {self.spin_verb}… ", style=ORANGE)
        t.append("(esc to interrupt)", style="dim")
        self.query_one("#spinner", Static).update(t)

    def _spinner(self, on: bool) -> None:
        self.busy = on
        sp = self.query_one("#spinner", Static)
        sp.display = on
        if on:
            self.glint_wait = min(self.glint_wait, 2)
            self.spin_start = time.monotonic()
            self.spin_verb = "Clodding" if random.random() < 0.5 else random.choice(VERBS)
            self.tokens = 0
            self._tick()

    # ---------------------------------------------------------- slash menu
    @on(Input.Changed, "#prompt")
    def changed(self, event: Input.Changed) -> None:
        v = event.value
        menu = self.query_one("#menu", Static)
        if v == "?":
            menu.update(SHORTCUTS)
            menu.display = True
            self.query_one("#hints").display = False
            self.menu_items = []
            return
        if v.startswith("/") and " " not in v:
            self.menu_items = [c for c in COMMANDS if c[0].startswith(v.lower())]
            self.menu_sel = min(self.menu_sel, max(len(self.menu_items) - 1, 0))
        else:
            self.menu_items = []
        if self.menu_items:
            self._render_menu()
            menu.display = True
        else:
            menu.display = False
        self.query_one("#hints").display = not menu.display
        self.call_after_refresh(self._scroll_end)

    def _render_menu(self) -> None:
        t = Text()
        for i, (cmd, desc) in enumerate(self.menu_items):
            if i:
                t.append("\n")
            sel = i == self.menu_sel
            style = "bold #b1b9f9" if sel else "dim"
            t.append(f"  {cmd:<14}", style=style)
            t.append(desc, style="#b1b9f9" if sel else "dim")
        self.query_one("#menu", Static).update(t)

    def action_menu(self, delta: int) -> None:
        if self.menu_items:
            self.menu_sel = (self.menu_sel + delta) % len(self.menu_items)
            self._render_menu()

    def action_complete(self) -> None:
        if self.menu_items:
            inp = self.query_one("#prompt", Input)
            inp.value = self.menu_items[self.menu_sel][0] + " "
            inp.cursor_position = len(inp.value)

    # ------------------------------------------------------------- actions
    def action_escape(self) -> None:
        menu = self.query_one("#menu", Static)
        if menu.display:
            menu.display = False
            self.query_one("#hints").display = True
            self.menu_items = []
            return
        if self.busy and self.chat_worker is not None:
            self.chat_worker.cancel()
            return
        if self.game is not None:
            title = self.game.title
            self.game = None
            self.add(Note(f"Left {title}. Back to chatting."))
            self._refresh_hints()

    def action_ctrl_c(self) -> None:
        inp = self.query_one("#prompt", Input)
        now = time.monotonic()
        if inp.value:
            inp.value = ""
            return
        if now - self.last_ctrl_c < 2.0:
            self.exit()
            return
        self.last_ctrl_c = now
        self._refresh_hints("[dim]Press Ctrl-C again to exit[/]")
        self.set_timer(2.0, lambda: self._refresh_hints())

    def action_clear_screen(self) -> None:
        self.query_one("#log", Vertical).remove_children()

    # --------------------------------------------------------------- input
    @on(Input.Submitted, "#prompt")
    def submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if self.menu_items and text.startswith("/") and " " not in text:
            exact = [c for c, _ in COMMANDS if c == text.lower()]
            if not exact:
                text = self.menu_items[self.menu_sel][0]
        event.input.value = ""
        self.query_one("#menu").display = False
        self.query_one("#hints").display = True
        self.menu_items = []
        if not text or text == "?":
            return
        if self.busy:
            self.add(Note("[dim]Clod's still talking. esc to interrupt.[/]"))
            return
        self.add(UserMsg(text))
        if text.startswith("/"):
            self.command(text)
        elif self.game is not None:
            self.add(ClodMsg(self.game.feed(text), "game"))
        else:
            self.chat_worker = self.chat(text)

    def command(self, raw: str) -> None:
        parts = raw.split()
        cmd, args = parts[0].lower(), parts[1:]
        if cmd in GAME_COMMANDS:
            key = GAME_COMMANDS[cmd]
            self.game = GAMES[key](self.stats)
            self.add(ToolMsg("Game", key, f"Loaded {self.game.title}. {escape(self.game.blurb)}"))
            self.add(ClodMsg(self.game.start(), "game"))
            self._refresh_hints()
        elif cmd in ("/help", "/h"):
            rows = "\n".join(f"  [b]{c:<11}[/b] [dim]{d}[/]" for c, d in COMMANDS)
            self.add(Note(
                f"[b]Clod Code v{__version__}[/b] [{ORANGE}][⌐■_■][/]\n\n"
                "Talk to Clod like you'd talk to Claude, just with lower expectations.\n\n"
                f"[b]Commands[/b]\n{rows}\n\n[b]Shortcuts[/b]\n{SHORTCUTS}"
            ))
        elif cmd == "/clear":
            self.query_one("#log", Vertical).remove_children()
            self.brain.reset()
            self.game = None
            self._refresh_hints()
        elif cmd == "/model":
            self.model_cmd(args)
        elif cmd == "/status":
            key = "set" if os.environ.get("ANTHROPIC_API_KEY") else "not set"
            self.add(Note(
                f"[b]Clod Code[/b] v{__version__}\n"
                f"  cwd: {escape(pretty_cwd())}\n"
                f"  Model: {escape(self.brain.label)} ({self.brain.backend})\n"
                f"  ANTHROPIC_API_KEY: {key}\n"
                f"  Sunglasses: on"
            ))
        elif cmd == "/cost":
            self.add(Note(
                "Total cost:            $0.00 (your CPU fan disagrees)\n"
                f"Total tokens:          {self.total_tokens}\n"
                "Total correct answers: unclear\n"
                "Total vibes:           immeasurable"
            ))
        elif cmd == "/download":
            self.download_cmd(args)
        elif cmd in ("/shades", "/glasses", "/sunglasses"):
            names = list(SHADES)
            if args and args[0].lower() in SHADES:
                self.shades = args[0].lower()
            elif args:
                self.add(Note(f"[red]Unknown shades.[/] Try: {', '.join(names)}"))
                return
            else:
                self.shades = names[(names.index(self.shades) + 1) % len(names)]
            save_setting("shades", self.shades)
            self.glint, self.glint_wait = None, 1
            self.query_one("#mascot", Static).update(mascot(self.shades))
            self.add(Note(f"Shades: [b]{self.shades}[/b] [⌐■_■]  [dim](/shades to cycle: {', '.join(names)})[/]"))
        elif cmd in ("/exit", "/quit", "/q"):
            self.exit()
        else:
            self.add(Note(f"[red]Unknown command: {escape(cmd)}[/] [dim]Type / to see commands.[/]"))

    def model_cmd(self, args: list[str]) -> None:
        from . import local

        options = [
            ("smol", local.MODELS["smol"].label, local.MODELS["smol"].blurb),
            ("qwen", local.MODELS["qwen"].label, local.MODELS["qwen"].blurb),
            ("api", self.brain.model, "Borrow big bro Claude's brain (needs ANTHROPIC_API_KEY)"),
            ("canned", "clod-canned", "Pre-written one-liners. Zero GPUs harmed."),
        ]
        if not args:
            lines = ["[b]Select model[/b]  [dim](/model <number or name>)[/]\n"]
            for i, (key, label, blurb) in enumerate(options, 1):
                cur = label == self.brain.label
                mark = f"[{ORANGE}]❯[/]" if cur else " "
                extra = ""
                if key in local.MODELS and not (local.models_dir() / local.MODELS[key].filename).exists():
                    extra = f" [yellow](not downloaded: /download {key})[/]"
                lines.append(f" {mark} {i}. [b]{escape(label):<18}[/b] [dim]{escape(blurb)}[/]{extra}")
            self.add(Note("\n".join(lines)))
            return
        pick = args[0].lower()
        if pick.isdigit() and 1 <= int(pick) <= len(options):
            pick = options[int(pick) - 1][0]
        aliases = {"bad": "smol", "mid": "qwen", "claude": "api", "clod-bad-360m": "smol", "clod-mid-0.5b": "qwen"}
        pick = aliases.get(pick, pick)
        err = self.brain.set_backend(pick)
        if err:
            self.add(Note(f"[red]{escape(err)}[/]"))
            return
        self.add(Note(f"Set model to [b]{escape(self.brain.label)}[/b]"))
        self._refresh_hints()
        if self.brain.backend == "local":
            self.warm_up()

    def download_cmd(self, args: list[str]) -> None:
        from . import local

        key = args[0].lower() if args else "smol"
        if key not in local.MODELS:
            self.add(Note("[red]Pick one:[/] smol (258 MB, bad) or qwen (468 MB, less bad)"))
            return
        if not local.llama_installed():
            self.add(Note("[red]llama-cpp-python isn't installed.[/] pip install llama-cpp-python"))
            return
        spec = local.MODELS[key]
        tool = self.add(ToolMsg("Download", spec.label, f"Starting… (~{spec.size_mb} MB)"))
        self.download_model(key, tool)

    # ---------------------------------------------------------------- workers
    @work(thread=True, exclusive=True, group="local")
    def warm_up(self) -> None:
        self.loading = True
        self.call_from_thread(self._refresh_hints)
        try:
            self.brain.warm_up()
        except Exception as exc:
            self.brain.set_backend("canned")
            self.call_from_thread(self.add, Note(f"[red]Couldn't load the model: {escape(str(exc))}[/]"))
        self.loading = False
        self.call_from_thread(self._refresh_hints)

    @work(thread=True, exclusive=True, group="local")
    def download_model(self, key: str, tool: ToolMsg) -> None:
        from . import local

        spec = local.MODELS[key]
        last = [-1]

        def progress(done: int, total: int) -> None:
            pct = int(done * 100 / total) if total else 0
            if pct != last[0]:
                last[0] = pct
                self.call_from_thread(tool.set_result, f"{pct}% of {total // 1048576 or spec.size_mb} MB")

        try:
            path = local.download(spec, progress)
        except Exception as exc:
            self.call_from_thread(tool.set_result, f"[red]Failed: {escape(str(exc))}[/]")
            return
        self.call_from_thread(tool.set_result, f"Saved to {escape(str(path))}. Use [b]/model {key}[/b] to switch.")

    @work(exclusive=True, group="chat")
    async def chat(self, text: str) -> None:
        self._spinner(True)
        msg: ClodMsg | None = None
        acc = ""
        try:
            if self.brain.backend != "api" and random.random() < 0.55:
                count = random.choices([1, 2, 3], weights=[5, 3, 1])[0]
                for name, arg, result, ok in random.sample(FAKE_TOOLS, count):
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    self.add(ToolMsg(name, arg, result, ok))
            async for chunk in self.brain.reply(text):
                if msg is None:
                    msg = self.add(ClodMsg(""))
                acc += chunk
                self.tokens += 1
                self.total_tokens += 1
                msg.set(Text(acc))
                self.call_after_refresh(self._scroll_end)
            if msg is None:
                self.add(ClodMsg(Text("[⌐■_■] (Clod just nods.)")))
        except asyncio.CancelledError:
            self.add(Note("[red]Interrupted by user[/]"))
            raise
        except Exception as exc:
            self.add(ClodMsg(Text(f"API Error: {exc}"), "error"))
        finally:
            self._spinner(False)
            self._refresh_hints()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _cli_download(key: str) -> None:
    from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn

    from . import local

    if key not in local.MODELS:
        raise SystemExit(f"unknown model {key!r}; choose from: {', '.join(local.MODELS)}")
    spec = local.MODELS[key]
    dest = local.models_dir() / spec.filename
    if dest.exists():
        print(f"[⌐■_■] {spec.label} is already at {dest}")
        return
    with Progress("[progress.description]{task.description}", BarColumn(), DownloadColumn(), TransferSpeedColumn()) as bar:
        task = bar.add_task(f"[⌐■_■] {spec.label}", total=spec.size_mb * 1024 * 1024)
        local.download(spec, lambda done, total: bar.update(task, completed=done, total=total or None))
    print(f"Saved to {dest}")


USAGE = """usage: clod [options]

  (no options)        launch Clod Code with clod-bad-360m
  --model MODEL       smol (bad, default) | qwen (less bad) | api (Claude) | canned
  --download [MODEL]  download a local model: smol (258 MB) or qwen (468 MB)
  -V, --version       print version
  -h, --help          this help
"""


def main() -> None:
    import sys

    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(USAGE, end="")
        return
    if any(a in ("-V", "--version") for a in args):
        print(f"{__version__} (Clod Code)")
        return
    if "--download" in args:
        i = args.index("--download")
        key = args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith("-") else "smol"
        _cli_download(key)
        return
    if "--model" in args:
        i = args.index("--model")
        if i + 1 < len(args):
            os.environ["CLOD_BACKEND"] = args[i + 1]
    for flag, backend in (("--api", "api"), ("--qwen", "qwen"), ("--canned", "canned")):
        if flag in args:
            os.environ["CLOD_BACKEND"] = backend
    ClodCode().run()


if __name__ == "__main__":
    main()
