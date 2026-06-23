"""
screen_reader.py — Onscreen awareness for JARVIS.

Capabilities:
  • Read text from any app using macOS Accessibility API (no internet, instant)
  • Describe the screen visually using Groq Vision (AI-powered)
  • Answer questions about the screen content
  • Find and click UI elements by name in any app
  • Click at coordinates (for Vision-identified targets)
  • YouTube title matching from on-screen results

Vision model cascade: Groq llama-4-scout (vision) → Gemini 2.0 Flash → text-only fallback
"""

import subprocess
import tempfile
import os
import base64
import logging
import json
import re

logger = logging.getLogger(__name__)

# Screen logical dimensions (set at import time)
_SCREEN_W = 1512
_SCREEN_H = 982


def _get_screen_size():
    """Get current screen logical size via AppleScript."""
    global _SCREEN_W, _SCREEN_H
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "Finder" to get bounds of window of desktop'],
            capture_output=True, text=True, timeout=3
        )
        parts = r.stdout.strip().split(",")
        if len(parts) == 4:
            _SCREEN_W = int(parts[2].strip())
            _SCREEN_H = int(parts[3].strip())
    except Exception:
        pass


_get_screen_size()


# ── Screenshot ────────────────────────────────────────────────────────────────

def capture_screen() -> str:
    """Take a screenshot and return the temp file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    path = tmp.name
    tmp.close()
    result = subprocess.run(
        ["screencapture", "-x", path],
        capture_output=True, timeout=5
    )
    if result.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    if os.path.exists(path):
        os.unlink(path)
    return ""


# ── Accessibility text reader (no internet) ───────────────────────────────────

def get_screen_text_accessibility() -> str:
    """
    Read visible text from the frontmost app using macOS Accessibility API.
    Instant, no internet, works for most native apps.
    """
    script = '''
    tell application "System Events"
        set frontApp to name of first process whose frontmost is true
        set output to ""
        tell process frontApp
            try
                set allElements to entire contents of window 1
                repeat with el in allElements
                    try
                        set val to value of el
                        if val is not missing value and val is not "" then
                            set output to output & val & " "
                        end if
                    end try
                    try
                        set ttl to title of el
                        if ttl is not missing value and ttl is not "" then
                            set output to output & ttl & " "
                        end if
                    end try
                end repeat
            end try
        end tell
        return output
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=12
        )
        return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Accessibility read error: {e}")
        return ""


def get_frontmost_app_name() -> str:
    """Return the name of the frontmost application."""
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to return name of first process whose frontmost is true'],
            capture_output=True, text=True, timeout=3
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ── Vision AI (Groq) ──────────────────────────────────────────────────────────

def _vision_describe(image_path: str, question: str = "") -> str:
    """Send screenshot to vision LLM and return description."""
    from dotenv import load_dotenv
    import os as _os
    _env = _os.path.join(_os.path.dirname(__file__), '..', '..', 'API', 'agent.env')
    load_dotenv(_env)

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except Exception:
        return ""

    q = question or "What is on this screen? Describe the main app, any visible text, window titles, and what the user is looking at. Be specific and concise."

    # Groq Vision (primary)
    try:
        from groq import Groq
        key = _os.getenv("GROQ_API_KEY", "")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": q}
                ]}],
                max_tokens=400,
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.debug(f"Groq Vision error: {e}")

    # Gemini fallback
    try:
        from google import genai
        import PIL.Image
        key = _os.getenv("GEMINI_API_KEY", "")
        if key:
            client = genai.Client(api_key=key)
            img = PIL.Image.open(image_path)
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[img, q]
            )
            return resp.text.strip()
    except Exception as e:
        logger.debug(f"Gemini Vision error: {e}")

    return ""


# ── Main screen awareness functions ──────────────────────────────────────────

def describe_screen(question: str = "") -> str:
    """
    Describe what's currently on screen.
    Uses Accessibility text first (fast, no API), then Vision AI for visual description.
    """
    app_name = get_frontmost_app_name()
    acc_text = get_screen_text_accessibility()

    # If we got good accessibility text, use LLM to answer question about it
    if acc_text and len(acc_text) > 50:
        if question:
            from assistant.ai.llm_engine import ask_llm
            from assistant.ai.memory import ConversationMemory
            _mem = ConversationMemory()
            prompt = (
                f"The user is looking at {app_name}. "
                f"Here is the text visible on screen via Accessibility:\n\n"
                f"{acc_text[:2000]}\n\n"
                f"Answer this question about what's on screen: {question}\n"
                f"Be brief and spoken-friendly."
            )
            return ask_llm(prompt, _mem)
        else:
            # Quick summary without Vision API
            return f"You're in {app_name}. I can see: {acc_text[:300].strip()}"

    # Fall back to Vision AI screenshot
    path = capture_screen()
    if not path:
        return f"You're in {app_name} but I couldn't capture the screen right now."
    try:
        result = _vision_describe(path, question)
        return result or f"I can see you're in {app_name}, but I couldn't read more detail right now."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def read_screen_text() -> str:
    """Extract and speak the readable text from the current screen."""
    app_name = get_frontmost_app_name()
    text = get_screen_text_accessibility()

    if text and len(text) > 20:
        # Clean up repeated whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return f"In {app_name}, I can read: {text[:400]}"

    # Fallback: Vision OCR
    path = capture_screen()
    if not path:
        return "Couldn't capture the screen."
    try:
        result = _vision_describe(
            path,
            "Read all the text visible on this screen. List it clearly."
        )
        return result or "I couldn't read the text on screen right now."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def answer_about_screen(question: str) -> str:
    """Answer a specific question about what's on screen."""
    return describe_screen(question)


# ── UI element clicking ───────────────────────────────────────────────────────

def click_ui_element(element_name: str, app_name: str = "") -> str:
    """
    Click a UI element by name in the frontmost app (or specified app).
    Uses macOS Accessibility API — works in any standard Mac app.
    """
    if not app_name:
        app_name = get_frontmost_app_name()

    if not app_name:
        return "I couldn't determine which app is open."

    # Try clicking as a button first
    script = f'''
    tell application "System Events"
        tell process "{app_name}"
            try
                click button "{element_name}" of window 1
                return "clicked"
            end try
            try
                click button "{element_name}" of front window
                return "clicked"
            end try
            -- Search all buttons
            set allBtns to buttons of windows
            repeat with w in windows
                repeat with b in buttons of w
                    if title of b contains "{element_name}" or description of b contains "{element_name}" then
                        click b
                        return "clicked"
                    end if
                end repeat
            end repeat
            return "not_found"
        end tell
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=8
    )
    output = result.stdout.strip()

    if output == "clicked":
        return f"Clicked {element_name}."

    # Try menu items
    menu_script = f'''
    tell application "System Events"
        tell process "{app_name}"
            try
                click menu item "{element_name}" of menu bar 1
                return "clicked"
            end try
            try
                -- Search sub-menus
                set mbar to menu bar 1
                repeat with mi in menu bar items of mbar
                    try
                        click menu item "{element_name}" of menu 1 of mi
                        return "clicked"
                    end try
                end repeat
            end try
            return "not_found"
        end tell
    end tell
    '''
    result2 = subprocess.run(
        ["osascript", "-e", menu_script],
        capture_output=True, text=True, timeout=8
    )
    if result2.stdout.strip() == "clicked":
        return f"Clicked {element_name}."

    # Vision-based fallback: find by screenshot + coordinates
    return _click_by_vision(element_name, app_name)


def _click_by_vision(element_name: str, app_name: str) -> str:
    """
    Last resort: use Vision AI to locate an element on screen and click it.
    Returns spoken response.
    """
    path = capture_screen()
    if not path:
        return f"Couldn't find {element_name} on screen."
    try:
        question = (
            f"I need to click the element called '{element_name}'. "
            f"Look at this screenshot and tell me the approximate X,Y coordinates "
            f"as percentages of screen width and height (e.g. '25%, 60%'). "
            f"Reply with ONLY the coordinates like: x=25%, y=60%"
        )
        coord_text = _vision_describe(path, question)
        if not coord_text:
            return f"I couldn't locate {element_name} on screen."

        # Parse percentages
        mx = re.search(r'x\s*=\s*(\d+(?:\.\d+)?)\s*%', coord_text, re.IGNORECASE)
        my = re.search(r'y\s*=\s*(\d+(?:\.\d+)?)\s*%', coord_text, re.IGNORECASE)

        if mx and my:
            x = int(float(mx.group(1)) * _SCREEN_W / 100)
            y = int(float(my.group(1)) * _SCREEN_H / 100)
            click_script = f'''
            tell application "System Events"
                click at {{{x}, {y}}}
            end tell
            '''
            subprocess.run(["osascript", "-e", click_script], timeout=3)
            return f"Clicked where {element_name} appears to be."

        return f"I found a description of {element_name} but couldn't get precise coordinates to click it."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def click_at_coordinates(x: int, y: int) -> str:
    """Click at specific screen coordinates."""
    script = f'''
    tell application "System Events"
        click at {{{x}, {y}}}
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
    return "Done." if result.returncode == 0 else "Couldn't click there."


# ── YouTube title matching ────────────────────────────────────────────────────

def find_youtube_video_on_screen(title_query: str) -> str:
    """
    When YouTube is open in the browser, find a video by title and open it.
    Reads the actual page DOM (via browser module) — no screenshot needed.
    """
    from assistant.automation.browser import get_page_links

    links_raw = get_page_links()
    if not links_raw or "couldn't" in links_raw.lower():
        return _find_youtube_via_vision(title_query)

    # Parse links: format is "1. Title — URL"
    lines = [l.strip() for l in links_raw.split("\n") if l.strip()]
    query_words = set(title_query.lower().split())

    best_match = None
    best_score = 0

    for line in lines:
        line_lower = line.lower()
        score = sum(1 for w in query_words if w in line_lower)
        if score > best_score:
            best_score = score
            best_match = line

    if best_match and best_score > 0:
        # Extract URL from the line
        url_match = re.search(r'(https?://\S+)', best_match)
        if url_match:
            url = url_match.group(1)
            subprocess.run(["osascript", "-e",
                f'tell application "Google Chrome" to set URL of active tab of front window to "{url}"'],
                timeout=3)
            title_text = best_match.split("—")[0].strip() if "—" in best_match else best_match[:60]
            return f"Opening: {title_text}"

    # Fall back to YouTube search by title
    from assistant.automation.browser import youtube_play
    return youtube_play(title_query)


def _find_youtube_via_vision(title_query: str) -> str:
    """Use Vision AI to find a YouTube video title on screen and click it."""
    path = capture_screen()
    if not path:
        return "Couldn't capture the screen."
    try:
        question = (
            f"This is a YouTube page. Find the video titled '{title_query}' or the closest match. "
            f"Give the X,Y coordinates of that video thumbnail/title as screen percentages. "
            f"Reply: x=XX%, y=YY%"
        )
        coord_text = _vision_describe(path, question)
        if coord_text:
            mx = re.search(r'x\s*=\s*(\d+(?:\.\d+)?)\s*%', coord_text, re.IGNORECASE)
            my = re.search(r'y\s*=\s*(\d+(?:\.\d+)?)\s*%', coord_text, re.IGNORECASE)
            if mx and my:
                x = int(float(mx.group(1)) * _SCREEN_W / 100)
                y = int(float(my.group(1)) * _SCREEN_H / 100)
                click_at_coordinates(x, y)
                return f"Clicked on what looks like '{title_query}'."
    finally:
        if os.path.exists(path):
            os.unlink(path)
    from assistant.automation.browser import youtube_play
    return youtube_play(title_query)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Screen Text (Accessibility) ===")
    print(get_screen_text_accessibility()[:500])
    print()
    print("=== Screen Description (Vision) ===")
    print(describe_screen())
    print()
    print("=== Frontmost App ===")
    print(get_frontmost_app_name())
