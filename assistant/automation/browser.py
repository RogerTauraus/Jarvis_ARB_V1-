"""
assistant/automation/browser.py — In-browser automation for JARVIS.

Controls Chrome and Safari via AppleScript + JavaScript injection.
No external dependencies (no Selenium/Playwright required).
"""

import subprocess
import urllib.parse
import time
import logging

logger = logging.getLogger(__name__)

# ── AppleScript helpers ───────────────────────────────────────────────────────

def _run(script: str, timeout: int = 10) -> str:
    """Run an AppleScript and return stdout."""
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        logger.warning(f"AppleScript error: {e}")
        return ""


def _active_browser() -> str:
    """Return the name of the frontmost browser, or 'Google Chrome' as default."""
    name = _run(
        'tell application "System Events" to return name of '
        'first application process whose frontmost is true'
    )
    for b in ("Google Chrome", "Safari", "Firefox", "Brave Browser",
              "Microsoft Edge", "Opera GX"):
        if b.lower() in name.lower():
            return b
    return "Google Chrome"   # safe default


def _js_in_browser(js: str, browser: str = None) -> str:
    """Inject and execute JavaScript in the active browser tab."""
    b = browser or _active_browser()
    # Escape double quotes inside the JS for AppleScript embedding
    safe_js = js.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

    if "Chrome" in b or "Brave" in b or "Edge" in b:
        script = (
            f'tell application "{b}" to '
            f'execute front window\'s active tab javascript "{safe_js}"'
        )
    elif "Safari" in b:
        script = (
            f'tell application "Safari" to '
            f'do JavaScript "{safe_js}" in current tab of front window'
        )
    else:
        return ""   # Firefox doesn't support AppleScript JS injection

    return _run(script)


def _navigate(url: str, browser: str = None) -> None:
    """Navigate the active browser to a URL."""
    b = browser or _active_browser()
    if "Chrome" in b or "Brave" in b or "Edge" in b:
        script = f'''
        tell application "{b}"
            activate
            if (count of windows) = 0 then make new window
            set URL of active tab of front window to "{url}"
        end tell
        '''
    elif "Safari" in b:
        script = f'''
        tell application "Safari"
            activate
            open location "{url}"
        end tell
        '''
    else:
        # Generic macOS open
        subprocess.Popen(["open", url])
        return
    _run(script)


# ── YouTube ───────────────────────────────────────────────────────────────────

def youtube_play(query: str) -> str:
    """Search YouTube and auto-click the first video result."""
    encoded = urllib.parse.quote(query)
    _navigate(f"https://www.youtube.com/results?search_query={encoded}")
    time.sleep(3.5)   # let the results page render

    clicked = _js_in_browser(
        "var v = document.querySelector('a#video-title'); "
        "if(v){v.click();'clicked';}else{'none';}",
    )
    if clicked == "clicked":
        time.sleep(1.5)
        return f"Playing '{query}' on YouTube."
    else:
        return (f"I've searched YouTube for '{query}'. "
                "The results are open — tap the video you want.")


def youtube_toggle_pause() -> str:
    """Toggle play/pause on the active YouTube tab."""
    _js_in_browser(
        "var v=document.querySelector('video');"
        "if(v){v.paused?v.play():v.pause();}"
    )
    return "Toggled YouTube playback."


def youtube_next() -> str:
    """Click the Next button on YouTube."""
    _js_in_browser(
        "var b=document.querySelector('.ytp-next-button');"
        "if(b)b.click();"
    )
    return "Skipping to the next video."


def youtube_fullscreen() -> str:
    """Toggle YouTube fullscreen."""
    _js_in_browser(
        "var b=document.querySelector('.ytp-fullscreen-button');"
        "if(b)b.click();"
    )
    return "Toggling fullscreen."


def youtube_mute() -> str:
    """Mute/unmute YouTube video."""
    _js_in_browser(
        "var b=document.querySelector('.ytp-mute-button');"
        "if(b)b.click();"
    )
    return "Toggled YouTube mute."


def youtube_volume(level: int) -> str:
    """Set YouTube video volume (0–100)."""
    _js_in_browser(
        f"var v=document.querySelector('video');if(v)v.volume={level/100};"
    )
    return f"YouTube volume set to {level} percent."


# ── General browser ───────────────────────────────────────────────────────────

def browser_search(query: str, engine: str = "google") -> str:
    """Open a browser search."""
    urls = {
        "google":  f"https://www.google.com/search?q={urllib.parse.quote(query)}",
        "youtube": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
        "bing":    f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
        "maps":    f"https://www.google.com/maps/search/{urllib.parse.quote(query)}",
    }
    url = urls.get(engine.lower(), urls["google"])
    _navigate(url)
    return f"Searching {engine.capitalize()} for '{query}'."


def browser_go_to(url: str) -> str:
    """Navigate the browser to any URL."""
    if not url.startswith("http"):
        url = "https://" + url
    _navigate(url)
    return f"Navigating to {url}."


def browser_go_back() -> str:
    _js_in_browser("history.back();")
    return "Going back."


def browser_go_forward() -> str:
    _js_in_browser("history.forward();")
    return "Going forward."


def browser_refresh() -> str:
    b = _active_browser()
    if "Chrome" in b or "Brave" in b or "Edge" in b:
        _run(f'tell application "{b}" to reload active tab of front window')
    else:
        _js_in_browser("location.reload();")
    return "Page refreshed."


def browser_scroll(direction: str = "down", amount: int = 600) -> str:
    dy = amount if direction == "down" else -amount
    _js_in_browser(f"window.scrollBy(0,{dy});")
    return f"Scrolling {direction}."


def browser_scroll_top() -> str:
    _js_in_browser("window.scrollTo(0,0);")
    return "Scrolled to the top."


def browser_scroll_bottom() -> str:
    _js_in_browser("window.scrollTo(0,document.body.scrollHeight);")
    return "Scrolled to the bottom."


def browser_new_tab(url: str = "") -> str:
    b = _active_browser()
    if "Chrome" in b or "Brave" in b or "Edge" in b:
        script = (
            f'tell application "{b}" to '
            f'make new tab at end of tabs of front window'
        )
        _run(script)
        if url:
            time.sleep(0.3)
            _navigate(url, b)
    elif "Safari" in b:
        _run('tell application "Safari" to make new tab at end of tabs of front window')
        if url:
            time.sleep(0.3)
            _navigate(url, b)
    return f"Opened new tab{(' at ' + url) if url else ''}."


def browser_close_tab() -> str:
    b = _active_browser()
    if "Chrome" in b or "Brave" in b or "Edge" in b:
        _run(f'tell application "{b}" to close active tab of front window')
    elif "Safari" in b:
        _run('tell application "Safari" to close current tab of front window')
    return "Tab closed."


def browser_get_page_title() -> str:
    b = _active_browser()
    if "Chrome" in b or "Brave" in b or "Edge" in b:
        return _run(
            f'tell application "{b}" to return title of active tab of front window'
        )
    elif "Safari" in b:
        return _run(
            'tell application "Safari" to return name of current tab of front window'
        )
    return ""
