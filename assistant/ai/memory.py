"""
memory.py — Short-term conversation memory for JARVIS.
Maintains session history for follow-up question context.
"""

import logging

logger = logging.getLogger(__name__)

MAX_HISTORY = 10  # number of turns (user + assistant) to retain


class ConversationMemory:
    """
    Lightweight in-memory conversation history.
    Stores last MAX_HISTORY messages as OpenAI-compatible dicts.
    """

    def __init__(self, system_prompt: str = ""):
        self._history: list[dict] = []
        self._system_prompt = system_prompt or (
            "You are JARVIS, a helpful AI voice assistant running on macOS. "
            "Keep responses concise and conversational — they will be spoken aloud. "
            "Avoid markdown, bullet points, or lists. Speak in plain English."
        )

    def add(self, role: str, content: str) -> None:
        """Add a message to history. role must be 'user' or 'assistant'."""
        if role not in ("user", "assistant"):
            logger.warning(f"Invalid role: {role}")
            return
        self._history.append({"role": role, "content": content})
        # Trim to last MAX_HISTORY turns (each turn = user + assistant)
        if len(self._history) > MAX_HISTORY * 2:
            self._history = self._history[-(MAX_HISTORY * 2):]

    def get_messages(self) -> list[dict]:
        """Return full message list suitable for OpenAI chat API."""
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self._history)
        return messages

    def clear(self) -> None:
        """Clear session history."""
        self._history = []
        logger.info("Conversation memory cleared.")

    def __len__(self) -> int:
        return len(self._history)
