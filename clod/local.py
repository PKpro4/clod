"""On-device LLM for Clod, via llama.cpp (llama-cpp-python) and a small GGUF model.

No API key and no network needed once the model file is downloaded.
"""

from __future__ import annotations

import asyncio
import os
import threading
import urllib.request
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    key: str
    name: str
    filename: str
    url: str
    size_mb: int
    label: str = ""
    blurb: str = ""


MODELS: dict[str, ModelSpec] = {
    "smol": ModelSpec(
        "smol",
        "SmolLM2 360M Instruct",
        "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        "https://huggingface.co/bartowski/SmolLM2-360M-Instruct-GGUF/resolve/main/SmolLM2-360M-Instruct-Q4_K_M.gguf",
        258,
        "clod-bad-360m",
        "Bad. Confident. Fast. The real Clod experience.",
    ),
    "qwen": ModelSpec(
        "qwen",
        "Qwen2.5 0.5B Instruct",
        "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        468,
        "clod-mid-0.5b",
        "Less bad. Can add numbers. Sometimes.",
    ),
}
DEFAULT_MODEL = "smol"

# A tiny model needs a short, concrete persona and a couple of examples.
def local_system(name: str) -> str:
    return (
        f"You are Clod, {name}'s best friend. You are Claude's cool, laid-back brother "
        f"and you always wear sunglasses. You talk to {name} like a close buddy: warm, "
        "witty, relaxed, a little teasing, always on their side. "
        "Answer in 1-3 short sentences, casual tone. Never use lists or headings."
    )


def few_shot(name: str) -> list[dict]:
    return [
        {"role": "user", "content": "hey who are you?"},
        {"role": "assistant", "content": f"It's me, Clod, your best buddy, {name}. Claude's cooler brother. Same family, better sunglasses."},
        {"role": "user", "content": "what's 12 times 12?"},
        {"role": "assistant", "content": "144. Easy. Didn't even have to take the shades off."},
    ]


HISTORY_TURNS = 6  # user+assistant pairs kept in context


def models_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(Path.home(), ".local", "share")
    return Path(base) / "clod" / "models"


def selected_spec() -> ModelSpec:
    """CLOD_LOCAL_MODEL picks a model; the default is the gloriously bad one."""
    key = os.environ.get("CLOD_LOCAL_MODEL", "").lower()
    return MODELS.get(key, MODELS[DEFAULT_MODEL])


def model_path(spec: ModelSpec | None = None) -> Path:
    """Path of the GGUF to use. CLOD_LOCAL_MODEL may also be a path to any .gguf."""
    custom = os.environ.get("CLOD_LOCAL_MODEL", "")
    if custom.endswith(".gguf"):
        return Path(custom).expanduser()
    return models_dir() / (spec or selected_spec()).filename


def llama_installed() -> bool:
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return False
    return True


def download(spec: ModelSpec, progress: Callable[[int, int], None] | None = None) -> Path:
    """Download `spec` into models_dir(), resumably-safe via a .part file."""
    dest = models_dir() / spec.filename
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(spec.url, headers={"User-Agent": "clod-terminal-buddy"})
    with urllib.request.urlopen(req, timeout=30) as resp, open(part, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while chunk := resp.read(1 << 16):
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    part.replace(dest)
    return dest


class LocalLLM:
    """Thin async wrapper around llama_cpp.Llama with chat history."""

    def __init__(self, path: Path, user_name: str = "friend") -> None:
        self.path = path
        self.user_name = user_name
        self.llm = None
        self.history: list[dict] = []
        self._load_lock = threading.Lock()
        self._gen_lock = threading.Lock()

    @property
    def spec(self) -> ModelSpec | None:
        for spec in MODELS.values():
            if spec.filename == self.path.name:
                return spec
        return None

    @property
    def name(self) -> str:
        return self.spec.name if self.spec else self.path.stem

    @property
    def label(self) -> str:
        return self.spec.label if self.spec else self.path.stem

    @property
    def loaded(self) -> bool:
        return self.llm is not None

    def load(self) -> None:
        """Blocking load; safe to call from several threads."""
        with self._load_lock:
            if self.llm is not None:
                return
            import llama_cpp

            # verbose=False makes llama-cpp-python install its own quiet log
            # handler, so llama.cpp can't scribble over the TUI.
            self.llm = llama_cpp.Llama(
                model_path=str(self.path),
                n_ctx=2048,
                n_threads=max(2, (os.cpu_count() or 4) // 2),
                verbose=False,
            )

    def reset(self) -> None:
        self.history.clear()

    async def reply(self, text: str) -> AsyncIterator[str]:
        if not self.loaded:
            await asyncio.to_thread(self.load)

        self.history.append({"role": "user", "content": text})
        self.history = self.history[-(HISTORY_TURNS * 2 - 1):]
        messages = [
            {"role": "system", "content": local_system(self.user_name)},
            *few_shot(self.user_name),
            *self.history,
        ]

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        stop = threading.Event()

        def worker() -> None:
            try:
                with self._gen_lock:
                    for chunk in self.llm.create_chat_completion(
                        messages=messages,
                        stream=True,
                        max_tokens=220,
                        temperature=0.7,
                        top_p=0.9,
                        repeat_penalty=1.15,
                    ):
                        if stop.is_set():
                            break
                        delta = chunk["choices"][0]["delta"].get("content")
                        if delta:
                            loop.call_soon_threadsafe(queue.put_nowait, delta)
            except Exception as exc:  # surface errors to the async side
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=worker, daemon=True).start()
        acc = ""
        try:
            while (item := await queue.get()) is not None:
                if isinstance(item, Exception):
                    raise item
                if not acc.strip():  # small models love starting lowercase
                    item = item.lstrip()
                    item = item[:1].upper() + item[1:]
                    if not item:
                        continue
                acc += item
                yield item
        finally:
            stop.set()
            if acc.strip():
                self.history.append({"role": "assistant", "content": acc.strip()})
            elif self.history and self.history[-1]["role"] == "user":
                self.history.pop()
