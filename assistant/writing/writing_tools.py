"""
writing_tools.py — Clipboard-based writing assistant for JARVIS.

How it works:
  1. User copies text to clipboard
  2. User says "proofread this" / "make this formal" / "summarize this"
  3. JARVIS processes it through LLM
  4. Result is placed back in clipboard
  5. User pastes anywhere

Can also draft text from scratch: "write me an email about X"
"""

import subprocess
import logging
import os

logger = logging.getLogger(__name__)


# ── Clipboard helpers ─────────────────────────────────────────────────────────

def get_clipboard() -> str:
    """Get current clipboard text content."""
    try:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return ""


def set_clipboard(text: str) -> None:
    """Write text to clipboard."""
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
    except Exception as e:
        logger.error(f"Clipboard write error: {e}")


# ── LLM-powered writing operations ───────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """Call LLM with writing task. Uses Groq → Gemini cascade."""
    from dotenv import load_dotenv
    import os as _os
    _env = _os.path.join(_os.path.dirname(__file__), '..', '..', 'API', 'agent.env')
    load_dotenv(_env)

    # Try Groq first
    try:
        from groq import Groq
        key = _os.getenv("GROQ_API_KEY", "")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": (
                        "You are a professional writing assistant. "
                        "Return ONLY the processed text — no explanations, "
                        "no preamble, no 'Here is the rewritten version'. "
                        "Just the text itself, ready to paste."
                    )},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.4,
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq writing error: {e}")

    # Fallback: Gemini
    try:
        from google import genai
        key = _os.getenv("GEMINI_API_KEY", "")
        if key:
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return resp.text.strip()
    except Exception as e:
        logger.warning(f"Gemini writing error: {e}")

    return ""


# ── Writing operations ────────────────────────────────────────────────────────

def proofread(text: str = "") -> str:
    """
    Fix grammar, spelling, punctuation. Keep the original voice and meaning.
    If text is empty, reads from clipboard.
    """
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard to proofread. Copy some text first."

    prompt = (
        f"Proofread and correct the following text. "
        f"Fix grammar, spelling, punctuation, and awkward phrasing. "
        f"Keep the original tone and meaning — do not rephrase or restructure. "
        f"Return only the corrected text:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return "Done — corrected text is in your clipboard. Just paste it."
    return "Something went wrong. Try again."


def rewrite(text: str = "", style: str = "professional") -> str:
    """
    Rewrite text in a given style: professional, casual, formal, simple, persuasive.
    If text is empty, reads from clipboard.
    """
    if not text:
        text = get_clipboard()
    if not text:
        return f"Nothing in clipboard. Copy text first, then say rewrite this as {style}."

    style_instructions = {
        "professional": "Clear, confident, business-appropriate. No slang.",
        "casual":       "Friendly, relaxed, conversational. Contractions welcome.",
        "formal":       "Highly formal and polished. Suitable for official correspondence.",
        "simple":       "Very simple and clear. Short sentences. Plain words.",
        "persuasive":   "Compelling and motivating. Strong verbs. Confident tone.",
        "friendly":     "Warm, approachable, and upbeat.",
    }
    instruction = style_instructions.get(style.lower(), f"Rewrite in a {style} tone.")

    prompt = (
        f"Rewrite the following text in a {style} tone. "
        f"Style guidance: {instruction} "
        f"Keep the same core meaning and key points. "
        f"Return only the rewritten text:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return f"Done — rewritten as {style}. It's in your clipboard, just paste it."
    return "Something went wrong. Try again."


def summarize_text(text: str = "") -> str:
    """Summarize text to 2-3 sentences. Reads from clipboard if no text given."""
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard. Copy some text first."

    prompt = (
        f"Summarize the following text in 2-3 clear, concise sentences. "
        f"Capture the most important points. "
        f"Return only the summary:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        # Also return it verbally so JARVIS can speak it
        return f"Here's the summary: {result}"
    return "Something went wrong. Try again."


def make_shorter(text: str = "") -> str:
    """Trim text to its essentials. Reads from clipboard if empty."""
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard. Copy text first."

    prompt = (
        f"Make the following text shorter and more concise. "
        f"Cut filler words, redundant phrases, and anything non-essential. "
        f"Keep all important information. Return only the shortened text:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return "Done — trimmed it down. It's in your clipboard."
    return "Something went wrong."


def make_longer(text: str = "") -> str:
    """Expand text with more detail. Reads from clipboard if empty."""
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard. Copy text first."

    prompt = (
        f"Expand and elaborate on the following text. "
        f"Add relevant detail, context, and supporting points. "
        f"Keep the same tone. Return only the expanded text:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return "Done — expanded it. It's in your clipboard."
    return "Something went wrong."


def fix_grammar(text: str = "") -> str:
    """Quick grammar fix only. Reads from clipboard if empty."""
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard. Copy text first."

    prompt = (
        f"Fix only the grammar and spelling in the following text. "
        f"Do not change the wording, tone, or structure. "
        f"Return only the corrected text:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return "Fixed — corrected text is in your clipboard."
    return "Something went wrong."


def draft_writing(doc_type: str, topic: str, extra: str = "") -> str:
    """
    Draft a document from scratch.
    doc_type: email, message, essay, cover letter, bio, caption, report, speech
    topic: what it should be about
    extra: extra instructions (tone, recipient, length, etc.)
    """
    type_instructions = {
        "email":        "Write a professional email. Include subject line as first line.",
        "message":      "Write a short, natural-sounding text message or chat message.",
        "essay":        "Write a well-structured essay with intro, body, and conclusion.",
        "cover letter": "Write a compelling job application cover letter.",
        "bio":          "Write a short professional bio in third person.",
        "caption":      "Write an engaging social media caption.",
        "report":       "Write a clear, structured report.",
        "speech":       "Write a spoken speech that sounds natural when read aloud.",
        "apology":      "Write a sincere, heartfelt apology.",
        "proposal":     "Write a professional project or business proposal.",
    }
    instruction = type_instructions.get(doc_type.lower(), f"Write a {doc_type}.")

    prompt = (
        f"{instruction}\n"
        f"Topic/Subject: {topic}\n"
        f"{'Additional instructions: ' + extra if extra else ''}\n"
        f"Return only the draft — no explanations or meta commentary."
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return f"Done — your {doc_type} is ready in the clipboard. Check it and paste whenever you're ready."
    return "I couldn't draft that. Try again."


# ── Translate ─────────────────────────────────────────────────────────────────

def translate_text(text: str = "", target_lang: str = "English") -> str:
    """Translate clipboard text to target language."""
    if not text:
        text = get_clipboard()
    if not text:
        return "Nothing in clipboard to translate."

    prompt = (
        f"Translate the following text to {target_lang}. "
        f"Return only the translation:\n\n{text}"
    )
    result = _call_llm(prompt)
    if result:
        set_clipboard(result)
        return f"Translated to {target_lang}. It's in your clipboard."
    return "Translation failed. Try again."


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'API', 'agent.env'))

    test_text = "i went to the store and buyed some milk and eggs it was pretty good"
    print("Original:", test_text)
    set_clipboard(test_text)

    print("\n--- Proofread ---")
    print(proofread())
    print("\n--- Rewrite (professional) ---")
    set_clipboard(test_text)
    print(rewrite(style="professional"))
    print("\n--- Summarize ---")
    long_text = "The quick brown fox jumps over the lazy dog. This is a well-known pangram used in typography. It contains every letter of the English alphabet at least once. Typesetters have used it for centuries to display fonts."
    set_clipboard(long_text)
    print(summarize_text())
    print("\n--- Draft email ---")
    print(draft_writing("email", "requesting a meeting with the team about project delays"))
