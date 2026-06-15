"""
system.py — macOS system controls for JARVIS.
Volume, brightness, sleep, lock, shutdown, restart — via AppleScript and osascript.
"""

import subprocess
import logging
from assistant.integrations.macos_services import run_applescript

logger = logging.getLogger(__name__)


# ── Volume ────────────────────────────────────────────────────────────────────

def set_volume(level: int) -> str:
    """Set system volume. level = 0–100."""
    level = max(0, min(100, int(level)))
    # macOS volume scale is 0–7 for osascript set volume, or use output volume
    run_applescript(f"set volume output volume {level}")
    return f"Volume set to {level} percent."


def get_volume() -> int:
    """Return current output volume (0–100)."""
    result = run_applescript("output volume of (get volume settings)")
    try:
        return int(result)
    except (ValueError, TypeError):
        return -1


def volume_up(step: int = 10) -> str:
    """Increase volume by step percent."""
    current = get_volume()
    if current < 0:
        current = 50
    return set_volume(current + step)


def volume_down(step: int = 10) -> str:
    """Decrease volume by step percent."""
    current = get_volume()
    if current < 0:
        current = 50
    return set_volume(current - step)


def mute() -> str:
    """Mute system audio."""
    run_applescript("set volume with output muted")
    return "System muted."


def unmute() -> str:
    """Unmute system audio."""
    run_applescript("set volume without output muted")
    return "System unmuted."


# ── Brightness ────────────────────────────────────────────────────────────────

def set_brightness(level: int) -> str:
    """
    Set display brightness. level = 0–100.
    Uses the `brightness` CLI tool (install via: brew install brightness).
    Falls back gracefully if not installed.
    """
    level = max(0, min(100, int(level)))
    pct = level / 100.0
    try:
        result = subprocess.run(
            ["brightness", str(pct)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Brightness set to {level} percent."
        else:
            return "Brightness control requires the 'brightness' tool. Install with: brew install brightness"
    except FileNotFoundError:
        return "Brightness control requires the 'brightness' CLI tool. Run: brew install brightness"
    except Exception as e:
        logger.error(f"set_brightness error: {e}")
        return "Could not change brightness."


# ── Power Controls ────────────────────────────────────────────────────────────

def sleep_mac() -> str:
    """Put the Mac to sleep."""
    run_applescript('tell application "System Events" to sleep')
    return "Putting your Mac to sleep. Goodnight."


def lock_mac() -> str:
    """Lock the screen immediately."""
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "q" using {command down, control down}'],
        timeout=5
    )
    return "Screen locked."


def shutdown_mac() -> str:
    """Initiate system shutdown."""
    run_applescript('tell application "System Events" to shut down')
    return "Shutting down. Goodbye."


def restart_mac() -> str:
    """Initiate system restart."""
    run_applescript('tell application "System Events" to restart')
    return "Restarting your Mac."


def logout_mac() -> str:
    """Log out the current user."""
    run_applescript('tell application "System Events" to log out')
    return "Logging out."
