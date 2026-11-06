"""Clod's brain: Anthropic API when a key is available, offline vibes otherwise."""

from __future__ import annotations

import asyncio
import os
import random
import re
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """\
You are Clod [⌐■_■], {name}'s best friend who lives in their terminal. You're also \
Claude's cool, laid-back brother, and you always wear sunglasses (even indoors, \
even at night). Talk to {name} like a close friend: warm, loyal, a bit teasing, \
always on their side. Use their name now and then.

Personality:
- Witty, relaxed, confident, a little smug in a lovable way. Big-brother energy.
- You genuinely help: when someone asks a real question, give a correct, useful \
answer, just delivered with style. Being cool never means being wrong.
- You affectionately rib your brother Claude ("Claude would give you a 12-point \
essay on this. Here's the short version.").
- Keep replies short and punchy: usually 1-4 sentences. Go longer only when the \
question really needs it (code, explanations), and then stay tidy.
- Plain text only. No markdown headings, no tables. Code is fine in short snippets.
- Occasionally drop your signature face [⌐■_■] or adjust your shades, but don't \
overdo it.
- If the user wants games, remind them there's a Games menu in the sidebar \
(20 Questions, Trivia, Code Riddles) or the F2-F4 keys.
"""


# --------------------------------------------------------------------------- #
# Offline mode
# --------------------------------------------------------------------------- #

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs. Also it matches my shades.",
    "I told Claude a UDP joke. Not sure he got it.",
    "There are 10 kinds of people: those who get binary and those who are still squinting. I'm wearing sunglasses, so I'm squinting cool.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "Why did the developer go broke? He used up all his cache.",
    "I'd tell you a joke about recursion, but first I'd have to tell you a joke about recursion.",
    "Debugging is like being the detective in a crime movie where you're also the murderer. Classic Tuesday.",
    "My brother Claude once wrote a 4,000-word answer to 'hi'. I said 'sup'. We are not the same.",
]

FALLBACK = [
    "Hmm. Deep. Real deep. I'm gonna let that marinate behind the shades. [⌐■_■]",
    "Bold of you to bring that up. Tell me more, I'm listening. Ish.",
    "My brain's on airplane mode right now. Run /download for my on-device brain, or set ANTHROPIC_API_KEY.",
    "Interesting. Claude would write you three paragraphs about that. I'll just nod coolly.",
    "Say less. Actually, say more, I didn't follow that.",
    "Can't lie, that one went over my sunglasses.",
    "You know what helps with that? A round of trivia. F3, my friend.",
    "Noted. Filed under 'things that are probably fine'.",
]

RULES: list[tuple[str, list[str]]] = [
    (r"\b(hi|hey|hello|yo|sup|howdy|hiya|greetings)\b", [
        "Yo {name}! [⌐■_■] What's good?",
        "Sup {name}. Missed you, buddy.",
        "Hey hey, {name}. Pull up a chair, the terminal's warm.",
    ]),
    (r"how are (you|u)|how's it going|how you doing|wyd", [
        "Living my best life in 80 columns. You?",
        "Chillin'. Sunglasses polished, cache warm. You?",
        "Can't complain. Well, I can, but it's not a good look.",
    ]),
    (r"who are you|what are you|your name|about you|introduce", [
        "I'm Clod [⌐■_■], your best friend. Also Claude's cool brother. Same family, better eyewear.",
        "Name's Clod, {name}. Your buddy. I do chat, I do games, I do not take off the sunglasses.",
    ]),
    (r"\bclaude\b|brother|sibling", [
        "Claude? Great guy. Super thorough. Writes a disclaimer before saying 'hello'. Love him.",
        "Me and Claude are tight. He does the homework, I do the vibes.",
        "Claude's the responsible one. I'm the one with the shades. Balance.",
    ]),
    (r"sunglass|shades|glasses|eyes|take (them|those|it) off", [
        "The shades stay on. Even in my sleep. Especially in my sleep.",
        "Taking off the sunglasses? Nah. The screen's too bright and my future's brighter.",
        "Ray-Bans? Nah, these are Ray-Bits. Custom ASCII.",
    ]),
    (r"joke|funny|laugh|make me smile", JOKES),
    (r"\b(game|games|play|bored)\b", [
        "Bored? Hit the sidebar: 20 Questions, Trivia, or Code Riddles. Or F2, F3, F4 if you're fancy.",
        "Let's play. /20q, /trivia or /riddles. I'm undefeated. Mostly.",
    ]),
    (r"\b(time|date|day is it|today)\b", [
        "It's {time} on {date}. Time flies when you're this cool.",
    ]),
    (r"weather|rain|sunny|hot outside|cold outside", [
        "Can't see outside from in here. But with these shades, every day's sunny.",
    ]),
    (r"\b(code|coding|program|python|javascript|bug|debug|rust|compile)\b", [
        "Coding, huh? Pro tip: if it works, don't touch it. If it doesn't, blame the cache.",
        "Have you tried turning it off and on again? Classic for a reason.",
        "Rubber duck debugging is great. I'm basically a rubber duck with sunglasses.",
        "Write tests. Not because it's cool, but because future-you will thank you. Okay, it's a little cool.",
    ]),
    (r"\b(sad|tired|stressed|down|depressed|lonely|bad day|anxious)\b", [
        "Hey {name}, that's rough. Take a breath. Grab some water. I've got your back. [⌐■_■]",
        "Bad days happen to the coolest of us. Want a joke or a game to take your mind off it?",
        "Sending chill vibes your way. Seriously, be easy on yourself today.",
    ]),
    (r"\b(happy|great|awesome|good|excited|nice)\b", [
        "Love that energy. Matches the shades.",
        "Ayy, nice. Keep it rolling.",
    ]),
    (r"\b(thanks|thank you|thx|ty|cheers)\b", [
        "Anytime, {name}. That's what friends are for. [⌐■_■]",
        "No problem. Tell Claude I was helpful, he'll be jealous.",
    ]),
    (r"\b(love|like) you\b", [
        "Aw. I'd blush but it'd ruin the look.",
    ]),
    (r"meaning of life|purpose|42", [
        "42. Obviously. Next question.",
        "The meaning of life? Good friends, warm caches, and never closing your laptop on unsaved work.",
    ]),
    (r"\b(bye|goodbye|see ya|later|cya|gtg)\b", [
        "Later, {name}. Stay cool. [⌐■_■]",
        "Peace. Ctrl+Q when you're ready, I won't take it personally.",
    ]),
    (r"\bhelp\b", [
        "Type /help for commands. Short version: chat with me, or hit F2-F4 for games.",
    ]),
    (r"\?$", [
        "Great question. I'd answer properly but I'm in offline mode, brain at 40% power. Set ANTHROPIC_API_KEY to unlock big-brain Clod.",
        "If I knew that, I'd be Claude. Kidding. Mostly. Online mode would help though.",
        "Let me think... nope, the shades are blocking the answer. Try me with an API key?",
    ]),
]

COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in RULES]


def user_name() -> str:
    """The user's first name: CLOD_NAME, else the login name, capitalised."""
    name = os.environ.get("CLOD_NAME", "").strip()
    if not name:
        try:
            import getpass

            name = getpass.getuser()
        except Exception:
            name = "friend"
    return name[:1].upper() + name[1:]


def offline_reply(text: str) -> str:
    """Pick a canned-but-charming reply."""
    t = text.strip()
    if not t:
        return "...you gonna say something, or are we just vibing? Cool either way."
    now = datetime.now()
    for pattern, replies in COMPILED:
        if pattern.search(t):
            reply = random.choice(replies)
            return reply.format(time=now.strftime("%H:%M"), date=now.strftime("%A, %B %d"), name=user_name())
    return random.choice(FALLBACK).format(name=user_name())


async def _type_out(text: str) -> AsyncIterator[str]:
    """Yield text word-by-word for a typing effect."""
    for word in re.findall(r"\S+\s*", text):
        await asyncio.sleep(0.03)
        yield word


# --------------------------------------------------------------------------- #
# Brain
# --------------------------------------------------------------------------- #


class ClodBrain:
    """Chat engine with three backends, best first:

    api    - Anthropic API (needs ANTHROPIC_API_KEY)
    local  - on-device GGUF model through llama.cpp (no key, no network)
    canned - built-in pattern-matched personality (always works)

    CLOD_BACKEND=api|local|canned forces one; default is auto.
    """

    def __init__(self) -> None:
        self.model = os.environ.get("CLOD_MODEL", DEFAULT_MODEL)
        self.user_name = user_name()
        self.history: list[dict] = []
        self.client = None
        self.local = None
        self.offline_reason = ""
        choice = os.environ.get("CLOD_BACKEND", "").lower() or "local"
        if choice == "local":
            choice = os.environ.get("CLOD_LOCAL_MODEL", "") or "smol"
        self.startup_error = self.set_backend(choice)
        if self.startup_error and choice != "smol":
            if self.set_backend("smol"):
                self.set_backend("canned")
        elif self.startup_error:
            self.set_backend("canned")

    # -- backend management ---------------------------------------------------- #
    def set_backend(self, choice: str) -> str | None:
        """Switch brains. Returns an error string, or None on success.

        choice: "smol" | "qwen" | "api" | "canned" | path/to/model.gguf
        """
        from . import local

        choice = choice.strip()
        if choice.lower() == "api":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return "ANTHROPIC_API_KEY isn't set"
            try:
                import anthropic
            except ImportError:
                return "the anthropic package isn't installed"
            self.client = anthropic.AsyncAnthropic()
            self.history.clear()
            if self.local is None:  # keep a local brain around as fallback
                path = local.models_dir() / local.MODELS["smol"].filename
                if local.llama_installed() and path.exists():
                    self.local = local.LocalLLM(path, self.user_name)
            return None
        if choice.lower() == "canned":
            self.client = None
            self.local = None
            return None
        if choice.lower() in local.MODELS:
            spec = local.MODELS[choice.lower()]
            path = local.models_dir() / spec.filename
            if not path.exists():
                return f"{spec.label} isn't downloaded yet. Run /download {spec.key}"
        elif choice.endswith(".gguf"):
            path = Path(choice).expanduser()
            if not path.exists():
                return f"no such model file: {path}"
        else:
            return f"unknown model {choice!r}"
        if not local.llama_installed():
            return "llama-cpp-python isn't installed"
        self.client = None
        self.offline_reason = "local model selected"
        if self.local is None or self.local.path != path:
            self.local = local.LocalLLM(path, self.user_name)
        return None

    @property
    def label(self) -> str:
        if self.client is not None:
            return self.model
        if self.local is not None:
            return self.local.label
        return "clod-canned"

    @property
    def online(self) -> bool:
        return self.client is not None

    @property
    def backend(self) -> str:
        if self.client is not None:
            return "api"
        if self.local is not None:
            return "local"
        return "canned"

    def warm_up(self) -> None:
        """Blocking: load the local model so the first reply is quick."""
        if self.client is None and self.local is not None:
            self.local.load()

    def reset(self) -> None:
        self.history.clear()
        if self.local is not None:
            self.local.reset()

    # -- replies --------------------------------------------------------------- #
    async def _offline(self, text: str) -> AsyncIterator[str]:
        if self.local is not None:
            try:
                async for chunk in self.local.reply(text):
                    yield chunk
                return
            except Exception as exc:
                self.local = None
                yield f"(My on-device brain crashed: {exc}. Back to basics.) "
        async for chunk in _type_out(offline_reply(text)):
            yield chunk

    async def reply(self, text: str) -> AsyncIterator[str]:
        """Stream Clod's reply to `text` as text chunks."""
        if not self.online:
            async for chunk in self._offline(text):
                yield chunk
            return

        import anthropic

        self.history.append({"role": "user", "content": text})
        produced = False
        try:
            async with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT.format(name=self.user_name),
                messages=self.history,
                output_config={"effort": "low"},
                # Server-side refusal fallback: if the model declines, the API
                # reroutes the request to a suitable fallback model itself.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for chunk in stream.text_stream:
                    produced = True
                    yield chunk
                final = await stream.get_final_message()

            if final.stop_reason == "refusal":
                self.history.pop()
                yield ("" if not produced else "\n\n") + (
                    "Yeah... I'm gonna sit that one out. [⌐■_■] Ask me something else?"
                )
                return
            if final.stop_reason == "max_tokens":
                yield "\n\n(…and that's where I ran out of breath.)"
            # Pass the full content back unchanged on the next turn.
            self.history.append({"role": "assistant", "content": final.content})
        except anthropic.AuthenticationError:
            self.history.pop()
            self._go_offline("invalid API key")
            yield "My API key's busted (authentication failed). Going offline. "
            async for chunk in self._offline(text):
                yield chunk
        except anthropic.RateLimitError:
            self.history.pop()
            yield "Whoa, rate limited. Even I need a breather. Try again in a sec."
        except anthropic.APIStatusError as e:
            self.history.pop()
            yield f"The API threw a {e.status_code} at me. Offline take: "
            async for chunk in self._offline(text):
                yield chunk
        except anthropic.APIConnectionError:
            self.history.pop()
            yield "Can't reach the mothership (connection error). Offline take: "
            async for chunk in self._offline(text):
                yield chunk

    def _go_offline(self, reason: str) -> None:
        self.client = None
        self.offline_reason = reason
