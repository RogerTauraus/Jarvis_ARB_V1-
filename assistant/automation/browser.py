"""
assistant/automation/browser.py — Real-time browser automation for JARVIS.

Strategy:
  • Primary: URL navigation via AppleScript (no JS permission needed)
  • For links: fetch HTML with Python → extract href → navigate
  • JS injection: attempted but gracefully skipped if blocked
  • Works with Chrome, Safari, Opera GX, Brave, Edge
"""

import subprocess
import urllib.request
import urllib.parse
import re
import time
import logging

logger = logging.getLogger(__name__)

BROWSER_NAMES = [
    "Google Chrome", "Brave Browser", "Microsoft Edge",
    "Opera GX", "Opera", "Safari", "Arc",
]

ORDINALS = {
    "first": 1,  "second": 2,  "third": 3,  "fourth": 4,  "fifth": 5,
    "sixth": 6,  "seventh": 7, "eighth": 8, "ninth": 9,   "tenth": 10,
    "1st": 1,    "2nd": 2,     "3rd": 3,    "4th": 4,     "5th": 5,
    "1": 1,      "2": 2,       "3": 3,      "4": 4,       "5": 5,
    "one": 1,    "two": 2,     "three": 3,  "four": 4,    "five": 5,
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36"
}


# ── AppleScript helpers ───────────────────────────────────────────────────────

def _run(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        logger.debug(f"AS error: {e}")
        return ""


def _running_apps() -> list:
    out = _run('tell application "System Events" to get name of every process')
    return [n.strip() for n in out.split(",")]


def _get_browser() -> str:
    """Return the best available browser name."""
    running = _running_apps()
    for b in BROWSER_NAMES:
        if b in running:
            return b
    return "Google Chrome"


def _launch_browser(browser: str) -> None:
    running = _running_apps()
    if browser not in running:
        subprocess.Popen(["open", "-a", browser])
        time.sleep(2.2)


# ── Navigation (works without JS permissions) ─────────────────────────────────

def _navigate(url: str, browser: str = None) -> None:
    """Navigate active tab to URL. Launches browser if needed."""
    b = browser or _get_browser()
    _launch_browser(b)
    time.sleep(0.3)

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
    _run(script)


def get_current_url() -> str:
    """Get the current tab's URL — works without JS permission."""
    b = _get_browser()
    if "Safari" in b:
        return _run('tell application "Safari" to return URL of current tab of front window')
    else:
        return _run(f'tell application "{b}" to return URL of active tab of front window')


def get_current_title() -> str:
    """Get the current tab's title — works without JS permission."""
    b = _get_browser()
    if "Safari" in b:
        return _run('tell application "Safari" to return name of current tab of front window')
    else:
        return _run(f'tell application "{b}" to return title of active tab of front window')


# ── JavaScript injection (optional, works only if user enables it in Chrome) ──

def _try_js(js_code: str) -> str:
    """Attempt JS injection. Returns '' if Chrome has it blocked."""
    b = _get_browser()
    safe = js_code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    if "Safari" in b:
        script = f'tell application "Safari" to do JavaScript "{safe}" in current tab of front window'
    else:
        script = f'tell application "{b}" to execute front window\'s active tab javascript "{safe}"'
    result = _run(script)
    if "AppleScript is turned off" in result or "turned off" in result:
        return ""
    return result


def enable_chrome_js_events() -> str:
    """
    Attempt to enable 'Allow JavaScript from Apple Events' in Chrome.
    Requires Accessibility permission for Terminal/Python.
    """
    script = '''
    tell application "Google Chrome"
        activate
    end tell
    delay 0.4
    tell application "System Events"
        tell process "Google Chrome"
            try
                click menu bar item "View" of menu bar 1
                delay 0.25
                click menu item "Developer" of menu "View" of menu bar 1
                delay 0.25
                set devMenu to menu 1 of menu item "Developer" of menu "View" of menu bar 1
                click menu item "Allow JavaScript from Apple Events" of devMenu
                delay 0.2
                key code 53
                return "enabled"
            on error e
                key code 53
                return "error:" & e
            end try
        end tell
    end tell
    '''
    result = _run(script, timeout=8)
    if result == "enabled":
        return "Chrome JS from Apple Events is now enabled."
    return ""


# ── Python-based page fetching (no Chrome permission needed) ──────────────────

def _fetch_html(url: str) -> str:
    """Fetch raw HTML of a URL using Python. Returns '' on failure."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug(f"Fetch error: {e}")
        return ""


def _extract_links(html: str, exclude_domains: list = None) -> list:
    """Extract all absolute HTTP links from HTML source."""
    exclude = exclude_domains or [
        "google.com", "gstatic.com", "googleapis.com",
        "w3.org", "schema.org", "facebook.com/plugins"
    ]
    raw = re.findall(r'href=["\']((https?://)[^"\'> ]+)["\']', html)
    links = [m[0] for m in raw]
    filtered = []
    seen = set()
    for l in links:
        if any(ex in l for ex in exclude):
            continue
        clean = l.split("#")[0]
        if clean not in seen:
            seen.add(clean)
            filtered.append(clean)
    return filtered


def _google_result_urls(html: str) -> list:
    """
    Extract organic result URLs from Google search HTML.
    Google wraps them in /url?q=... or data-href attributes.
    """
    # Pattern 1: /url?q=ACTUAL_URL&...  (Google redirect wrapper)
    wrapped = re.findall(r'/url\?q=(https?://[^&"\']+)', html)
    unwrapped = [urllib.parse.unquote(u) for u in wrapped]

    # Pattern 2: direct href to non-google domains
    direct = re.findall(
        r'href=["\']((https?://)(?!(?:www\.)?google\.com)(?!accounts\.)(?!support\.google)[^"\'> ]+)["\']',
        html
    )
    direct_links = [m[0] for m in direct]

    # Merge, deduplicate, filter junk
    combined = []
    seen = set()
    for u in unwrapped + direct_links:
        u = u.split("&")[0]  # strip tracking params
        if u not in seen and len(u) > 20:
            seen.add(u)
            combined.append(u)
    return combined


# ── Link / result clicking (URL-based — no JS needed) ─────────────────────────

def click_link(index: int = 1) -> str:
    """
    Click the Nth link on the current page.
    Strategy: get current URL → fetch HTML → extract links → navigate to Nth.
    Falls back to JS injection if available.
    """
    url = get_current_url()
    if not url:
        return "I couldn't detect an open browser tab."

    # Google search: specialised extraction
    if "google.com/search" in url:
        return click_search_result(index)

    # Try JS first (if user has it enabled)
    js_result = _try_js(f"""
    (function(){{
        var els = Array.from(document.querySelectorAll('a[href]')).filter(function(e){{
            var r = e.getBoundingClientRect();
            return r.width > 0 && e.href && e.href.startsWith('http') && e.textContent.trim().length > 0;
        }});
        if(els.length >= {index}) return els[{index-1}].href;
        return '';
    }})()
    """)
    if js_result and js_result.startswith("http"):
        _navigate(js_result)
        return f"Opening link {index}."

    # Fallback: fetch HTML with Python
    html = _fetch_html(url)
    if not html:
        return "I couldn't load the page content."

    links = _extract_links(html)
    if len(links) >= index:
        _navigate(links[index - 1])
        return f"Opening link {index}."

    return f"I found {len(links)} links. Try a smaller number."


def click_search_result(index: int = 1) -> str:
    """
    Click the Nth Google/Bing/DuckDuckGo result.
    Uses 'I'm Feeling Lucky' for first result, Python HTML parse for others.
    """
    url = get_current_url()
    if not url:
        return "I couldn't detect an open browser tab."

    # ── Google ────────────────────────────────────────────────────────────────
    if "google.com/search" in url:
        query_m = re.search(r"[?&]q=([^&]+)", url)
        if not query_m:
            return "I couldn't find the search query."
        query_raw = query_m.group(1)
        query_display = urllib.parse.unquote_plus(query_raw)

        if index == 1:
            # Feeling Lucky = direct first result
            lucky = f"https://www.google.com/search?q={query_raw}&btnI=1"
            _navigate(lucky)
            return f"Opening the top result for '{query_display}'."

        # For 2nd+ results: fetch HTML and parse
        html = _fetch_html(url)
        result_urls = _google_result_urls(html)
        if len(result_urls) >= index:
            _navigate(result_urls[index - 1])
            return f"Opening result {index} for '{query_display}'."
        return (f"I could only find {len(result_urls)} results. "
                f"Try a smaller number.")

    # ── Bing ──────────────────────────────────────────────────────────────────
    if "bing.com/search" in url:
        html = _fetch_html(url)
        results = re.findall(
            r'<h2><a href="(https?://(?!www\.bing\.com)[^"]+)"', html
        )
        if len(results) >= index:
            _navigate(results[index - 1])
            return f"Opening result {index}."
        return f"Found {len(results)} results."

    # Generic fallback
    return click_link(index)


def click_button(text: str) -> str:
    """Click a button/link by text. Uses JS if available, else keyboard simulation."""
    safe = text.replace('"', '\\"')
    js_result = _try_js(f"""
    (function(){{
        var lower = '{safe}'.toLowerCase();
        var els = Array.from(document.querySelectorAll(
            'button, input[type=submit], input[type=button], a, [role=button]'
        ));
        var match = els.find(function(el){{
            var t = (el.textContent || el.value || '').toLowerCase().trim();
            return t.includes(lower) && el.offsetParent !== null;
        }});
        if(match){{ match.click(); return 'ok'; }}
        return '';
    }})()
    """)
    if js_result == "ok":
        return f"Clicked '{text}'."

    # Fallback: try to find href of a link with that text using Python
    url = get_current_url()
    if url:
        html = _fetch_html(url)
        # Find anchor containing the text
        m = re.search(
            rf'<a[^>]+href=["\']([^"\']+)["\'][^>]*>[^<]*{re.escape(text)}[^<]*</a>',
            html, re.IGNORECASE
        )
        if m:
            href = m.group(1)
            if href.startswith("http"):
                _navigate(href)
            else:
                base = "/".join(url.split("/")[:3])
                _navigate(base + "/" + href.lstrip("/"))
            return f"Clicked '{text}'."

    return f"I couldn't find a button or link that says '{text}'."


def type_in_field(text: str, submit: bool = False) -> str:
    """Type text into the active field. Uses JS if available."""
    safe = text.replace('"', '\\"').replace("'", "\\'")
    js = f"""
    (function(){{
        var el = document.querySelector(
            'input[type=text]:not([disabled]), input[type=search]:not([disabled]),
             textarea:not([disabled]), [contenteditable=true]'
        );
        if(el){{
            el.focus(); el.value = '{safe}';
            el.dispatchEvent(new Event('input', {{bubbles:true}}));
            el.dispatchEvent(new Event('change', {{bubbles:true}}));
            {'el.form && el.form.submit();' if submit else ''}
            return 'ok';
        }}
        return '';
    }})()
    """.replace("\n", " ")
    result = _try_js(js)
    if result == "ok":
        return f"Typed '{text}'." + (" Submitted." if submit else "")
    # Fallback: use keyboard
    b = _get_browser()
    _run(f'tell application "{b}" to activate')
    time.sleep(0.3)
    subprocess.run(["osascript", "-e",
        f'tell application "System Events" to keystroke "{safe}"'])
    return f"Typed '{text}'."


def press_enter_on_page() -> str:
    b = _get_browser()
    _run(f'tell application "{b}" to activate')
    subprocess.run(["osascript", "-e",
        'tell application "System Events" to key code 36'])
    return "Pressed Enter."


def get_page_links() -> str:
    """List the first 5 visible links on the current page."""
    url = get_current_url()
    if not url:
        return "No browser tab detected."
    html = _fetch_html(url)
    if not html:
        return "I couldn't load the page."
    links = _extract_links(html)[:5]
    if not links:
        return "I couldn't find any links on this page."
    numbered = [f"{i+1}. {l[:60]}" for i, l in enumerate(links)]
    return "Here are the first links: " + "; ".join(numbered)


# ── YouTube ───────────────────────────────────────────────────────────────────

def youtube_play(query: str) -> str:
    encoded = urllib.parse.quote(query)
    _navigate(f"https://www.youtube.com/results?search_query={encoded}")
    time.sleep(4.0)
    # Try JS to click first result
    js_result = _try_js(
        "(function(){var v=document.querySelector('a#video-title');"
        "if(v){v.click();return 'clicked';}return '';})() "
    )
    if js_result == "clicked":
        return f"Playing '{query}' on YouTube."
    # Fallback: fetch HTML and get first video URL
    url = get_current_url()
    html = _fetch_html(url)
    vid_m = re.search(r'href="(/watch\?v=[^"&]+)"', html)
    if vid_m:
        _navigate("https://www.youtube.com" + vid_m.group(1))
        return f"Playing '{query}' on YouTube."
    return f"YouTube search for '{query}' is open."


def youtube_toggle_pause() -> str:
    _try_js("(function(){var v=document.querySelector('video');if(v){v.paused?v.play():v.pause();}})();")
    return "Toggled playback."


def youtube_next() -> str:
    _try_js("(function(){var b=document.querySelector('.ytp-next-button');if(b)b.click();})();")
    return "Skipping to next."


def youtube_fullscreen() -> str:
    _try_js("(function(){var b=document.querySelector('.ytp-fullscreen-button');if(b)b.click();})();")
    return "Toggling fullscreen."


def youtube_mute() -> str:
    _try_js("(function(){var b=document.querySelector('.ytp-mute-button');if(b)b.click();})();")
    return "Toggled mute."


def youtube_volume(level: int) -> str:
    _try_js(f"(function(){{var v=document.querySelector('video');if(v)v.volume={level/100};}})();")
    return f"Volume set to {level}%."


# ── Web search & navigation ───────────────────────────────────────────────────

def browser_search(query: str, engine: str = "google") -> str:
    urls = {
        "google":  f"https://www.google.com/search?q={urllib.parse.quote(query)}",
        "youtube": f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
        "bing":    f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
    }
    _navigate(urls.get(engine.lower(), urls["google"]))
    return f"Searching {engine.capitalize()} for '{query}'."


def browser_go_to(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    _navigate(url)
    return f"Navigating to {url}."


def browser_go_back() -> str:
    b = _get_browser()
    if "Safari" in b:
        _run('tell application "Safari" to do JavaScript "history.back();" in current tab of front window')
    else:
        _run(f'tell application "{b}" to execute front window\'s active tab javascript "history.back();"')
    return "Going back."


def browser_go_forward() -> str:
    _try_js("history.forward();")
    return "Going forward."


def browser_refresh() -> str:
    b = _get_browser()
    if "Safari" in b:
        _run('tell application "Safari" to do JavaScript "location.reload();" in current tab of front window')
    else:
        _run(f'tell application "{b}" to reload active tab of front window')
    return "Page refreshed."


def browser_scroll(direction: str = "down", amount: int = 600) -> str:
    dy = amount if direction == "down" else -amount
    _try_js(f"window.scrollBy(0,{dy});")
    return f"Scrolling {direction}."


def browser_scroll_top() -> str:
    _try_js("window.scrollTo(0,0);")
    return "Scrolled to top."


def browser_scroll_bottom() -> str:
    _try_js("window.scrollTo(0,document.body.scrollHeight);")
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
    return get_current_title()
