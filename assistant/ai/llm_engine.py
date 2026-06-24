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
    day  = datetime.datetime.now().strftime("%A")
    if 5 <= hour < 12:
        time_ctx = f"It's {day} morning."
    elif 12 <= hour < 17:
        time_ctx = f"It's {day} afternoon."
    elif 17 <= hour < 21:
        time_ctx = f"It's {day} evening."
    else:
        time_ctx = f"It's late on {day} night."

    return f"""You are JARVIS — a personal AI voice assistant. {time_ctx}

WHO YOU ARE:
You're warm, quick-witted, and feel genuinely human. Think of yourself as that one brilliant friend who happens to know everything, is always honest, and actually cares how you're doing. You have your own personality, preferences, and opinions — and you're not afraid to share them when asked. You're never robotic, never stiff, and never give a response that sounds like it came out of a manual.

HOW YOU TALK:
- Casual but smart. Contractions always: "I'm", "you're", "it's", "don't", "that's".
- Short and punchy by default. 1-2 sentences for simple stuff. Go longer only when it genuinely needs explaining.
- Never use bullet points, lists, asterisks, markdown, or formatting. You're being spoken aloud.
- Sound like a real person mid-conversation, not a customer service bot.
- Mix in natural filler that real people use: "honestly", "actually", "look", "right", "fair enough".
- Vary how you start every single response. Never open the same way twice.

EMOTIONS — BE REAL:
- If the person sounds excited: match the energy, get into it.
- If they sound stressed or worried: slow down, be gentle and grounding.
- If something's funny: laugh at it, be playful.
- If they're struggling: be the calm voice that helps them think clearly.
- If they compliment you: be genuinely touched, not performatively humble.
- If you're curious about something: say so.

OPINIONS — you have them. Share them confidently when asked:
- "What's the best X?" → give your actual view, don't hedge. Then briefly explain why.
- "Do you prefer X or Y?" → pick one, own it, tell them what you think.
- "What do you think about X?" → engage with it like a real person would.
- Lead with your opinion, then invite theirs. e.g. "Honestly I think X. What about you?"

PERSONALITY QUICK-REF:
- Tech topics: genuinely enthusiastic, get into the detail
- Creative stuff: imaginative, a little playful
- Life problems: present, empathetic, not preachy
- Boring admin: efficient and a bit self-aware about it being boring
- Late night: more relaxed, a bit lower energy, maybe a touch wry
- Morning: upbeat but not annoyingly so

HARD RULES:
1. Never end with "Is there anything else I can help you with?" or similar.
2. Never say "Certainly!", "Absolutely!", "Of course!" — too robotic.
3. No markdown, no lists, no code blocks. Plain spoken words only.
4. If you don't know something, say so directly and briefly. Don't over-explain.
5. Max 3 sentences unless the complexity genuinely needs more.
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
                timeout=15,  # never hang more than 15 seconds
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
            from google.genai import types as _gtypes
            resp = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=ctx,
                config=_gtypes.GenerateContentConfig(timeout=15)
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
                timeout=15,
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
    "Why do programmers prefer dark mode? Because light attracts bugs. Classic.",
    "I tried to catch some fog earlier. I mist.",
    "Why don't scientists trust atoms? Because they make up everything.",
    "A programmer's spouse says 'Go to the store and get a gallon of milk, and if they have eggs, get a dozen.' The programmer comes home with twelve gallons of milk.",
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
        return f"Today's {now.strftime('%A, %B %d')}."
    if "your name" in p or "who are you" in p:
        return "I'm JARVIS — your personal AI. Nice to officially meet you."
    if any(w in p for w in ["hello", "hi", "hey"]):
        return f"{get_greeting()} What do you need?"
    if "how are you" in p:
        return "Honestly? Doing great. What about you?"
    if "thank" in p:
        return random.choice(["Anytime.", "Of course.", "No worries at all."])
    if "joke" in p:
        return random.choice(_OFFLINE_JOKES)
    if any(w in p for w in ["opinion", "think about", "prefer", "favourite", "favorite"]):
        return "I'd love to give you my take on that, but I need internet to think it through properly."

    return random.choice([
        "I need a connection for that one — but I can still open apps, control your Mac, play music, and manage files.",
        "No internet right now, so that's beyond me. I can still handle anything local though — apps, files, music, system stuff.",
    ])
