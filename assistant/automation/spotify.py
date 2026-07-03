# -*- coding: utf-8 -*-
"""
assistant/automation/spotify.py — Full Spotify control for JARVIS on macOS.

Uses Spotify's AppleScript dictionary (most reliable, no API key needed).
Spotify exposes: play, pause, next track, previous track, sound volume,
current track name/artist/album, and search via URI scheme.
"""

import subprocess
import time
import urllib.parse
import logging
import os

logger = logging.getLogger(__name__)


# ─── AppleScript helper ───────────────────────────────────────────────────────

def _as(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        logger.debug(f"Spotify AS error: {e}")
        return ""


# ─── State helpers ────────────────────────────────────────────────────────────

def _is_running() -> bool:
    return _as('application "Spotify" is running') == "true"


def _ensure_open(wait: float = 2.5) -> None:
    if not _is_running():
        subprocess.Popen(["open", "-a", "Spotify"])
        time.sleep(wait)


# ─── Playback controls ────────────────────────────────────────────────────────

def spotify_play_pause() -> str:
    _ensure_open()
    _as('tell application "Spotify" to playpause')
    state = _as('tell application "Spotify" to player state as string')
    return "Resumed." if state == "playing" else "Paused."


def spotify_pause() -> str:
    _ensure_open()
    _as('tell application "Spotify" to pause')
    return "Paused Spotify."


def spotify_resume() -> str:
    _ensure_open()
    _as('tell application "Spotify" to play')
    return "Resuming Spotify."


def spotify_next() -> str:
    _ensure_open()
    _as('tell application "Spotify" to next track')
    time.sleep(0.8)
    return spotify_current_track() or "Skipped to next track."


def spotify_previous() -> str:
    _ensure_open()
    _as('tell application "Spotify" to previous track')
    time.sleep(0.8)
    return spotify_current_track() or "Went back to previous track."


def spotify_volume(level: int) -> str:
    level = max(0, min(100, level))
    _ensure_open()
    _as(f'tell application "Spotify" to set sound volume to {level}')
    return f"Spotify volume set to {level}%."


def spotify_current_track() -> str:
    if not _is_running():
        return "Spotify isn't open right now."
    name   = _as('tell application "Spotify" to name of current track')
    artist = _as('tell application "Spotify" to artist of current track')
    album  = _as('tell application "Spotify" to album of current track')
    if name:
        return f"Playing '{name}' by {artist} — from the album {album}." if album else f"Playing '{name}' by {artist}."
    return "Nothing is playing on Spotify right now."


def spotify_shuffle(on: bool = True) -> str:
    _ensure_open()
    val = "true" if on else "false"
    _as(f'tell application "Spotify" to set shuffling to {val}')
    return f"Shuffle {'on' if on else 'off'}."


def spotify_repeat(on: bool = True) -> str:
    _ensure_open()
    val = "true" if on else "false"
    _as(f'tell application "Spotify" to set repeating to {val}')
    return f"Repeat {'on' if on else 'off'}."


# ─── Search & Play ────────────────────────────────────────────────────────────

def spotify_play(song: str) -> str:
    """
    Search for a song/artist/playlist on Spotify and start playing it.

    Strategy:
    1. Open Spotify via URI search scheme → opens search results
    2. Use AppleScript to activate and let Spotify handle it
    3. Press Enter / click first result via System Events
    """
    _ensure_open(wait=2.0)

    encoded = urllib.parse.quote(song)
    search_uri = f"spotify:search:{encoded}"

    # Open the search URI — Spotify handles this natively
    subprocess.run(["open", search_uri], capture_output=True, timeout=5)
    time.sleep(2.5)

    # Try to play the first result using System Events + AppleScript
    # Spotify's search UI: first result row is clickable via accessibility
    play_script = '''
    tell application "Spotify" to activate
    delay 0.8
    tell application "System Events"
        tell process "Spotify"
            -- Try clicking first track result via accessibility tree
            try
                set allGroups to groups of group 1 of group 1 of window 1
                repeat with g in allGroups
                    try
                        set allRows to rows of table 1 of scroll area 1 of g
                        if (count allRows) > 0 then
                            double click item 1 of allRows
                            return "played"
                        end if
                    end try
                end repeat
            end try
            -- Fallback: press Enter to play first result
            try
                key code 36
                return "enter_pressed"
            end try
        end tell
    end tell
    return "searched"
    '''
    result = _as(play_script, timeout=12)
    time.sleep(1.0)

    # Check if something is now playing
    now = _as('tell application "Spotify" to name of current track')
    if now:
        artist = _as('tell application "Spotify" to artist of current track')
        return f"Playing '{now}' by {artist} on Spotify."

    # If we can't auto-click, at least Spotify is open with search results
    return f"I've searched for '{song}' on Spotify — it's right there on screen, just tap play!"


def spotify_play_artist(artist: str) -> str:
    return spotify_play(f"artist:{artist}")


def spotify_play_album(album: str) -> str:
    return spotify_play(album)


def spotify_play_playlist(playlist: str) -> str:
    return spotify_play(playlist)


def spotify_like_current() -> str:
    """Add current track to Liked Songs using keyboard shortcut."""
    _ensure_open()
    _as('''
    tell application "Spotify" to activate
    delay 0.3
    tell application "System Events"
        keystroke "s" using {command down}
    end tell
    ''')
    name = _as('tell application "Spotify" to name of current track')
    return f"Added '{name}' to your Liked Songs." if name else "Added current track to Liked Songs."


def spotify_open() -> str:
    _ensure_open()
    return "Spotify is open."
