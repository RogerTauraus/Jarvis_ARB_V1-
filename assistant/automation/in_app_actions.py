# -*- coding: utf-8 -*-
"""
assistant/automation/in_app_actions.py — In-app action automation for JARVIS.

Lets JARVIS perform actions INSIDE open applications, not just launch them.
Covers: App Store, Chrome, Safari, Finder, Mail, Notes, Telegram, and a
        generic Cmd+F search fallback that works in most macOS apps.
"""

import subprocess
import time
import urllib.parse
import re
import logging

logger = logging.getLogger(__name__)


# ─── AppleScript helper ───────────────────────────────────────────────────────

def _run_as(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        logger.debug(f"in_app AS error: {e}")
        return ""


def _get_frontmost_app() -> str:
    return _run_as('tell application "System Events" to name of first process whose frontmost is true')


# ─── App Store ────────────────────────────────────────────────────────────────

def app_store_search(query: str) -> str:
    """Search the App Store for an app/game by name."""
    encoded = urllib.parse.quote(query)
    # macappstores:// URL scheme opens App Store directly on the search results
    subprocess.run(["open", f"macappstores://search?term={encoded}"],
                   capture_output=True, timeout=5)
    return f"Searching the App Store for '{query}'."


def app_store_open_app_page(app_name: str) -> str:
    """Open a specific app's page in the App Store."""
    encoded = urllib.parse.quote(app_name)
    subprocess.run(["open", f"macappstores://search?term={encoded}"],
                   capture_output=True, timeout=5)
    return f"Opened App Store for '{app_name}'."


# ─── Chrome / browser ────────────────────────────────────────────────────────

def chrome_search_in_page(query: str) -> str:
    """Use Chrome's Cmd+F to find text on the current page."""
    _run_as(f'''
    tell application "Google Chrome" to activate
    delay 0.3
    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 0.4
        keystroke "{query}"
    end tell
    ''')
    return f"Searching for '{query}' on this page."


def chrome_go_to_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    _run_as(f'''
    tell application "Google Chrome"
        activate
        set URL of active tab of front window to "{url}"
    end tell
    ''')
    return f"Navigating to {url}."


def chrome_click_element(description: str) -> str:
    """
    Try to click a button/link by its visible text label via JS injection.
    Works on most websites.
    """
    js = (
        f"(function(){{"
        f"var all=document.querySelectorAll('button,a,[role=button],[role=link]');"
        f"for(var i=0;i<all.length;i++){{"
        f"if(all[i].innerText.toLowerCase().includes('{description.lower()}'))"
        f"{{all[i].click();return 'clicked '+all[i].innerText;}}}}"
        f"return 'not found';}})();"
    )
    result = _run_as(f'''
    tell application "Google Chrome"
        activate
        execute front window's active tab javascript "{js}"
    end tell
    ''')
    if result and "clicked" in result:
        return f"Clicked '{description}'."
    return f"Couldn't find a '{description}' button on this page."


def chrome_fill_form(field_label: str, value: str) -> str:
    """Fill a form field (by placeholder or label) on the current Chrome page."""
    js = (
        f"(function(){{"
        f"var inputs=document.querySelectorAll('input,textarea');"
        f"for(var i=0;i<inputs.length;i++){{"
        f"var ph=(inputs[i].placeholder||'').toLowerCase();"
        f"var nm=(inputs[i].name||'').toLowerCase();"
        f"var id=(inputs[i].id||'').toLowerCase();"
        f"var lbl='{field_label.lower()}';"
        f"if(ph.includes(lbl)||nm.includes(lbl)||id.includes(lbl)){{"
        f"inputs[i].focus();inputs[i].value='{value}';"
        f"inputs[i].dispatchEvent(new Event('input',{{bubbles:true}}));"
        f"return 'filled';}}}}"
        f"return 'not found';}})();"
    )
    result = _run_as(f'''
    tell application "Google Chrome"
        activate
        execute front window's active tab javascript "{js}"
    end tell
    ''')
    if result == "filled":
        return f"Filled in '{value}' for {field_label}."
    return f"Couldn't find the {field_label} field on this page."


def chrome_scroll(direction: str = "down", amount: int = 500) -> str:
    dy = amount if direction == "down" else -amount
    _run_as(f'''
    tell application "Google Chrome"
        execute front window's active tab javascript "window.scrollBy(0,{dy});"
    end tell
    ''')
    return f"Scrolled {direction}."


# ─── Finder ──────────────────────────────────────────────────────────────────

def finder_search(query: str) -> str:
    """Open a Finder search for a file/folder."""
    _run_as(f'''
    tell application "Finder"
        activate
        open location "x-apple.systempreferences:"
    end tell
    ''')
    # Use Cmd+F in Finder
    _run_as(f'''
    tell application "Finder" to activate
    delay 0.5
    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 0.4
        keystroke "{query}"
        key code 36
    end tell
    ''')
    return f"Searching Finder for '{query}'."


# ─── Mail ─────────────────────────────────────────────────────────────────────

def mail_search(query: str) -> str:
    """Search Mail for messages matching a query."""
    _run_as(f'''
    tell application "Mail" to activate
    delay 0.5
    tell application "System Events"
        keystroke "f" using {{option down, command down}}
        delay 0.4
        keystroke "{query}"
        key code 36
    end tell
    ''')
    return f"Searching Mail for '{query}'."


# ─── Notes ───────────────────────────────────────────────────────────────────

def notes_search(query: str) -> str:
    _run_as(f'''
    tell application "Notes" to activate
    delay 0.5
    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 0.4
        keystroke "{query}"
    end tell
    ''')
    return f"Searching Notes for '{query}'."


# ─── Telegram ────────────────────────────────────────────────────────────────

def telegram_search(query: str) -> str:
    """Search for a chat or message in Telegram."""
    _run_as(f'''
    tell application "Telegram" to activate
    delay 0.5
    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 0.4
        keystroke "{query}"
    end tell
    ''')
    return f"Searching Telegram for '{query}'."


def telegram_open_chat(contact: str) -> str:
    """Open a chat with a specific contact in Telegram."""
    _run_as(f'''
    tell application "Telegram" to activate
    delay 0.5
    tell application "System Events"
        keystroke "k" using {{command down}}
        delay 0.4
        keystroke "{contact}"
        delay 0.5
        key code 36
    end tell
    ''')
    return f"Opening chat with {contact} in Telegram."


# ─── Generic in-app search (Cmd+F) ───────────────────────────────────────────

def search_in_frontmost_app(query: str) -> str:
    """
    Use Cmd+F to search within the currently active app.
    Works in most macOS applications.
    """
    app = _get_frontmost_app()
    _run_as(f'''
    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 0.5
        keystroke "{query}"
    end tell
    ''')
    return f"Searching for '{query}' in {app}."


def press_button_in_app(button_label: str, app_name: str = None) -> str:
    """
    Click a button by its label in any macOS app using Accessibility APIs.
    """
    app = app_name or _get_frontmost_app()
    result = _run_as(f'''
    tell application "{app}" to activate
    delay 0.3
    tell application "System Events"
        tell process "{app}"
            try
                click button "{button_label}" of front window
                return "clicked"
            end try
            try
                set allBtns to every button of front window
                repeat with b in allBtns
                    if name of b contains "{button_label}" then
                        click b
                        return "clicked"
                    end if
                end repeat
            end try
        end tell
    end tell
    return "not found"
    ''')
    if result == "clicked":
        return f"Clicked '{button_label}'."
    return f"Couldn't find a '{button_label}' button in {app}."


# ─── Smart in-app router ─────────────────────────────────────────────────────

# Map normalized app names → their search functions
_APP_SEARCH_FUNCTIONS = {
    "appstore":  app_store_search,
    "app store": app_store_search,
    "chrome":    lambda q: search_in_frontmost_app(q),
    "safari":    lambda q: search_in_frontmost_app(q),
    "firefox":   lambda q: search_in_frontmost_app(q),
    "finder":    finder_search,
    "mail":      mail_search,
    "notes":     notes_search,
    "telegram":  telegram_search,
}


def search_in_app(app_name: str, query: str) -> str:
    """
    Route a search command to the right app-specific search function.
    Falls back to generic Cmd+F if the app isn't specifically supported.
    """
    key = app_name.lower().strip()
    func = _APP_SEARCH_FUNCTIONS.get(key) or _APP_SEARCH_FUNCTIONS.get(key.replace(" ", ""))
    if func:
        return func(query)
    # Generic fallback: open app then use Cmd+F
    subprocess.run(["open", "-a", app_name], capture_output=True, timeout=5)
    time.sleep(1.5)
    return search_in_frontmost_app(query)


def get_supported_apps() -> list:
    return list(_APP_SEARCH_FUNCTIONS.keys())
