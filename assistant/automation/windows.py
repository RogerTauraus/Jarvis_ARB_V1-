"""
windows.py — macOS window management for JARVIS.
Minimize, maximize, close, move, and split windows via AppleScript + System Events.
"""

import logging
from assistant.integrations.macos_services import run_applescript

logger = logging.getLogger(__name__)


def _get_frontmost_app() -> str:
    """Return the name of the currently focused application."""
    return run_applescript(
        'tell application "System Events" to '
        'get name of first application process whose frontmost is true'
    )


def minimize_window() -> str:
    """Minimize the current frontmost window."""
    app = _get_frontmost_app()
    script = f'tell application "System Events" to tell process "{app}" to click button 2 of window 1'
    run_applescript(script)
    return f"Minimized {app}."


def maximize_window() -> str:
    """Maximize (zoom) the current frontmost window via green button."""
    app = _get_frontmost_app()
    script = f'tell application "System Events" to tell process "{app}" to click button 3 of window 1'
    run_applescript(script)
    return f"Maximized {app}."


def close_window() -> str:
    """Close the current frontmost window."""
    app = _get_frontmost_app()
    script = f'tell application "System Events" to tell process "{app}" to click button 1 of window 1'
    run_applescript(script)
    return f"Closed window in {app}."


def move_left() -> str:
    """Snap current window to the left half using keyboard shortcut (requires macOS Sonoma or Rectangle app)."""
    # Tries Rectangle app shortcut first (ctrl+opt+left), then native macOS tile
    script = (
        'tell application "System Events" to '
        'keystroke (ASCII character 28) using {control down, option down}'
    )
    run_applescript(script)
    return "Moved window to the left."


def move_right() -> str:
    """Snap current window to the right half."""
    script = (
        'tell application "System Events" to '
        'keystroke (ASCII character 29) using {control down, option down}'
    )
    run_applescript(script)
    return "Moved window to the right."


def full_screen() -> str:
    """Toggle full screen for the current window (cmd+ctrl+f)."""
    script = (
        'tell application "System Events" to '
        'keystroke "f" using {command down, control down}'
    )
    run_applescript(script)
    return "Toggled full screen."


def switch_to(app_name: str) -> str:
    """Bring a specific app window to the front."""
    from assistant.automation.apps import switch_app
    return switch_app(app_name)


def split_screen() -> str:
    """Enter macOS Split View for the frontmost window."""
    # Hold green button (btn 3) — this enters Split View on macOS
    app = _get_frontmost_app()
    script = (
        f'tell application "System Events" to tell process "{app}" to '
        f'set value of attribute "AXFullScreen" of window 1 to true'
    )
    run_applescript(script)
    return "Entering full screen to enable Split View. Drag another app from Mission Control."


def list_windows() -> str:
    """List windows of the frontmost application."""
    app = _get_frontmost_app()
    script = (
        f'tell application "System Events" to tell process "{app}" to '
        f'get name of every window'
    )
    result = run_applescript(script)
    return f"Windows open in {app}: {result}" if result else f"No windows found in {app}."
