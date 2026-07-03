# -*- coding: utf-8 -*-
"""
assistant/automation/spotify.py — Full Spotify control for JARVIS on macOS.

Playback strategy (in order of reliability):
 1. Spotify Web API — Client Credentials (search → get URI → AppleScript play)
    Requires SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET in API/agent.env
    Free setup at: https://developer.spotify.com/dashboard (< 2 mins)
 2. AppleScript keyboard automation fallback (no credentials needed)
    Opens Spotify search then simulates keyboard to play top result
"""

import subprocess
import time
import urllib.parse
import logging
import os
import re

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


# ─── Spotify Web API (Client Credentials — search only, no user auth) ─────────

def _get_api_token() -> str:
    """Get a Spotify API token via Client Credentials flow (no user login needed)."""
    cid = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    sec = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        return ""
    try:
        import requests, base64
        auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json().get("access_token", "")
    except Exception as e:
        logger.warning(f"Spotify token error: {e}")
    return ""


def _search_track(query: str) -> tuple:
    """
    Search Spotify API for a track. Returns (track_uri, track_name, artist_name).
    Returns ("", "", "") if credentials missing or search fails.
    """
    token = _get_api_token()
    if not token:
        return "", "", ""
    try:
        import requests
        r = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": 1},
            timeout=8,
        )
        if r.status_code == 200:
            items = r.json().get("tracks", {}).get("items", [])
            if items:
                track = items[0]
                return (
                    track["uri"],                          # e.g. spotify:track:4iV5W9u...
                    track["name"],                         # e.g. "Open Up"
                    track["artists"][0]["name"],           # e.g. "Daniel Caesar"
                )
    except Exception as e:
        logger.warning(f"Spotify search error: {e}")
    return "", "", ""


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
        return (f"Playing '{name}' by {artist} — from the album {album}."
                if album else f"Playing '{name}' by {artist}.")
    return "Nothing is playing on Spotify right now."


def spotify_shuffle(on: bool = True) -> str:
    _ensure_open()
    _as(f'tell application "Spotify" to set shuffling to {"true" if on else "false"}')
    return f"Shuffle {'on' if on else 'off'}."


def spotify_repeat(on: bool = True) -> str:
    _ensure_open()
    _as(f'tell application "Spotify" to set repeating to {"true" if on else "false"}')
    return f"Repeat {'on' if on else 'off'}."


# ─── Search & Play (the hard part) ───────────────────────────────────────────

def _play_via_keyboard(query: str) -> bool:
    """
    Fallback: open search URI then use keyboard navigation to play first result.
    Returns True if we confirmed playback changed.
    """
    # Record what was playing before
    before = _as('tell application "Spotify" to name of current track')

    encoded = urllib.parse.quote(query)
    subprocess.run(["open", f"spotify:search:{encoded}"], capture_output=True, timeout=5)
    time.sleep(3.2)   # wait for search results to fully load

    # Strategy: focus Spotify, press Escape to leave search bar,
    # then Tab to first filter button, Tab again to enter the results grid,
    # then Enter to play. Try multiple sequences.
    sequences = [
        # Sequence A: Escape → Tab → Tab → Enter (navigate to top result card)
        'tell application "Spotify" to activate\ndelay 0.4\n'
        'tell application "System Events"\ntell process "Spotify"\n'
        'key code 53\ndelay 0.3\nkey code 48\ndelay 0.25\nkey code 48\ndelay 0.25\nkey code 36\n'
        'end tell\nend tell',

        # Sequence B: just Enter (sometimes works if top result already selected)
        'tell application "Spotify" to activate\ndelay 0.3\n'
        'tell application "System Events"\ntell process "Spotify"\n'
        'key code 36\nend tell\nend tell',

        # Sequence C: Tab then Enter
        'tell application "Spotify" to activate\ndelay 0.3\n'
        'tell application "System Events"\ntell process "Spotify"\n'
        'key code 48\ndelay 0.3\nkey code 36\nend tell\nend tell',
    ]

    for seq in sequences:
        _as(seq, timeout=8)
        time.sleep(1.2)
        after = _as('tell application "Spotify" to name of current track')
        if after and after != before:
            return True   # something new started playing

    return False


def spotify_play(song: str) -> str:
    """
    Search for a song/artist/album on Spotify and start playing it.

    Method 1 (best): Spotify Web API → get exact track URI → AppleScript play
    Method 2 (fallback): Open search URI + keyboard navigation
    """
    if not song or len(song.strip()) < 2:
        return spotify_resume()

    _ensure_open(wait=2.0)

    # ── Method 1: Web API (requires SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET) ─
    uri, found_name, found_artist = _search_track(song)
    if uri:
        # AppleScript can directly play a Spotify URI — this is 100% reliable
        safe_uri = uri.replace('"', '')
        result = _as(f'tell application "Spotify" to play track "{safe_uri}"', timeout=8)
        time.sleep(1.2)
        # Confirm what's playing
        now    = _as('tell application "Spotify" to name of current track')
        artist = _as('tell application "Spotify" to artist of current track')
        if now:
            return f"Playing '{now}' by {artist} on Spotify."
        # Even if confirmation fails, the track is likely playing
        return f"Playing '{found_name}' by {found_artist} on Spotify."

    # ── Method 2: Keyboard automation fallback ─────────────────────────────────
    logger.info(f"Spotify API not configured — using keyboard fallback for '{song}'")
    played = _play_via_keyboard(song)
    time.sleep(0.5)

    now    = _as('tell application "Spotify" to name of current track')
    artist = _as('tell application "Spotify" to artist of current track')

    if played and now:
        return f"Playing '{now}' by {artist} on Spotify."
    elif now:
        return (f"I searched for '{song}' on Spotify — '{now}' by {artist} is "
                f"showing. Tap the green play button to start it!")
    else:
        return (f"I've searched for '{song}' on Spotify. "
                f"Tap the play button on the first result. "
                f"For auto-play, add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET "
                f"to API/agent.env (free at developer.spotify.com).")


def spotify_play_artist(artist: str) -> str:
    return spotify_play(f"artist:{artist}")


def spotify_play_album(album: str) -> str:
    return spotify_play(album)


def spotify_play_playlist(playlist: str) -> str:
    return spotify_play(playlist)


def spotify_like_current() -> str:
    """Add current track to Liked Songs via keyboard shortcut (Cmd+S)."""
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


# ─── Query extraction helper ──────────────────────────────────────────────────

def extract_spotify_query(statement: str) -> str:
    """
    Extract just the song/artist name from a voice command.
    Handles: 'play X', 'in Spotify play X', 'open Spotify and play X',
             'listen to X on Spotify', 'put on X', etc.
    """
    stmt = statement.lower().strip()

    # Step 1: Remove app-context words anywhere in the phrase
    for pat in [r'\bon spotify\b', r'\bin spotify\b', r'\bvia spotify\b',
                r'\bwith spotify\b', r'\bopen spotify and\b', r'\bopen spotify\b',
                r'\bspotify\b']:
        stmt = re.sub(pat, '', stmt, flags=re.IGNORECASE)

    # Step 2: Find the LAST occurrence of a command verb and take everything after it
    # This handles "listen to open up by Daniel Caesar" → "open up by Daniel Caesar"
    cmd_re = re.compile(
        r'\b(play me|play|put on|listen to|search for|search|find me|find|'
        r'look up|start playing|start|queue)\b\s*',
        re.IGNORECASE
    )
    matches = list(cmd_re.finditer(stmt))
    if matches:
        query = stmt[matches[-1].end():].strip()
    else:
        query = stmt.strip()

    # Step 3: Strip leading filler words but NOT song-title words like "open", "the"
    # Only strip from start if they're standalone fillers
    query = re.sub(r'^(the song|the track|song called|track called|a song called)\s+',
                   '', query, flags=re.IGNORECASE)

    return ' '.join(query.split()).strip()
