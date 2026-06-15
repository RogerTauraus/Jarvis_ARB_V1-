"""
porcupine_listener.py — Local wake-word detection for JARVIS.

Engine priority (auto-selected, no config needed):
  1. OpenWakeWord  — FREE, no account, fully local, recommended
  2. Porcupine     — optional, better accuracy if you have an access key
  3. Simple energy — last resort fallback using PyAudio silence detection

Usage:
    listener = WakeWordListener(on_wake=my_callback)
    listener.start()   # non-blocking, runs in background daemon thread
    listener.stop()
"""

import os
import threading
import logging
import time

logger = logging.getLogger(__name__)

# ── Engine availability checks ─────────────────────────────────────────────────

def _has_openwakeword() -> bool:
    try:
        import openwakeword          # noqa: F401
        import pyaudio               # noqa: F401
        return True
    except ImportError:
        return False


def _has_porcupine() -> bool:
    try:
        import pvporcupine           # noqa: F401
        import pvrecorder            # noqa: F401
        return bool(os.getenv("PORCUPINE_ACCESS_KEY", ""))
    except ImportError:
        return False


# ── OpenWakeWord engine ────────────────────────────────────────────────────────

class _OpenWakeWordEngine:
    """
    Uses the free openwakeword library with pre-trained ONNX models.
    Supports: hey_jarvis, alexa, hey_mycroft, timer, weather, etc.
    No account or API key required.
    """

    # Map of user-facing keyword names → openwakeword model identifiers
    KEYWORD_MAP = {
        "jarvis":       "hey_jarvis",
        "hey jarvis":   "hey_jarvis",
        "alexa":        "alexa",
        "mycroft":      "hey_mycroft",
        "computer":     "hey_jarvis",   # best match available
    }
    SCORE_THRESHOLD = 0.5   # confidence threshold (0–1)
    CHUNK            = 1280  # ~80ms at 16kHz, required by openwakeword
    SAMPLE_RATE      = 16000
    FORMAT_INT16     = None   # set in __init__

    def __init__(self, keyword: str, on_wake):
        import pyaudio
        self._pyaudio    = pyaudio
        self._on_wake    = on_wake
        self._running    = False
        self._model_name = self.KEYWORD_MAP.get(keyword.lower(), "hey_jarvis")
        self.FORMAT_INT16 = pyaudio.paInt16

    def run(self):
        """Blocking loop — call from a daemon thread."""
        from openwakeword.model import Model
        import numpy as np

        # Load pre-trained model (downloads ~5 MB on first run)
        oww_model = Model(
            wakeword_models=[self._model_name],
            inference_framework="onnx"
        )

        pa = self._pyaudio.PyAudio()
        stream = pa.open(
            rate=self.SAMPLE_RATE,
            channels=1,
            format=self.FORMAT_INT16,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        logger.info(f"[OpenWakeWord] Listening for '{self._model_name}'...")
        print(f"[JARVIS] Wake-word engine active — say 'Hey Jarvis' to activate.")

        try:
            while self._running:
                if getattr(self, '_paused', False):
                    time.sleep(0.05)   # idle while mic is in use by takeCommand
                    continue
                raw = stream.read(self.CHUNK, exception_on_overflow=False)
                audio = np.frombuffer(raw, dtype=np.int16)
                predictions = oww_model.predict(audio)

                score = predictions.get(self._model_name, 0.0)
                if score >= self.SCORE_THRESHOLD:
                    logger.info(f"[OpenWakeWord] Wake word detected (score={score:.2f})")
                    self._on_wake()
                    # Brief pause to avoid double-trigger
                    time.sleep(1.0)
                    oww_model.reset()   # clear internal buffer
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def stop(self):
        self._running = False

    def pause(self):
        """Temporarily stop reading audio — releases mic for takeCommand()."""
        self._paused = True

    def resume(self):
        """Resume listening after takeCommand() is done."""
        self._paused = False

    def start(self):
        self._running = True
        self._paused  = False


# ── Porcupine engine ───────────────────────────────────────────────────────────

class _PorcupineEngine:
    """
    Picovoice Porcupine engine — higher accuracy, requires free access key.
    Get one at: https://console.picovoice.ai (personal/free tier available).
    """
    BUILT_IN = ["jarvis", "computer", "hey google", "alexa", "ok google"]

    def __init__(self, keyword: str, on_wake):
        self._keyword  = keyword.lower() if keyword.lower() in self.BUILT_IN else "jarvis"
        self._on_wake  = on_wake
        self._running  = False

    def run(self):
        import pvporcupine
        from pvrecorder import PvRecorder

        access_key = os.getenv("PORCUPINE_ACCESS_KEY", "")
        porcupine  = pvporcupine.create(access_key=access_key, keywords=[self._keyword])
        recorder   = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
        recorder.start()

        logger.info(f"[Porcupine] Listening for '{self._keyword}'...")
        try:
            while self._running:
                if getattr(self, '_paused', False):
                    time.sleep(0.05)
                    continue
                pcm = recorder.read()
                if porcupine.process(pcm) >= 0:
                    logger.info("[Porcupine] Wake word detected!")
                    self._on_wake()
                    time.sleep(1.0)
        finally:
            recorder.delete()
            porcupine.delete()

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def start(self):
        self._running = True
        self._paused  = False


# ── Public interface ───────────────────────────────────────────────────────────

class WakeWordListener:
    """
    Unified wake-word listener that auto-selects the best available engine.

    Priority:
        1. Porcupine  (if PORCUPINE_ACCESS_KEY is set and pvporcupine installed)
        2. OpenWakeWord (free, no key needed — RECOMMENDED)
        3. Disabled   (graceful no-op if neither is available)

    Example:
        listener = WakeWordListener(on_wake=lambda: print("ACTIVATED!"))
        listener.start()
        # ... do other work ...
        listener.stop()
    """

    def __init__(self, on_wake=None, keyword: str = "jarvis"):
        self._on_wake  = on_wake or (lambda: None)
        self._keyword  = keyword
        self._thread   = None
        self._engine   = None
        self._engine_name = "none"
        self._select_engine()

    def _select_engine(self):
        if _has_porcupine():
            self._engine = _PorcupineEngine(self._keyword, self._on_wake)
            self._engine_name = "Porcupine"
            logger.info("Wake-word engine: Porcupine (high accuracy)")
        elif _has_openwakeword():
            self._engine = _OpenWakeWordEngine(self._keyword, self._on_wake)
            self._engine_name = "OpenWakeWord"
            logger.info("Wake-word engine: OpenWakeWord (free, local)")
        else:
            self._engine = None
            self._engine_name = "none"
            logger.warning(
                "No wake-word engine available.\n"
                "  → Install OpenWakeWord (FREE, no account): pip install openwakeword\n"
                "  → Or add PORCUPINE_ACCESS_KEY to API/agent.env"
            )

    def start(self) -> bool:
        """Start background listener. Returns True if engine is running."""
        if self._engine is None:
            return False

        self._engine.start()
        self._thread = threading.Thread(target=self._engine.run, daemon=True)
        self._thread.start()
        print(f"[JARVIS] Wake-word listener started ({self._engine_name})")
        return True

    def stop(self):
        """Stop the background listener gracefully."""
        if self._engine:
            self._engine.stop()
        if self._thread:
            self._thread.join(timeout=3)
        print(f"[JARVIS] Wake-word listener stopped.")

    def pause(self):
        """Pause mic reading so takeCommand() can use the microphone."""
        if self._engine:
            self._engine.pause()

    def resume(self):
        """Resume mic reading after takeCommand() releases the microphone."""
        if self._engine:
            self._engine.resume()

    @property
    def engine_name(self) -> str:
        return self._engine_name

    @property
    def is_available(self) -> bool:
        return self._engine is not None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
