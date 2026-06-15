"""
apps.py — macOS application management for JARVIS.
Open, close, quit, and switch between applications using AppleScript and subprocess.
"""

import subprocess
import logging
from assistant.integrations.macos_services import run_applescript

logger = logging.getLogger(__name__)

# Map of spoken names → macOS application bundle names
APP_MAP = {
    # Browsers
    "safari":           "Safari",
    "chrome":           "Google Chrome",
    "google chrome":    "Google Chrome",
    "firefox":          "Firefox",
    "brave":            "Brave Browser",
    "edge":             "Microsoft Edge",
    "opera":            "Opera",

    # Dev tools
    "vs code":              "Visual Studio Code",
    "vscode":               "Visual Studio Code",
    "visual studio code":   "Visual Studio Code",
    "visual studio":        "Visual Studio Code",
    "cursor":               "Cursor",
    "terminal":             "Terminal",
    "iterm":                "iTerm",
    "xcode":                "Xcode",
    "android studio":       "Android Studio",
    "pycharm":              "PyCharm",
    "webstorm":             "WebStorm",
    "github desktop":       "GitHub Desktop",
    "sourcetree":           "Sourcetree",
    "postman":              "Postman",

    # System & Utilities
    "finder":               "Finder",
    "app store":            "App Store",
    "activity monitor":     "Activity Monitor",
    "system preferences":   "System Preferences",
    "system settings":      "System Preferences",
    "calculator":           "Calculator",
    "preview":              "Preview",
    "textedit":             "TextEdit",
    "text edit":            "TextEdit",
    "console":              "Console",
    "disk utility":         "Disk Utility",
    "screenshot":           "Screenshot",
    "keychain access":      "Keychain Access",

    # Communication
    "messages":             "Messages",
    "mail":                 "Mail",
    "facetime":             "FaceTime",
    "zoom":                 "zoom.us",
    "slack":                "Slack",
    "discord":              "Discord",
    "whatsapp":             "WhatsApp",
    "telegram":             "Telegram",
    "signal":               "Signal",
    "teams":                "Microsoft Teams",
    "microsoft teams":      "Microsoft Teams",
    "skype":                "Skype",

    # Social
    "instagram":            "Instagram",
    "twitter":              "Twitter",
    "x":                    "Twitter",
    "reddit":               "Reddit",

    # Media
    "spotify":              "Spotify",
    "apple music":          "Music",
    "music":                "Music",
    "podcasts":             "Podcasts",
    "vlc":                  "VLC",
    "photos":               "Photos",
    "quicktime":            "QuickTime Player",
    "quick time":           "QuickTime Player",
    "imovie":               "iMovie",
    "garageband":           "GarageBand",
    "garage band":          "GarageBand",

    # Productivity
    "notes":                "Notes",
    "calendar":             "Calendar",
    "reminders":            "Reminders",
    "maps":                 "Maps",
    "notion":               "Notion",
    "obsidian":             "Obsidian",
    "bear":                 "Bear",
    "things":               "Things 3",

    # Microsoft Office
    "word":                 "Microsoft Word",
    "excel":                "Microsoft Excel",
    "powerpoint":           "Microsoft PowerPoint",
    "outlook":              "Microsoft Outlook",
    "onenote":              "Microsoft OneNote",

    # Apple iWork
    "pages":                "Pages",
    "numbers":              "Numbers",
    "keynote":              "Keynote",

    # Design
    "figma":                "Figma",
    "sketch":               "Sketch",
    "photoshop":            "Adobe Photoshop 2025",
    "illustrator":          "Adobe Illustrator 2025",
    "lightroom":            "Adobe Lightroom",
}


def _resolve_app(name: str) -> str:
    """Resolve a spoken app name to the macOS application name."""
    name_lower = name.lower().strip()
    return APP_MAP.get(name_lower, name.title())  # fallback: capitalize


def open_app(name: str) -> str:
    """Open a macOS application by spoken name."""
    app = _resolve_app(name)
    try:
        result = subprocess.run(
            ["open", "-a", app],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info(f"Opened: {app}")
            return f"Opening {app}."
        else:
            logger.warning(f"Could not open {app}: {result.stderr.strip()}")
            return f"I couldn't find an app called {name}. Make sure it's installed."
    except Exception as e:
        logger.error(f"open_app error: {e}")
        return f"Something went wrong while opening {name}."


def close_app(name: str) -> str:
    """Quit a macOS application gracefully via AppleScript."""
    app = _resolve_app(name)
    script = f'tell application "{app}" to quit'
    run_applescript(script)
    return f"Closing {app}."


def switch_app(name: str) -> str:
    """Bring a macOS application to the foreground."""
    app = _resolve_app(name)
    script = f'tell application "{app}" to activate'
    run_applescript(script)
    return f"Switching to {app}."


def restart_app(name: str) -> str:
    """Quit and reopen an application."""
    close_app(name)
    import time
    time.sleep(1.5)
    return open_app(name)


def list_running_apps() -> list[str]:
    """Return a list of currently running application names."""
    script = (
        'tell application "System Events" to '
        'get name of every process whose background only is false'
    )
    output = run_applescript(script)
    if output:
        return [a.strip() for a in output.split(",")]
    return []
