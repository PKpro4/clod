# Clod Code [⌐■_■]

> **Unofficial parody.** Not affiliated with, endorsed by, or connected to Anthropic.
> "Claude" and "Claude Code" are trademarks of Anthropic, PBC. This is a fan-made joke
> app that pokes affectionate fun at Claude Code's look; the sunglasses-wearing critter is
> a parody of Claude Code's mascot. No Anthropic source code is included.

> Your best friend in the terminal. Claude's cool brother. Wears sunglasses.
> Runs a gloriously bad model on your CPU.

A Claude Code look-alike terminal app, built with [Textual](https://textual.textualize.io/).
It has the same flow: the compact header with the little orange critter (the original,
plus gradient sunglasses with a glint that sweeps across them), name/version, model and path, `> ` prompts on a gray bar, the input
between two rules, `> ` prompts, `⏺` replies with a hanging indent,
`⎿` tool results, a whimsical `✻ Vibing… (3s · ↓ 42 tokens · esc to interrupt)`
spinner, a rounded input box, and a slash-command menu. It uses your terminal's own
colors.

The difference: you get **Clod**, who wears sunglasses and by default runs
**clod-bad-360m** (SmolLM2 360M, 258 MB) fully offline through llama.cpp. He answers
everything confidently and some of it correctly. He also likes to pretend he's using
tools (`⏺ WebSearch("is this right")  ⎿ Did 0 searches. No internet, sunglasses on.`).

```
 ▐▄▄▄▄▄▌   Clod Code v1.0.0
▝▜▀▀█▀▀▛▘  clod-bad-360m (2K Context) · Clod Free
  ▘▘ ▝▝    ~/clod

> hey clod, can you give me a high-level overview of how cool you are?

⏺ I'll explore my coolness to give you a comprehensive overview.

⏺ Explore(Explore codebase structure)
  ⎿ Done (17 tool uses · 0.0k tokens · 28s) · found: vibes

✻ Clodding… (esc to interrupt)
────────────────────────────────────────────────────────────────
> Try "tell me a joke"
────────────────────────────────────────────────────────────────
  ? for shortcuts                                  clod-bad-360m
```

Clod is *your* friend: he greets you by name (your login name, or set `CLOD_NAME`)
and talks to you like a buddy.

## Install

```bash
cd ~/clod
python3 -m venv .venv
.venv/bin/pip install -e .                       # textual, rich, llama-cpp-python, anthropic
ln -s "$PWD/.venv/bin/clod" ~/.local/bin/clod    # ~/.local/bin must be on PATH
clod --download                                  # fetch clod-bad-360m (258 MB)
clod
```

If pip tries to compile `llama-cpp-python`, use the CPU wheel index:
`pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`.

## Brains

| `/model` | Name | Notes |
|---|---|---|
| 1 / `smol` | clod-bad-360m | **Default.** SmolLM2 360M, 258 MB. Bad. Confident. Fast. |
| 2 / `qwen` | clod-mid-0.5b | Qwen2.5 0.5B, 468 MB (`clod --download qwen`). Less bad. |
| 3 / `api` | claude-opus-5-5 | Borrows big bro's brain. Needs `ANTHROPIC_API_KEY`. |
| 4 / `canned` | clod-canned | Pre-written one-liners, no model at all. |

Launch with a different brain: `clod --model qwen`, `clod --api` or `clod --canned`.
You can also set `CLOD_BACKEND` (`smol`, `qwen`, `api`, `canned` or a path to any chat
`.gguf`). Models live in `~/.local/share/clod/models/`.

## Commands and keys

| Command | |
|---|---|
| `/help` | Help |
| `/clear` | Clear conversation and screen |
| `/model [n\|name]` | Show or switch the brain |
| `/status` · `/cost` | Status, and a very honest cost report |
| `/trivia` · `/20q` · `/riddles` | Mini-games: Trivia (A-D), 20 Questions (he learns), Code Riddles |
| `/download [smol\|qwen]` | Download a local model |
| `/shades [style]` | Swap Clod's sunglasses: synthwave (default), aviator, ice, toxic, classic. Saved between runs |
| `/exit` | Quit |

Keys:
- `/` opens the command menu (`↑`/`↓` to move, `Tab` to complete, `Enter` to run).
- `?` shows shortcuts.
- `Esc` interrupts Clod, closes the menu, or leaves a game.
- `Ctrl+C` twice exits.
- `Ctrl+L` clears the screen.

## Layout

```
clod/
├── README.md · requirements.txt · pyproject.toml · run.py
└── clod/
    ├── app.py        # Clod Code UI (transcript widgets, spinner, slash menu, CLI)
    ├── clod.tcss     # styles (ansi colors + one orange accent)
    ├── brain.py      # persona, brain switching, Anthropic API streaming, canned replies
    ├── local.py      # llama.cpp model download/load/stream
    └── games/        # trivia, twenty_questions (persists what it learns), riddles
```

## License

[MIT](LICENSE) for the code in this repo. The on-device models are downloaded at runtime
from Hugging Face and keep their own licenses: SmolLM2 and Qwen2.5 are both Apache-2.0.
