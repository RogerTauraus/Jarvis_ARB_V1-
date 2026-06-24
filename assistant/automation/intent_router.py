"""
assistant/automation/intent_router.py — LLM-based generative command understanding.

When JARVIS hears something that doesn't match a hardcoded pattern, this module
sends the command to the LLM and gets back a structured list of actions to execute.

Also handles compound commands: "open Chrome and search Star Wars and open first result"
→ [open Chrome] → [search Star Wars] → [click result 1]
"""

import re
import json
import time
import logging

logger = logging.getLogger(__name__)

# ── Compound command splitting ────────────────────────────────────────────────
_SPLITTER = re.compile(
    r'\s+(?:and then|and also|then|after that|afterwards|next|also|,'
    r'|followed by|after which)\s+',
    re.IGNORECASE
)

def split_compound(statement: str) -> list:
    """
    Split 'do X and then do Y and then do Z' into ['do X', 'do Y', 'do Z'].
    Returns a single-item list if no compound detected.
    """
    parts = _SPLITTER.split(statement)
    return [p.strip() for p in parts if p.strip()]


# ── Action definitions (what the LLM can choose from) ─────────────────────────
ACTION_SCHEMA = """
AVAILABLE ACTIONS (return as a JSON array):
- {"type": "open_app", "name": "app name"}
- {"type": "open_url", "url": "https://..."}
- {"type": "search_web", "query": "search terms", "engine": "google|youtube|bing"}
- {"type": "click_result", "index": 1}
- {"type": "click_link", "index": 1}
- {"type": "click_button", "text": "button text"}
- {"type": "type_text", "text": "text", "submit": true}
- {"type": "press_enter"}
- {"type": "scroll", "direction": "up|down"}
- {"type": "open_setting", "name": "bluetooth|wifi|display|sound|privacy|battery|..."}
- {"type": "toggle_bluetooth", "state": "on|off|toggle"}
- {"type": "toggle_wifi", "state": "on|off|toggle"}
- {"type": "bluetooth_connect", "device": "device name"}
- {"type": "bluetooth_disconnect", "device": "device name"}
- {"type": "list_bt_devices"}
- {"type": "get_wifi_state"}
- {"type": "get_bluetooth_state"}
- {"type": "set_volume", "level": 50}
- {"type": "go_back"}
- {"type": "go_forward"}
- {"type": "refresh_page"}
- {"type": "new_tab"}
- {"type": "close_tab"}
- {"type": "speak", "text": "response to say to user"}
"""

_SYSTEM_PROMPT = (
    "You are JARVIS, an AI assistant that controls a Mac computer. "
    "Parse voice commands into executable actions. "
    "Return ONLY a valid JSON array. No explanation, no markdown, no code blocks."
)


def llm_parse_actions(statement: str, context: dict = None) -> list:
    """
    Use the LLM to parse an arbitrary voice command into a list of actions.
    Returns [] if parsing fails.
    """
    ctx_str = ""
    if context and context.get("is_browser"):
        ctx_str = (
            f"\nActive browser: {context.get('app', 'Chrome')}"
            f"\nCurrent URL: {context.get('url', 'unknown')}"
            f"\nPage type: {context.get('page_type', 'generic')}"
        )

    prompt = (
        f"Voice command: \"{statement}\"\n"
        f"{ctx_str}\n\n"
        f"{ACTION_SCHEMA}\n"
        "Return JSON array only:"
    )

    try:
        from assistant.ai.llm_engine import ask_llm
        from assistant.ai.memory import ConversationMemory
        mem = ConversationMemory()
        # Pass a special flag so ask_llm doesn't wrap in conversation prose
        response = ask_llm(prompt, mem)
        # Extract JSON array from response
        json_m = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_m:
            actions = json.loads(json_m.group())
            if isinstance(actions, list):
                return actions
    except Exception as e:
        logger.debug(f"LLM parse error: {e}")

    return []


# ── Action executor ───────────────────────────────────────────────────────────

def execute_action(action: dict) -> str:
    """Execute a single parsed action dict. Returns a string response."""
    t = action.get("type", "")

    if t == "open_app":
        from assistant.automation.apps import open_app
        return open_app(action.get("name", ""))

    elif t == "open_url":
        url = action.get("url", "")
        if "youtube.com" in url:
            from assistant.automation.browser import browser_go_to, youtube_play
            import urllib.parse as _up
            # If it's a search URL, extract query and use youtube_play
            parsed = _up.urlparse(url)
            qs = _up.parse_qs(parsed.query)
            query = qs.get("search_query", [""])[0]
            if query:
                return youtube_play(query)
            else:
                # Channel or video URL - just navigate
                browser_go_to(url)
                return "Opening that YouTube page now."
        else:
            from assistant.automation.browser import browser_go_to
            browser_go_to(url)
            domain = url.split("/")[2] if "/" in url else url
            return f"Opening {domain} now."

    elif t == "search_web":
        from assistant.automation.browser import browser_search
        result = browser_search(action.get("query", ""), action.get("engine", "google"))
        time.sleep(3.5)   # wait for results page to load
        return result

    elif t == "click_result":
        from assistant.automation.browser import click_search_result
        time.sleep(1.5)   # brief wait for any previous nav to settle
        return click_search_result(action.get("index", 1))

    elif t == "click_link":
        from assistant.automation.browser import click_link
        time.sleep(1.0)
        return click_link(action.get("index", 1))

    elif t == "click_button":
        from assistant.automation.browser import click_button
        return click_button(action.get("text", ""))

    elif t == "type_text":
        from assistant.automation.browser import type_in_field
        return type_in_field(action.get("text", ""), action.get("submit", False))

    elif t == "press_enter":
        from assistant.automation.browser import press_enter_on_page
        return press_enter_on_page()

    elif t == "scroll":
        from assistant.automation.browser import browser_scroll
        return browser_scroll(action.get("direction", "down"))

    elif t == "open_setting":
        from assistant.automation.system_settings import open_setting
        return open_setting(action.get("name", ""))

    elif t == "toggle_bluetooth":
        from assistant.automation.system_settings import toggle_bluetooth
        return toggle_bluetooth(action.get("state", "toggle"))

    elif t == "toggle_wifi":
        from assistant.automation.system_settings import toggle_wifi
        return toggle_wifi(action.get("state", "toggle"))

    elif t == "bluetooth_connect":
        from assistant.automation.system_settings import bluetooth_connect
        return bluetooth_connect(action.get("device", ""))

    elif t == "bluetooth_disconnect":
        from assistant.automation.system_settings import bluetooth_disconnect
        return bluetooth_disconnect(action.get("device", ""))

    elif t == "list_bt_devices":
        from assistant.automation.system_settings import list_bluetooth_devices
        return list_bluetooth_devices()

    elif t == "get_bluetooth_state":
        from assistant.automation.system_settings import get_bluetooth_state
        return get_bluetooth_state()

    elif t == "get_wifi_state":
        from assistant.automation.system_settings import get_wifi_state
        return get_wifi_state()

    elif t == "set_volume":
        from assistant.automation.system import set_volume
        return set_volume(action.get("level", 50))

    elif t == "go_back":
        from assistant.automation.browser import browser_go_back
        return browser_go_back()

    elif t == "go_forward":
        from assistant.automation.browser import browser_go_forward
        return browser_go_forward()

    elif t == "refresh_page":
        from assistant.automation.browser import browser_refresh
        return browser_refresh()

    elif t == "new_tab":
        from assistant.automation.browser import browser_new_tab
        return browser_new_tab()

    elif t == "close_tab":
        from assistant.automation.browser import browser_close_tab
        return browser_close_tab()

    elif t == "speak":
        return action.get("text", "")

    else:
        logger.warning(f"Unknown action type: {t}")
        return ""


def execute_actions(actions: list, speak_fn=None) -> str:
    """
    Execute a list of actions sequentially.
    Optionally calls speak_fn(response) after each action so the user
    gets live feedback.
    Returns the last non-empty response.
    """
    last = ""
    for action in actions:
        resp = execute_action(action)
        if resp:
            last = resp
            if speak_fn:
                speak_fn(resp)
    return last


# ── High-level entry point ────────────────────────────────────────────────────

def route_with_llm(statement: str, speak_fn=None) -> str:
    """
    Full pipeline:
    1. Get current window context
    2. Ask LLM to parse the command into actions
    3. Execute actions sequentially
    4. Return combined response
    """
    try:
        from assistant.automation.window_control import get_window_context
        context = get_window_context()
    except Exception:
        context = {}

    actions = llm_parse_actions(statement, context)
    if not actions:
        return ""   # caller should fall back to regular LLM chat

    return execute_actions(actions, speak_fn)
