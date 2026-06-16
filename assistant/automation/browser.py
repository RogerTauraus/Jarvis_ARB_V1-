"""
assistant/automation/browser.py — Real-time browser automation for JARVIS.

Capabilities:
  • Open any URL (launches browser if not running)
  • YouTube: search & auto-play, pause, next, fullscreen, mute
  • Click links/search results by ordinal: "open first link"
  • Click buttons by text: "click Sign In"
  • Type into fields: "type hello in search"
  • Tab management, scroll, back/forward/refresh
  • Works with Chrome, Safari, Opera GX, Brave, Edge
"""

import subprocess
import urllib.parse
import time
import logging

logger = logging.getLogger(__name__)

# ── Browser priority (first installed wins) ───────────────────────────────────
_PREFERRED_BROWSERS = [
    "Google Chrome",
    "Brave Browser",
    "Microsoft Edge",
    "Opera GX",
    "Safari",
]

# Ordinal word → integer index (1-based)
ORDINALS = {
    "first": 1,  "second": 2,  "third": 3,  "fourth": 4,  "fifth": 5,
    "sixth": 6,  "seventh": 7, "eighth": 8, "ninth": 9,   "tenth": 10,
    "1st": 1,    "2nd": 2,     "3rd": 3,    "4th": 4,     "5th": 5,
    "1": 1,      "2": 2,       "3": 3,      "4": 4,       "5": 5,
    "one": 1,    "two": 2,     "three": 3,  "four": 4,    "five": 5,
}


# ── AppleScript helpers ───────────────────────────────────────────────────────

def _run(script: str, timeout: int = 10) -> str:
    """Execute AppleScript and return stdout, suppressing stderr."""
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        logger.debug(f"AS error: {e}")
        return ""


def _running_apps() -> list[str]:
    """Return list of running application names."""
    out = _run(
        'tell application "System Events" to get name of every process'
    )
    return [n.strip() for n in out.split(",")]


def _get_browser() -> str:
    """Return the name of the first installed browser that is also running, or launch one."""
    running = _running_apps()
    # Prefer one that's already open
    for b in _PREFERRED_BROWSERS:
        if b in running:
            return b
    # Nothing open — return first installed
    for b in _PREFERRED_BROWSERS:
        probe = _run(f'tell application "System Events" to exists application file of '
                     f'(first application process whose name is "{b}")')
        if probe == "true":
            return b
    # Absolute fallback
    return "Google Chrome"


def _launch_browser(browser: str) -> None:
    """Launch a browser app if it isn't already running."""
    running = _running_apps()
    if browser not in running:
        subprocess.Popen(["open", "-a", browser])
        time.sleep(2.0)   # give it time to open


def _js(js_code: str, browser: str = None) -> str:
    """Inject JavaScript into the active tab of the given browser."""
    b = browser or _get_browser()
    safe = js_code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    if "Safari" in b:
        script = (f'tell application "Safari" to '
                  f'do JavaScript "{safe}" in current tab of front window')
    else:
        script = (f'tell application "{b}" to '
                  f'execute front window\'s active tab javascript "{safe}"')
    return _run(script)


# ── Core navigation (FIXED — launches browser, handles closed state) ──────────

def _navigate(url: str, browser: str = None) -> None:
    b = browser or _get_browser()
    _launch_browser(b)
    time.sleep(0.4)

    if "Safari" in b:
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then make new document
            set URL of current tab of front window to "{url}"
        end tell
        '''
    else:
        script = f'''
        tell application "{b}"
            activate
            if (count of windows) = 0 then make new window
            set URL of active tab of front window to "{url}"
        end tell
        '''
    result = _run(script)

    # Fallback — if AppleScript fails, use Python's webbrowser
    if not result and "error" in result.lower():
        import webbrowser
        webbrowser.open(url)


def browser_go_to(url: str) -> str:
    """Navigate the browser to any URL."""
    if not url.startswith("http"):
        url = "https://" + url
    _navigate(url)
    return f"Opening {url}."


# ── Link / result clicking ────────────────────────────────────────────────────

def click_link(index: int = 1) -> str:
    """Click the Nth visible hyperlink on the current page (1-indexed)."""
    js = f"""
    (function(){{
        var all = Array.from(document.querySelectorAll('a[href]'));
        var visible = all.filter(function(el){{
            var r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0 &&
                   el.href && !el.href.startsWith('javascript') &&
                   el.textContent.trim().length > 0;
        }});
        if(visible.length >= {index}){{
            var el = visible[{index-1}];
            el.click();
            return 'Clicked: ' + el.textContent.trim().substring(0,60);
        }} else {{
            return 'Only ' + visible.length + ' links found';
        }}
    }})()
    """
    result = _js(js)
    if result.startswith("Clicked:"):
        label = result.replace("Clicked: ", "").strip()
        return f"Opening: {label}."
    return f"I could only find {result.split()[-2] if result else 'no'} links on this page."


def click_search_result(index: int = 1) -> str:
    """Click the Nth Google/Bing/DuckDuckGo search result (1-indexed)."""
    js = f"""
    (function(){{
        // Try multiple selectors to cover Google, Bing, DDG, etc.
        var selectors = [
            'div.g h3', 'div.yuRUbf a', '.g a[jsname]',
            'li.b_algo h2 a', '#links .result__a',
            'h3.r a', '.tF2Cxc a', 'a.l'
        ];
        var results = [];
        for(var sel of selectors){{
            var els = Array.from(document.querySelectorAll(sel))
                .filter(function(el){{
                    var r = el.getBoundingClientRect();
                    return r.width > 0 && el.textContent.trim().length > 0;
                }});
            if(els.length > 0){{ results = els; break; }}
        }}
        // Fallback: all visible links with text
        if(results.length === 0){{
            results = Array.from(document.querySelectorAll('a[href^="http"]'))
                .filter(function(el){{
                    var r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && el.textContent.trim().length > 3;
                }});
        }}
        if(results.length >= {index}){{
            var el = results[{index-1}];
            el.click();
            return 'Clicked: ' + el.textContent.trim().substring(0,80);
        }} else {{
            return 'Found:' + results.length;
        }}
    }})()
    """
    result = _js(js)
    if result.startswith("Clicked:"):
        label = result.replace("Clicked: ", "").strip()
        return f"Opening: {label}."
    count = result.split(":")[-1].strip() if "Found:" in result else "?"
    return f"I found {count} results. Try saying a smaller number."


def click_button(text: str) -> str:
    """Click a button or link that contains the given text."""
    safe = text.replace('"', '\\"').replace("'", "\\'")
    js = f"""
    (function(){{
        var lower = '{safe}'.toLowerCase();
        var els = Array.from(document.querySelectorAll(
            'button, input[type=submit], input[type=button], a, [role=button]'
        ));
        var match = els.find(function(el){{
            var t = (el.textContent || el.value || el.placeholder || '').toLowerCase();
            return t.includes(lower) && el.offsetParent !== null;
        }});
        if(match){{ match.click(); return 'Clicked: ' + (match.textContent || match.value).trim().substring(0,40); }}
        return 'Not found';
    }})()
    """
    result = _js(js)
    if result.startswith("Clicked:"):
        return f"Clicked '{text}'."
    return f"I couldn't find a button or link that says '{text}'."


def type_in_field(text: str, submit: bool = False) -> str:
    """Type text into the focused or first text input on the page."""
    safe = text.replace('"', '\\"').replace("'", "\\'")
    js = f"""
    (function(){{
        var el = document.querySelector(
            'input[type=text]:not([disabled]), input[type=search]:not([disabled]), textarea:not([disabled]), [contenteditable=true]'
        );
        if(el){{
            el.focus();
            el.value = '{safe}';
            el.dispatchEvent(new Event('input', {{bubbles:true}}));
            el.dispatchEvent(new Event('change', {{bubbles:true}}));
            {'el.form && el.form.submit();' if submit else ''}
            return 'Typed';
        }}
        return 'No input found';
    }})()
    """
    result = _js(js)
    if result == "Typed":
        return f"Typed '{text}'." + (" Submitted." if submit else "")
    return "I couldn't find a text field on this page."


def press_enter_on_page() -> str:
    """Press Enter / submit the focused form."""
    _js("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,bubbles:true}));")
    return "Pressed Enter."


def get_page_links() -> str:
    """List the first 5 visible links on the current page."""
    js = """
    (function(){
        var links = Array.from(document.querySelectorAll('a[href]'))
            .filter(function(el){
                var r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && el.textContent.trim().length > 1;
            }).slice(0,5);
        return links.map(function(el,i){return (i+1)+'. '+el.textContent.trim().substring(0,50);}).join('|');
    })()
    """
    result = _js(js)
    if not result:
        return "I couldn't read any links from this page."
    items = result.split("|")
    return "Here are the first links on the page: " + ", ".join(items)


def get_page_title_text() -> str:
    """Return the current page title."""
    return _js("document.title") or "Unknown page"


# ── YouTube ───────────────────────────────────────────────────────────────────

def youtube_play(query: str) -> str:
    encoded = urllib.parse.quote(query)
    _navigate(f"https://www.youtube.com/results?search_query={encoded}")
    time.sleep(4.0)
    clicked = _js(
        "(function(){var v=document.querySelector('a#video-title');"
        "if(v){v.click();return 'clicked';}return 'none';})() "
    )
    if clicked == "clicked":
        return f"Playing '{query}' on YouTube."
    return f"YouTube search results for '{query}' are open."


def youtube_toggle_pause() -> str:
    _js("(function(){var v=document.querySelector('video');if(v){v.paused?v.play():v.pause();}})();")
    return "Toggled playback."


def youtube_next() -> str:
    _js("(function(){var b=document.querySelector('.ytp-next-button');if(b)b.click();})();")
    return "Skipping to next."


def youtube_fullscreen() -> str:
    _js("(function(){var b=document.querySelector('.ytp-fullscreen-button');if(b)b.click();})();")
    return "Toggling fullscreen."


def youtube_mute() -> str:
    _js("(function(){var b=document.querySelector('.ytp-mute-button');if(b)b.click();})();")
    return "Toggled mute."


def youtube_volume(level: int) -> str:
    _js(f"(function(){{var v=document.querySelector('video');if(v)v.volume={level/100};}})();")
    return f"Volume set to {level}%."


# ── Web search ────────────────────────────────────────────────────────────────

def browser_search(query: str, engine: str = "google") -> str:
    urls = {
        "google":  f"https://www.google.com/search?q={urllib.parse.quote(query)}",
        "youtube": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
        "bing":    f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
    }
    _navigate(urls.get(engine.lower(), urls["google"]))
    return f"Searching {engine.capitalize()} for '{query}'."


# ── General browser controls ──────────────────────────────────────────────────

def browser_go_back() -> str:
    _js("history.back();")
    return "Going back."


def browser_go_forward() -> str:
    _js("history.forward();")
    return "Going forward."


def browser_refresh() -> str:
    b = _get_browser()
    if "Safari" in b:
        _js("location.reload();", b)
    else:
        _run(f'tell application "{b}" to reload active tab of front window')
    return "Page refreshed."


def browser_scroll(direction: str = "down", amount: int = 600) -> str:
    dy = amount if direction == "down" else -amount
    _js(f"window.scrollBy(0,{dy});")
    return f"Scrolling {direction}."


def browser_scroll_top() -> str:
    _js("window.scrollTo(0,0);")
    return "Scrolled to top."


def browser_scroll_bottom() -> str:
    _js("window.scrollTo(0,document.body.scrollHeight);")
    return "Scrolled to bottom."


def browser_new_tab(url: str = "") -> str:
    b = _get_browser()
    _launch_browser(b)
    if "Safari" in b:
        _run('tell application "Safari" to make new tab at end of tabs of front window')
    else:
        _run(f'tell application "{b}" to make new tab at end of tabs of front window')
    if url:
        time.sleep(0.5)
        _navigate(url, b)
    return "New tab opened."


def browser_close_tab() -> str:
    b = _get_browser()
    if "Safari" in b:
        _run('tell application "Safari" to close current tab of front window')
    else:
        _run(f'tell application "{b}" to close active tab of front window')
    return "Tab closed."


def browser_get_page_title() -> str:
    return get_page_title_text()
