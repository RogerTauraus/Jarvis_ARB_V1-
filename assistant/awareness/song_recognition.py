# -*- coding: utf-8 -*-
"""
assistant/awareness/song_recognition.py — Shazam-like song recognition for JARVIS.

Records ambient audio from mic, sends to Audd.io (free tier) for identification.
Falls back to local Shazam CLI if available on macOS 12+.

Setup (optional, for higher limits):
  Set AUDD_API_TOKEN in API/agent.env — get a free token at https://audd.io
  Without a token, still gets ~10 free ID calls per day.
"""

import os
import time
import wave
import struct
import tempfile
import logging
import subprocess
import threading

logger = logging.getLogger(__name__)

_SAMPLE_RATE    = 44100
_CHANNELS       = 1
_RECORD_SECONDS = 7   # how long to listen for the song


# ─── Audio recording ──────────────────────────────────────────────────────────

def record_audio(seconds: int = _RECORD_SECONDS) -> str:
    """Record audio from microphone. Returns path to .wav file, or ''."""
    try:
        import sounddevice as sd
        import numpy as np

        recording = sd.rec(
            int(seconds * _SAMPLE_RATE),
            samplerate=_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="float32"
        )
        sd.wait()

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "w") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(2)           # 16-bit
            wf.setframerate(_SAMPLE_RATE)
            pcm = (recording * 32767).astype(np.int16)
            wf.writeframes(pcm.tobytes())
        return tmp.name

    except ImportError:
        logger.warning("sounddevice not installed — trying pyaudio")
        return _record_pyaudio(seconds)
    except Exception as e:
        logger.error(f"record_audio error: {e}")
        return ""


def _record_pyaudio(seconds: int) -> str:
    """Fallback: record using pyaudio."""
    try:
        import pyaudio
        pa  = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16, channels=1,
            rate=_SAMPLE_RATE, input=True,
            frames_per_buffer=1024
        )
        frames = []
        for _ in range(0, int(_SAMPLE_RATE / 1024 * seconds)):
            frames.append(stream.read(1024, exception_on_overflow=False))
        stream.stop_stream()
        stream.close()
        pa.terminate()

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return tmp.name
    except Exception as e:
        logger.error(f"pyaudio record error: {e}")
        return ""


# ─── Audd.io recognition ──────────────────────────────────────────────────────

def _recognize_auddio(audio_path: str) -> dict:
    """Send audio to Audd.io and return result dict."""
    try:
        import requests
        api_token = os.getenv("AUDD_API_TOKEN", "")
        with open(audio_path, "rb") as f:
            resp = requests.post(
                "https://api.audd.io/",
                data={"api_token": api_token, "return": "spotify,apple_music"},
                files={"file": f},
                timeout=20,
            )
        data = resp.json()
        if data.get("status") == "success" and data.get("result"):
            return data["result"]
    except Exception as e:
        logger.warning(f"Audd.io error: {e}")
    return {}


# ─── macOS Shazam CLI (macOS 14+ ships shazam binary) ────────────────────────

def _recognize_shazam_cli(audio_path: str) -> dict:
    """Try the macOS built-in shazam CLI tool."""
    try:
        r = subprocess.run(
            ["shazam", "recognize", audio_path],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode == 0 and r.stdout:
            import json
            data = json.loads(r.stdout)
            # shazam CLI returns matches array
            if data.get("matches"):
                m = data["matches"][0]
                track = data.get("track", {})
                return {
                    "title":  track.get("title", "Unknown"),
                    "artist": track.get("subtitle", "Unknown"),
                    "album":  track.get("sections", [{}])[0].get("metadata", [{}])[0].get("text", ""),
                }
    except FileNotFoundError:
        pass   # shazam CLI not available
    except Exception as e:
        logger.debug(f"shazam CLI error: {e}")
    return {}


# ─── Public API ───────────────────────────────────────────────────────────────

def identify_song() -> str:
    """
    Listen for 7 seconds, identify the song playing nearby, return spoken result.
    """
    logger.info("Song recognition: recording audio...")
    audio_path = record_audio(_RECORD_SECONDS)

    if not audio_path:
        return "I couldn't access the microphone to listen for a song. Check your mic permissions."

    try:
        # Try macOS Shazam CLI first (no API limit)
        result = _recognize_shazam_cli(audio_path)

        # Fall back to Audd.io
        if not result:
            result = _recognize_auddio(audio_path)

        if result:
            title  = result.get("title", "Unknown")
            artist = result.get("artist", "Unknown")
            album  = result.get("album", "")
            album_str = f" from the album {album}" if album else ""
            return f"That's '{title}' by {artist}{album_str}."
        else:
            return "I couldn't identify that song — the music might be too quiet or distorted. Try again closer to the speaker."

    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass


def what_song_is_playing() -> str:
    """Alias for identify_song — friendly response wrapper."""
    return identify_song()
