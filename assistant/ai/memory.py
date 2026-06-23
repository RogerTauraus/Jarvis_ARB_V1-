"""
memory.py — Conversation memory for JARVIS.
  • Session memory: fast in-memory store for the current run
  • Persistent history: saved to ~/.jarvis/history.json — survives restarts
  • Context carries across sessions so JARVIS remembers what you talked about
"""

import os
import json
import logging
import threading
import datetime

logger = logging.getLogger(__name__)

MAX_SESSION   = 10   # turns kept in RAM for LLM context (each turn = user+assistant)
MAX_PERSISTED = 50   # turns saved to disk across sessions

_HISTORY_DIR  = os.path.expanduser("~/.jarvis")
_HISTORY_FILE = os.path.join(_HISTORY_DIR, "history.json")

# ── Sensitive pattern filtering ───────────────────────────────────────────────
_SENSITIVE_KEYWORDS = {
    "password", "credit card", "bank", "pin ", "secret", "private key",
    "ssn", "social security", "passport", "card number",
}

def _is_sensitive(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _SENSITIVE_KEYWORDS)


class ConversationMemory:
    """
    Short-term session memory + long-term disk persistence.

    Session window: last MAX_SESSION turns (used for LLM context)
    Persistent store: last MAX_PERSISTED turns written to ~/.jarvis/history.json
    """

    def __init__(self, system_prompt: str = ""):
        self._lock = threading.Lock()
        self._history: list[dict] = []    # session window (in RAM)
        self._system_prompt = system_prompt or (
            "You are JARVIS, a helpful AI voice assistant running on macOS. "
            "Keep responses concise and conversational — they will be spoken aloud. "
            "Avoid markdown, bullet points, or lists. Speak in plain English."
        )
        # Load persisted history on startup
        self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def add(self, role: str, content: str) -> None:
        """Add a message. Saves to disk automatically (non-blocking)."""
        if role not in ("user", "assistant"):
            logger.warning(f"Invalid role: {role}")
            return
        with self._lock:
            self._history.append({"role": role, "content": content})
            # Trim session window
            if len(self._history) > MAX_SESSION * 2:
                self._history = self._history[-(MAX_SESSION * 2):]
        # Async disk write — don't block the voice loop
        threading.Thread(target=self._save, daemon=True).start()

    def get_messages(self) -> list[dict]:
        """Return message list for LLM (system prompt + session window)."""
        with self._lock:
            messages = [{"role": "system", "content": self._system_prompt}]
            messages.extend(self._history)
            return messages

    def get_recent_summary(self, n: int = 5) -> str:
        """Return last n turns as human-readable text for display."""
        with self._lock:
            recent = self._history[-(n * 2):]
        if not recent:
            return "No recent conversation."
        lines = []
        for m in recent:
            prefix = "You" if m["role"] == "user" else "JARVIS"
            lines.append(f"{prefix}: {m['content'][:120]}")
        return "\n".join(lines)

    def clear(self) -> str:
        """Clear both session memory and disk history."""
        with self._lock:
            self._history.clear()
        try:
            os.makedirs(_HISTORY_DIR, exist_ok=True)
            with open(_HISTORY_FILE, "w") as f:
                json.dump([], f)
        except Exception as e:
            logger.warning(f"Could not clear history file: {e}")
        return "Done — conversation history cleared."

    def __len__(self) -> int:
        with self._lock:
            return len(self._history)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Append current session to disk. Non-blocking (called in thread)."""
        try:
            os.makedirs(_HISTORY_DIR, exist_ok=True)
            # Load existing persisted turns
            existing = []
            if os.path.exists(_HISTORY_FILE):
                with open(_HISTORY_FILE, "r") as f:
                    existing = json.load(f)

            with self._lock:
                current = list(self._history)

            # Merge and trim
            merged = existing + [
                {**m, "_ts": datetime.datetime.now().isoformat()}
                for m in current
                if not _is_sensitive(m.get("content", ""))
            ]
            merged = merged[-(MAX_PERSISTED * 2):]

            with open(_HISTORY_FILE, "w") as f:
                json.dump(merged, f, indent=2)
        except Exception as e:
            logger.debug(f"History save error: {e}")

    def _load(self) -> None:
        """Load last MAX_SESSION turns from disk into session window on startup."""
        try:
            if not os.path.exists(_HISTORY_FILE):
                return
            with open(_HISTORY_FILE, "r") as f:
                data = json.load(f)
            # Strip internal fields before adding to session
            loaded = [
                {"role": m["role"], "content": m["content"]}
                for m in data
                if m.get("role") in ("user", "assistant")
                and m.get("content")
            ]
            # Only load last MAX_SESSION turns so LLM context stays tight
            self._history = loaded[-(MAX_SESSION * 2):]
            if self._history:
                logger.info(f"Loaded {len(self._history)} messages from history.")
        except Exception as e:
            logger.debug(f"History load error: {e}")
            self._history = []
