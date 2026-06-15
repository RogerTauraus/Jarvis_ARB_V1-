"""
assistant/automation/apps.py — Dynamic app & document launcher for JARVIS.

NO hardcoded app lists. Scans the entire Mac at startup, builds a
fuzzy-searchable index, and opens anything the user asks for by name.
Works on any Mac without code changes.
"""

import os
import glob
import subprocess
import difflib
import logging
import threading

logger = logging.getLogger(__name__)

# ── Search locations ──────────────────────────────────────────────────────────

_APP_DIRS = [
    "/Applications",
    os.path.expanduser("~/Applications"),
    "/System/Applications",
    "/System/Applications/Utilities",
    "/System/Library/CoreServices",
    "/Applications/Utilities",
]

_DOC_DIRS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
]

_DOC_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".pages", ".numbers", ".key",
    ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".mp3",
    ".zip", ".dmg",
}

# ── In-memory indexes ─────────────────────────────────────────────────────────

_APP_INDEX: dict[str, str] = {}   # normalised_name → /path/to/App.app
_DOC_INDEX: dict[str, str] = {}   # normalised_name → /path/to/file
_cache_lock = threading.Lock()
_cache_ready = threading.Event()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(name: str) -> str:
    """Lowercase, strip spaces/dashes for consistent matching."""
    return name.lower().strip().replace(" ", "").replace("-", "").replace("_", "")


def _build_app_index() -> dict:
    index = {}
    for directory in _APP_DIRS:
        if not os.path.isdir(directory):
            continue
        # Top-level .app bundles
        for app_path in glob.glob(os.path.join(directory, "*.app")):
            raw = os.path.basename(app_path).replace(".app", "")
            # Store both normalised and original-lowercase for matching
            index[raw.lower()] = app_path
            index[_normalise(raw)] = app_path
        # One level deeper (e.g. /Applications/Utilities/*.app)
        for app_path in glob.glob(os.path.join(directory, "*", "*.app")):
            raw = os.path.basename(app_path).replace(".app", "")
            index[raw.lower()] = app_path
            index[_normalise(raw)] = app_path
    return index


def _build_doc_index() -> dict:
    index = {}
    for directory in _DOC_DIRS:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            ext = os.path.splitext(fname)[1].lower()
            if ext in _DOC_EXTENSIONS:
                fpath = os.path.join(directory, fname)
                index[fname.lower()] = fpath
                index[_normalise(os.path.splitext(fname)[0])] = fpath
    return index


def _build_cache():
    """Scan apps and docs; called once in a background thread."""
    global _APP_INDEX, _DOC_INDEX
    with _cache_lock:
        _APP_INDEX = _build_app_index()
        _DOC_INDEX = _build_doc_index()
    _cache_ready.set()
    logger.info(f"[JARVIS] App index ready: {len(_APP_INDEX)} entries, "
                f"{len(_DOC_INDEX)} documents")


# Kick off scanning immediately (non-blocking)
threading.Thread(target=_build_cache, daemon=True).start()


# ── Fuzzy matcher ─────────────────────────────────────────────────────────────

def _find_app(query: str):
    """Return (display_name, path) for the best-matching app, or (None, None)."""
    _cache_ready.wait(timeout=10)

    q_raw  = query.lower().strip()
    q_norm = _normalise(query)

    with _cache_lock:
        candidates = dict(_APP_INDEX)

    def _display(path):
        return os.path.basename(path).replace(".app", "")

    # 1. Exact match (raw or normalised)
    for key in (q_raw, q_norm):
        if key in candidates:
            path = candidates[key]
            return _display(path), path

    # 2. Normalised starts-with (e.g. "vscode" → "Visual Studio Code")
    for name, path in candidates.items():
        if name.startswith(q_norm) and len(q_norm) >= 3:
            return _display(path), path

    # 3. Substring: query is fully contained in app name (must be >= 4 chars)
    if len(q_raw) >= 4:
        for name, path in candidates.items():
            if q_raw in name:
                return _display(path), path
            if q_norm in name:
                return _display(path), path

    # 4. All individual words in query are found in app name
    words = [w for w in q_raw.split() if len(w) >= 3]
    if len(words) > 0:
        for name, path in candidates.items():
            if all(w in name for w in words):
                return _display(path), path

    # 5. Fuzzy difflib — only on normalised keys with tighter cutoff
    matches = difflib.get_close_matches(q_norm, candidates.keys(), n=1, cutoff=0.72)
    if not matches:
        matches = difflib.get_close_matches(q_raw, candidates.keys(), n=1, cutoff=0.72)
    if matches:
        path = candidates[matches[0]]
        return _display(path), path

    return None, None


def _find_doc(query: str):
    """Return (filename, path) for the best-matching document, or (None, None)."""
    _cache_ready.wait(timeout=10)

    q_raw  = query.lower().strip()
    q_norm = _normalise(query)

    with _cache_lock:
        candidates = dict(_DOC_INDEX)

    for key in (q_raw, q_norm):
        if key in candidates:
            path = candidates[key]
            return os.path.basename(path), path

    matches = difflib.get_close_matches(q_raw, candidates.keys(), n=1, cutoff=0.5)
    if not matches:
        matches = difflib.get_close_matches(q_norm, candidates.keys(), n=1, cutoff=0.5)
    if matches:
        path = candidates[matches[0]]
        return os.path.basename(path), path

    return None, None


# ── Public API ────────────────────────────────────────────────────────────────

def open_app(query: str) -> str:
    """Find and open any app by name. Falls back to 'open -a' if index misses."""
    query = query.strip()
    if not query:
        return "What app would you like me to open?"

    display, path = _find_app(query)

    # Try via index
    if path:
        try:
            subprocess.Popen(["open", path])
            return f"Opening {display}."
        except Exception as e:
            logger.warning(f"open_app index launch failed: {e}")

    # Fallback: let macOS resolve it via 'open -a'
    try:
        result = subprocess.run(
            ["open", "-a", query],
            capture_output=True, text=True, timeout=6
        )
        if result.returncode == 0:
            return f"Opening {query}."
    except Exception:
        pass

    # Last resort: Spotlight search + open
    try:
        result = subprocess.run(
            ["mdfind", f"kMDItemKind == 'Application' && kMDItemDisplayName == '{query}'*"],
            capture_output=True, text=True, timeout=5
        )
        paths = [p for p in result.stdout.strip().splitlines() if p.endswith(".app")]
        if paths:
            subprocess.Popen(["open", paths[0]])
            name = os.path.basename(paths[0]).replace(".app", "")
            return f"Opening {name}."
    except Exception:
        pass

    return f"I couldn't find an app called {query} on your Mac."


def open_document(query: str) -> str:
    """Find and open any document from Desktop/Documents/Downloads."""
    query = query.strip()
    display, path = _find_doc(query)
    if path:
        try:
            subprocess.Popen(["open", path])
            return f"Opening {display}."
        except Exception as e:
            return f"Found it but couldn't open it: {e}"

    # Try Spotlight for files anywhere on the Mac
    try:
        result = subprocess.run(
            ["mdfind", f"kMDItemDisplayName == '{query}'*"],
            capture_output=True, text=True, timeout=5
        )
        hits = result.stdout.strip().splitlines()
        # Prefer user home directory results
        user_hits = [h for h in hits if os.path.expanduser("~") in h]
        target = (user_hits or hits or [None])[0]
        if target:
            subprocess.Popen(["open", target])
            return f"Opening {os.path.basename(target)}."
    except Exception:
        pass

    return f"I couldn't find a document called {query}."


def close_app(app_name: str) -> str:
    """Quit a running application by name."""
    display, path = _find_app(app_name)
    target = display or app_name
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{target}" to quit'],
            capture_output=True, timeout=6
        )
        return f"Closing {target}."
    except Exception as e:
        return f"I had trouble closing {target}: {e}"


def switch_app(app_name: str) -> str:
    """Bring a running application to the foreground."""
    display, path = _find_app(app_name)
    target = display or app_name
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{target}" to activate'],
            capture_output=True, timeout=6
        )
        return f"Switching to {target}."
    except Exception as e:
        return f"I couldn't switch to {target}: {e}"


def refresh_index() -> str:
    """Rescan the system for newly installed apps and documents."""
    global _APP_INDEX, _DOC_INDEX
    _cache_ready.clear()
    threading.Thread(target=_build_cache, daemon=True).start()
    _cache_ready.wait(timeout=15)
    return (f"Done. I found {len(_APP_INDEX)//2} apps and "
            f"{len(_DOC_INDEX)//2} documents on your Mac.")
