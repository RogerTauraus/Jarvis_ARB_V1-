"""
menubar_app.py — JARVIS macOS Menu Bar App (py2app compatible)
Shows a ⬡ icon in the menu bar to start/stop/restart JARVIS.
"""

import rumps
import subprocess
import os
import signal
import threading
import time
from pathlib import Path

JARVIS_DIR = Path("/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Jarvis_v1")
PYTHON     = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
LOG_DIR    = JARVIS_DIR / "logs"
LOG_OUT    = LOG_DIR / "jarvis.log"
LOG_ERR    = LOG_DIR / "jarvis_error.log"
PID_FILE   = LOG_DIR / "jarvis.pid"
PLIST_DST  = Path.home() / "Library/LaunchAgents/com.jarvis.assistant.plist"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None

def _alive(pid) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def _autostart_on() -> bool:
    return PLIST_DST.exists()


# ── App ────────────────────────────────────────────────────────────────────────

class JarvisApp(rumps.App):

    def __init__(self):
        super().__init__("JARVIS", title="⬡", quit_button=None)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        self.status   = rumps.MenuItem("● Stopped")
        self.btn_start   = rumps.MenuItem("▶  Start JARVIS",        callback=self.on_start)
        self.btn_stop    = rumps.MenuItem("■  Stop JARVIS",         callback=None)
        self.btn_restart = rumps.MenuItem("↺  Restart JARVIS",      callback=None)
        self.btn_log     = rumps.MenuItem("📋 View Logs",            callback=self.on_logs)
        self.btn_auto    = rumps.MenuItem("🚀 Enable Auto-Start",    callback=self.on_autostart)
        self.btn_perms   = rumps.MenuItem("🔐 Grant Permissions",    callback=self.on_perms)
        self.btn_quit    = rumps.MenuItem("Quit",                    callback=rumps.quit_application)

        self.menu = [
            self.status, None,
            self.btn_start, self.btn_stop, self.btn_restart, None,
            self.btn_log, None,
            self.btn_auto, self.btn_perms, None,
            self.btn_quit,
        ]

        self._refresh()
        threading.Thread(target=self._poll, daemon=True).start()

    # ── Polling ────────────────────────────────────────────────────────────────

    def _poll(self):
        while True:
            time.sleep(3)
            self._refresh()

    def _refresh(self):
        running = _alive(_pid())
        self.status.title = f"● Running (PID {_pid()})" if running else "● Stopped"

        self.btn_start.set_callback(None if running else self.on_start)
        self.btn_stop.set_callback(self.on_stop if running else None)
        self.btn_restart.set_callback(self.on_restart if running else None)

        self.btn_auto.title = (
            "✅ Auto-Start ON  (click to disable)"
            if _autostart_on() else
            "🚀 Enable Auto-Start at Login"
        )

    # ── Actions ────────────────────────────────────────────────────────────────

    def on_start(self, _=None):
        if _alive(_pid()):
            return
        LOG_DIR.mkdir(exist_ok=True)

        # Strip py2app bundle env vars so the subprocess uses system site-packages
        env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE",
                    "RESOURCEPATH", "EXECUTABLEPATH"):
            env.pop(key, None)
        # Ensure correct PATH so system Python finds all tools
        env["PATH"] = (
            "/Library/Frameworks/Python.framework/Versions/3.13/bin:"
            "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        )

        p = subprocess.Popen(
            [PYTHON, "voice_assistant.py"],
            cwd=str(JARVIS_DIR),
            stdout=open(LOG_OUT, "a"),
            stderr=open(LOG_ERR, "a"),
            start_new_session=True,
            env=env,
        )
        PID_FILE.write_text(str(p.pid))
        self._refresh()
        rumps.notification("JARVIS", "Started", "Say 'Hey Jarvis' to activate!")

    def on_stop(self, _=None):
        pid = _pid()
        if not _alive(pid):
            return
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if _alive(pid):
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        PID_FILE.unlink(missing_ok=True)
        self._refresh()
        rumps.notification("JARVIS", "Stopped", "JARVIS has been shut down.")

    def on_restart(self, _=None):
        self.on_stop()
        time.sleep(1.2)
        self.on_start()

    def on_logs(self, _):
        if LOG_OUT.exists():
            subprocess.run(["open", str(LOG_OUT)])
        else:
            rumps.alert("No logs yet. Start JARVIS first.")

    def on_autostart(self, _):
        if _autostart_on():
            subprocess.run(["launchctl", "unload", str(PLIST_DST)], capture_output=True)
            PLIST_DST.unlink(missing_ok=True)
            rumps.notification("JARVIS", "Auto-Start Disabled", "JARVIS won't start at login.")
        else:
            PLIST_DST.parent.mkdir(parents=True, exist_ok=True)
            PLIST_DST.write_text(_plist_content(run_at_load=True))
            subprocess.run(["launchctl", "load", str(PLIST_DST)], capture_output=True)
            rumps.notification("JARVIS", "Auto-Start Enabled", "JARVIS will start at every login.")
        self._refresh()

    def on_perms(self, _):
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
        ])
        rumps.alert(
            title="Grant These Permissions",
            message=(
                "In Privacy & Security, enable:\n\n"
                "🎙  Microphone  → Terminal / Python\n"
                "♿  Accessibility → Terminal / Python\n"
                "🤖  Automation  → Terminal → System Events\n\n"
                "Then restart JARVIS from the menu."
            )
        )


# ── Plist helper ───────────────────────────────────────────────────────────────

def _plist_content(run_at_load: bool) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.jarvis.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON}</string>
        <string>{JARVIS_DIR}/voice_assistant.py</string>
    </array>
    <key>WorkingDirectory</key><string>{JARVIS_DIR}</string>
    <key>StandardOutPath</key><string>{LOG_OUT}</string>
    <key>StandardErrorPath</key><string>{LOG_ERR}</string>
    <key>RunAtLoad</key><{"true" if run_at_load else "false"}/>
    <key>KeepAlive</key><true/>
    <key>ThrottleInterval</key><integer>5</integer>
    <key>SessionCreate</key><true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key><string>/Users/ashwinrogerbaxla</string>
        <key>PYTHONUNBUFFERED</key><string>1</string>
    </dict>
</dict></plist>"""


# ── Entry ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    JarvisApp().run()
