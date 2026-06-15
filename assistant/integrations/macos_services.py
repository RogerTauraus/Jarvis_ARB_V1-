"""
macos_services.py — Shared AppleScript runner and macOS notification utility.
Used by all automation modules.
"""

import subprocess
import logging

logger = logging.getLogger(__name__)


def run_applescript(script: str) -> str:
    """
    Execute an AppleScript and return its stdout output.
    Returns empty string on failure; logs the error.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            logger.warning(f"AppleScript error: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("AppleScript timed out.")
        return ""
    except Exception as e:
        logger.error(f"AppleScript execution failed: {e}")
        return ""


def notify(title: str, message: str) -> None:
    """Send a macOS Notification Center notification."""
    script = f'display notification "{message}" with title "{title}"'
    run_applescript(script)
