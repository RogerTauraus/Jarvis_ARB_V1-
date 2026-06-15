"""
media.py — System-wide media playback control for JARVIS.
Controls Spotify, Apple Music, and system media keys via AppleScript.
"""

import subprocess
import logging
from assistant.integrations.macos_services import run_applescript

logger = logging.getLogger(__name__)


def _spotify_command(cmd: str) -> str:
    """Send a command directly to Spotify via AppleScript."""
    script = f'tell application "Spotify" to {cmd}'
    return run_applescript(script)


def _music_command(cmd: str) -> str:
    """Send a command to Apple Music via AppleScript."""
    script = f'tell application "Music" to {cmd}'
    return run_applescript(script)


def _media_key(key_code: int) -> None:
    """
    Simulate a media key press using osascript key code.
    key_code 100 = play/pause, 101 = next, 99 = previous
    """
    script = f'tell application "System Events" to key code {key_code}'
    run_applescript(script)


def play_pause() -> str:
    """Toggle play/pause on whatever is active (Spotify > Music > system key)."""
    # Try Spotify first
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        _spotify_command("playpause")
        return "Toggling playback on Spotify."

    result = run_applescript('application "Music" is running')
    if result == "true":
        _music_command("playpause")
        return "Toggling playback on Apple Music."

    # Fallback: system media key
    _media_key(100)
    return "Toggling media playback."


def play() -> str:
    """Start playback."""
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        _spotify_command("play")
        return "Playing on Spotify."
    _music_command("play")
    return "Playing on Apple Music."


def pause() -> str:
    """Pause playback."""
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        _spotify_command("pause")
        return "Paused Spotify."
    _music_command("pause")
    return "Paused Apple Music."


def next_track() -> str:
    """Skip to the next track."""
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        _spotify_command("next track")
        return "Skipping to next track on Spotify."

    result = run_applescript('application "Music" is running')
    if result == "true":
        _music_command("next track")
        return "Skipping to next track on Apple Music."

    _media_key(101)
    return "Next track."


def prev_track() -> str:
    """Go to the previous track."""
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        _spotify_command("previous track")
        return "Going to previous track on Spotify."

    result = run_applescript('application "Music" is running')
    if result == "true":
        _music_command("previous track")
        return "Going to previous track on Apple Music."

    _media_key(99)
    return "Previous track."


def get_current_track() -> str:
    """Return the currently playing track name and artist."""
    result = run_applescript('application "Spotify" is running')
    if result == "true":
        name = run_applescript('tell application "Spotify" to name of current track')
        artist = run_applescript('tell application "Spotify" to artist of current track')
        if name:
            return f"Now playing: {name} by {artist} on Spotify."

    result = run_applescript('application "Music" is running')
    if result == "true":
        name = run_applescript('tell application "Music" to name of current track')
        artist = run_applescript('tell application "Music" to artist of current track')
        if name:
            return f"Now playing: {name} by {artist} on Apple Music."

    return "No music is currently playing."
