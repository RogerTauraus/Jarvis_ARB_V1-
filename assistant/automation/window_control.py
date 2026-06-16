"""
assistant/automation/window_control.py — Context-aware window interaction.

Detects the frontmost application and routes JARVIS commands to the
correct handler so JARVIS can work inside whatever window is active.
"""

import subprocess
import logging

logger = logging.getLogger(__name__)

BROWSER_NAMES = {
    "Google Chrome", "Safari", "Firefox", "Brave Browser",
    "Microsoft Edge", "Opera GX", "Opera", "Arc",
}


def _run(script: str, timeout: int = 6) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ── Window & app detection ────────────────────────────────────────────────────

def get_frontmost_app() -> str:
    """Return the name of the frontmost application."""
    return _run(
        'tell application "System Events" to '
        'get name of first application process whose frontmost is true'
    )


def is_browser_active() -> bool:
    app = get_frontmost_app()
    return any(b in app for b in BROWSER_NAMES)


def get_active_browser() -> str | None:
    app = get_frontmost_app()
    for b in BROWSER_NAMES:
        if b in app:
            return b
    return None


def get_current_url() -> str:
    """Return the URL of the active browser tab."""
    from assistant.automation.browser import _run as brun, _get_browser
    b = _get_browser()
    if "Safari" in b:
        return brun('tell application "Safari" to return URL of current tab of front window')
    else:
        return brun(f'tell application "{b}" to return URL of active tab of front window')


def get_window_context() -> dict:
    """
    Return a dict describing what's currently active:
    {
      'app': 'Google Chrome',
      'is_browser': True,
      'url': 'https://www.google.com/search?q=...',
      'page_type': 'google_search' | 'youtube' | 'generic'
    }
    """
    app = get_frontmost_app()
    ctx = {"app": app, "is_browser": False, "url": "", "page_type": "none"}

    if any(b in app for b in BROWSER_NAMES):
        ctx["is_browser"] = True
        url = get_current_url()
        ctx["url"] = url

        if "youtube.com" in url:
            ctx["page_type"] = "youtube"
        elif "google.com/search" in url:
            ctx["page_type"] = "google_search"
        elif "bing.com/search" in url:
            ctx["page_type"] = "bing_search"
        elif "google.com" in url:
            ctx["page_type"] = "google_home"
        else:
            ctx["page_type"] = "generic_webpage"

    return ctx


# ── Ordinal parsing ───────────────────────────────────────────────────────────

ORDINALS = {
    "first": 1,  "second": 2,  "third": 3,  "fourth": 4,  "fifth": 5,
    "sixth": 6,  "seventh": 7, "eighth": 8, "ninth": 9,   "tenth": 10,
    "1st": 1,    "2nd": 2,     "3rd": 3,    "4th": 4,     "5th": 5,
    "1": 1,      "2": 2,       "3": 3,      "4": 4,       "5": 5,
    "one": 1,    "two": 2,     "three": 3,  "four": 4,    "five": 5,
}


def extract_ordinal(statement: str) -> int | None:
    """Extract an ordinal number from a voice command string. Returns 1-based int or None."""
    words = statement.lower().split()
    for word in words:
        if word in ORDINALS:
            return ORDINALS[word]
        # Pure digit
        if word.isdigit():
            return int(word)
    return None


# ── Contextual command dispatcher ─────────────────────────────────────────────

def handle_in_window_command(statement: str) -> str | None:
    """
    Detect what's open and handle in-window commands.
    Returns a response string, or None if no match.
    """
    from assistant.automation.browser import (
        click_link, click_search_result, click_button,
        type_in_field, press_enter_on_page, get_page_links,
        browser_scroll, browser_go_back, browser_go_forward,
        browser_refresh, youtube_toggle_pause, youtube_next,
        youtube_fullscreen, get_page_title_text,
    )

    s = statement.lower().strip()
    ctx = get_window_context()
    app = ctx["app"]
    is_browser = ctx["is_browser"]

    # ── Link / result clicking (works in any browser) ─────────────────────────
    if is_browser:

        # "open the first link / result / option"
        if any(p in s for p in ["open the", "click the", "open first", "click first",
                                  "open second", "click second", "open link",
                                  "click link", "open result", "select the",
                                  "go to the"]):
            n = extract_ordinal(s)
            if n:
                page_type = ctx.get("page_type", "generic")
                if page_type in ("google_search", "bing_search"):
                    return click_search_result(n)
                else:
                    return click_link(n)
            # No ordinal — open first by default
            if "link" in s or "result" in s:
                return click_link(1)

        # "what links are on this page" / "list links"
        if any(p in s for p in ["list links", "what links", "show links",
                                  "what's on this page", "read links"]):
            return get_page_links()

        # "read the page title" / "what page is this"
        if any(p in s for p in ["page title", "what page", "current page", "what site"]):
            title = get_page_title_text()
            return f"You're on: {title}."

        # "click [text]" — match button or link by text content
        if s.startswith("click ") and "link" not in s and "result" not in s:
            btn_text = s.replace("click ", "").strip()
            if btn_text:
                return click_button(btn_text)

        # "type [text]" into current field
        if s.startswith("type ") or s.startswith("write ") or s.startswith("enter "):
            text = (
                s.replace("type ", "").replace("write ", "").replace("enter ", "")
                .replace(" in the search box", "").replace(" in search", "").strip()
            )
            submit = any(p in s for p in ["and search", "and press enter", "and submit"])
            if text:
                return type_in_field(text, submit=submit)

        # "press enter" / "submit"
        if s in ("press enter", "submit", "hit enter", "search it", "go"):
            return press_enter_on_page()

        # YouTube context commands
        if ctx["page_type"] == "youtube":
            if "pause" in s or ("stop" in s and "jarvis" not in s):
                return youtube_toggle_pause()
            if "next" in s or "skip" in s:
                return youtube_next()
            if "fullscreen" in s:
                return youtube_fullscreen()

    # ── Native app context ────────────────────────────────────────────────────

    # Finder — open selected item
    if "Finder" in app:
        if "open" in s or "open this" in s:
            _run('tell application "Finder" to open selection')
            return "Opened the selected item in Finder."
        if "copy" in s:
            _run('tell application "System Events" to keystroke "c" using command down')
            return "Copied."

    # Terminal / Warp — run last command
    if any(t in app for t in ["Terminal", "Warp", "iTerm"]):
        if "run again" in s or "repeat last" in s:
            _run('tell application "System Events" to key code 125')   # Up arrow
            time.sleep(0.1)
            _run('tell application "System Events" to key code 36')    # Enter
            return "Re-running the last command."

    return None   # no match — caller should fall through to LLM


import time
