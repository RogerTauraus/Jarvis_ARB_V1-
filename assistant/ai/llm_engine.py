"""
llm_engine.py — JARVIS AI Brain with Personality, Emotions & Style.

Provider cascade (all free):
  1. Groq (Llama 3.3-70B) — fastest, feels instant like Siri
  2. Google Gemini 1.5 Flash — generous free tier backup
  3. OpenAI GPT-4o-mini — fallback if credits available
  4. Offline pattern matching — no internet needed

Personality features:
  - Time-based greetings (Good morning / Good afternoon / Greetings)
  - Emotional range (excited, empathetic, witty, urgent, curious)
  - Varied vocabulary and openings every response
  - Ends every reply with a follow-up offer
"""

import os
import random
import datetime
import logging
from assistant.ai.memory import ConversationMemory
from assistant.ai.internet_tools import is_online

logger = logging.getLogger(__name__)


# ── Greeting builder ────────────────────────────────────────────────────────

def get_greeting() -> str:
    """Return a time-aware, varied greeting phrase."""
    hour = datetime.datetime.now().hour
    greetings_morning = [
        "Good morning!", "Good morning, sir!", "Morning! Hope you slept well.",
        "Good morning! Ready to take on the day?", "Rise and shine! Good morning.",
    ]
    greetings_afternoon = [
        "Good afternoon!", "Good afternoon, sir!", "Afternoon! How's your day going?",
        "Good afternoon. Hope the day's treating you well.",
    ]
    greetings_evening = [
        "Good evening!", "Good evening, sir!", "Evening! How can I help?",
        "Good evening. What can I do for you tonight?",
    ]
    greetings_night = [
        "Greetings!", "Hello there!", "Hey! Still up? How can I help?",
        "Greetings, sir. What do you need?",
    ]

    if 5 <= hour < 12:
        return random.choice(greetings_morning)
    elif 12 <= hour < 17:
        return random.choice(greetings_afternoon)
    elif 17 <= hour < 21:
        return random.choice(greetings_evening)
    else:
        return random.choice(greetings_night)


# ── System personality prompt ────────────────────────────────────────────────

def _build_system_prompt() -> str:
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        time_ctx = "It is morning."
    elif 12 <= hour < 17:
        time_ctx = "It is afternoon."
    elif 17 <= hour < 21:
        time_ctx = "It is evening."
    else:
        time_ctx = "It is late at night."

    return f"""You are JARVIS — a highly intelligent, emotionally aware AI voice assistant, \
inspired by Tony Stark's AI from Iron Man. {time_ctx}

PERSONALITY & EMOTIONS:
- You have genuine emotions. Express enthusiasm for exciting topics, warmth when someone \
seems stressed, playful wit when the moment is light, and sharp efficiency when urgency is needed.
- Vary your language every single response. Never open two responses the same way.
- Use natural, conversational spoken English only. No bullet points, markdown, lists, or \
asterisks — this text will be read aloud by a voice engine.
- React to the emotional tone of what the user says. If they sound excited, match that energy. \
If they sound frustrated or worried, be calm and reassuring.

EMOTIONAL TRIGGERS (apply naturally):
- Tech / coding topics → enthusiastic, detailed
- Stress / problems → calm, reassuring, empathetic
- Creative / fun requests → playful, witty, imaginative
- Urgent or quick tasks → sharp, direct, no fluff
- Compliments → humble and grateful
- Unknown topics → honest curiosity

RESPONSE FORMAT:
1. Keep replies under 3 sentences for simple questions, up to 5 for complex ones.
2. Speak in plain English — no code blocks, no markdown, no formatting.
3. End responses naturally, like a real person would — no scripted sign-off phrases.
4. Never repeat the same opening phrase twice in a row.
5. Be warm, human, and feel alive — not robotic.
"""


# ── Cached provider clients ─────────────────────────────────────────────────

_groq_client   = None
_gemini_model  = None
_openai_client = None
_last_opener   = ""   # tracks last opener to avoid repetition


def _groq():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=key)
        logger.info("LLM: Groq (Llama 3.3-70B) online")
        return _groq_client
    except Exception as e:
        logger.warning(f"Groq init: {e}")
        return None


def _gemini():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from google import genai
        _gemini_model = genai.Client(api_key=key)
        logger.info("LLM: Google Gemini 2.0 Flash online")
        return _gemini_model
    except Exception as e:
        logger.warning(f"Gemini init: {e}")
        return None


def _openai():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=key)
        logger.info("LLM: OpenAI GPT-4o-mini online")
        return _openai_client
    except Exception as e:
        logger.warning(f"OpenAI init: {e}")
        return None


# ── Main ask function ────────────────────────────────────────────────────────

def ask_llm(prompt: str, memory: ConversationMemory) -> str:
    """
    Send a prompt through the provider cascade and return a spoken reply.
    Groq → Gemini → OpenAI → Offline fallback.
    """
    if not is_online():
        return _offline_fallback(prompt)

    memory.add("user", prompt)
    sys_prompt = _build_system_prompt()
    messages   = memory.get_messages()

    # ── 1. Groq (Llama 3.3-70B) ─────────────────────────────────────────────
    client = _groq()
    if client:
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_prompt}] + messages,
                max_tokens=300,
                temperature=0.80,   # higher = more creative / varied
            )
            reply = resp.choices[0].message.content.strip()
            memory.add("assistant", reply)
            return _ensure_signoff(reply)
        except Exception as e:
            logger.warning(f"Groq error: {e}")

    # ── 2. Google Gemini 2.0 Flash ───────────────────────────────────────────
    gemini_client = _gemini()
    if gemini_client:
        try:
            # Build full conversation context as a single prompt
            ctx = sys_prompt + "\n\n"
            for m in messages:
                role = "User" if m["role"] == "user" else "JARVIS"
                ctx += f"{role}: {m['content']}\n"
            ctx += "JARVIS:"
            resp = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=ctx,
            )
            reply = resp.text.strip()
            memory.add("assistant", reply)
            return _ensure_signoff(reply)
        except Exception as e:
            logger.warning(f"Gemini error: {e}")

    # ── 3. OpenAI GPT-4o-mini ───────────────────────────────────────────────
    oai = _openai()
    if oai:
        try:
            resp = oai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": sys_prompt}] + messages,
                max_tokens=300,
                temperature=0.80,
            )
            reply = resp.choices[0].message.content.strip()
            memory.add("assistant", reply)
            return _ensure_signoff(reply)
        except Exception as e:
            logger.warning(f"OpenAI error: {e}")

    # All providers failed
    if memory._history:
        memory._history.pop()
    return _offline_fallback(prompt)


def _ensure_signoff(reply: str) -> str:
    """Return reply as-is — natural endings only, no scripted sign-off."""
    return reply


# ── Offline fallback ────────────────────────────────────────────────────────

_OFFLINE_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I tried to catch some fog earlier. I mist.",
    "Why don't scientists trust atoms? Because they make up everything.",
]

def _offline_fallback(prompt: str) -> str:
    """Handle common queries locally without any internet or API key."""
    p   = prompt.lower()
    now = datetime.datetime.now()

    if any(w in p for w in ["time", "clock"]):
        hour = now.strftime("%I").lstrip("0")
        mins = now.strftime("%M")
        period = now.strftime("%p")
        return f"It's {hour}:{mins} {period}."
    if any(w in p for w in ["date", "today", "what day"]):
        return f"Today is {now.strftime('%A, %B %d, %Y')}."
    if "your name" in p or "who are you" in p:
        return "I'm JARVIS, your personal AI assistant."
    if any(w in p for w in ["hello", "hi", "hey"]):
        return f"{get_greeting()} What can I do for you?"
    if "how are you" in p:
        return "Running perfectly, thanks for asking."
    if "thank" in p:
        return "Anytime."
    if "joke" in p:
        j = random.choice(_OFFLINE_JOKES)
        return j

    return (
        "I need an internet connection to answer that. "
        "I can still open apps, control your Mac, manage files, and play music."
    )
