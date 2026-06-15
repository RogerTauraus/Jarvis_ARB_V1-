"""
setup.py — py2app build script for JARVIS Menu Bar app.
Run: python3 setup.py py2app
"""

from setuptools import setup

APP        = ["menubar_app.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,       # must be False for menu bar apps
    "plist": {
        "CFBundleName":             "JARVIS",
        "CFBundleDisplayName":      "JARVIS",
        "CFBundleIdentifier":       "com.jarvis.menubar",
        "CFBundleVersion":          "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "NSHighResolutionCapable":  True,
        "LSUIElement":              True,   # hides from Dock (menu bar only app)
        "NSMicrophoneUsageDescription": "JARVIS needs microphone access for voice commands.",
        "NSAppleEventsUsageDescription": "JARVIS uses AppleScript to control apps.",
    },
    "packages": ["rumps"],
    "excludes": [
        "assistant",        # not needed in the menu bar app itself
        "tkinter",
        "unittest",
        "pydoc",
    ],
    "iconfile": None,       # set to "jarvis.icns" if you have an icon
}

setup(
    app=APP,
    name="JARVIS",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
