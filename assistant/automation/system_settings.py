"""
assistant/automation/system_settings.py — System Settings, Bluetooth, WiFi.

Opens any Settings pane by voice, toggles Bluetooth/WiFi,
and connects to known Bluetooth devices.
"""

import subprocess
import re
import difflib
import time
import logging

logger = logging.getLogger(__name__)

# ── macOS 13+ System Settings URL schemes ────────────────────────────────────
SETTINGS_URLS = {
    "bluetooth":       "x-apple.systempreferences:com.apple.BluetoothSettings",
    "wifi":            "x-apple.systempreferences:com.apple.wifi-settings-extension",
    "wi-fi":           "x-apple.systempreferences:com.apple.wifi-settings-extension",
    "internet":        "x-apple.systempreferences:com.apple.wifi-settings-extension",
    "display":         "x-apple.systempreferences:com.apple.Displays-Settings.extension",
    "displays":        "x-apple.systempreferences:com.apple.Displays-Settings.extension",
    "brightness":      "x-apple.systempreferences:com.apple.Displays-Settings.extension",
    "sound":           "x-apple.systempreferences:com.apple.Sound-Settings.extension",
    "volume":          "x-apple.systempreferences:com.apple.Sound-Settings.extension",
    "battery":         "x-apple.systempreferences:com.apple.Battery-Settings.extension",
    "network":         "x-apple.systempreferences:com.apple.Network-Settings.extension",
    "vpn":             "x-apple.systempreferences:com.apple.Network-Settings.extension",
    "notifications":   "x-apple.systempreferences:com.apple.Notifications-Settings.extension",
    "privacy":         "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension",
    "security":        "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension",
    "appearance":      "x-apple.systempreferences:com.apple.Appearance-Settings.extension",
    "dark mode":       "x-apple.systempreferences:com.apple.Appearance-Settings.extension",
    "accessibility":   "x-apple.systempreferences:com.apple.Accessibility-Settings.extension",
    "keyboard":        "x-apple.systempreferences:com.apple.Keyboard-Settings.extension",
    "mouse":           "x-apple.systempreferences:com.apple.Mouse-Settings.extension",
    "trackpad":        "x-apple.systempreferences:com.apple.Trackpad-Settings.extension",
    "storage":         "x-apple.systempreferences:com.apple.settings.Storage",
    "users":           "x-apple.systempreferences:com.apple.Users-Groups-Settings.extension",
    "accounts":        "x-apple.systempreferences:com.apple.Users-Groups-Settings.extension",
    "language":        "x-apple.systempreferences:com.apple.Localization-Settings.extension",
    "region":          "x-apple.systempreferences:com.apple.Localization-Settings.extension",
    "software update": "x-apple.systempreferences:com.apple.Software-Update-Settings.extension",
    "updates":         "x-apple.systempreferences:com.apple.Software-Update-Settings.extension",
    "focus":           "x-apple.systempreferences:com.apple.Focus-Settings.extension",
    "do not disturb":  "x-apple.systempreferences:com.apple.Focus-Settings.extension",
    "screen time":     "x-apple.systempreferences:com.apple.Screen-Time-Settings.extension",
    "siri":            "x-apple.systempreferences:com.apple.Siri-Settings.extension",
    "general":         "x-apple.systempreferences:com.apple.GeneralSettings.extension",
    "airdrop":         "x-apple.systempreferences:com.apple.AirDrop-Handoff-Settings.extension",
    "handoff":         "x-apple.systempreferences:com.apple.AirDrop-Handoff-Settings.extension",
    "passwords":       "x-apple.systempreferences:com.apple.Passwords-Settings.extension",
    "wallpaper":       "x-apple.systempreferences:com.apple.Wallpaper-Settings.extension",
    "screen saver":    "x-apple.systempreferences:com.apple.ScreenSaver-Settings.extension",
    "lock screen":     "x-apple.systempreferences:com.apple.Lock-Screen-Settings.extension",
    "touch id":        "x-apple.systempreferences:com.apple.Touch-ID-Settings.extension",
    "printers":        "x-apple.systempreferences:com.apple.Print-Scan-Settings.extension",
    "date":            "x-apple.systempreferences:com.apple.Date-Time-Settings.extension",
    "time":            "x-apple.systempreferences:com.apple.Date-Time-Settings.extension",
    "energy":          "x-apple.systempreferences:com.apple.Battery-Settings.extension",
    "sharing":         "x-apple.systempreferences:com.apple.Sharing-Settings.extension",
    "control centre":  "x-apple.systempreferences:com.apple.ControlCenter-Settings.extension",
    "control center":  "x-apple.systempreferences:com.apple.ControlCenter-Settings.extension",
    "menu bar":        "x-apple.systempreferences:com.apple.ControlCenter-Settings.extension",
    "desktop":         "x-apple.systempreferences:com.apple.Desktops-Settings.extension",
    "mission control": "x-apple.systempreferences:com.apple.Desktops-Settings.extension",
}


def open_setting(name: str) -> str:
    """
    Open a specific macOS System Settings pane by name.
    Fuzzy-matches so 'blooth' → Bluetooth, 'display brightness' → Displays.
    """
    key = name.lower().strip()

    # Exact match
    url = SETTINGS_URLS.get(key)
    if url:
        subprocess.Popen(["open", url])
        return f"Opening {name.title()} settings."

    # Substring match (e.g., 'notification' in 'notifications')
    for k, v in SETTINGS_URLS.items():
        if key in k or k in key:
            subprocess.Popen(["open", v])
            return f"Opening {k.title()} settings."

    # Fuzzy match
    matches = difflib.get_close_matches(key, SETTINGS_URLS.keys(), n=1, cutoff=0.45)
    if matches:
        subprocess.Popen(["open", SETTINGS_URLS[matches[0]]])
        return f"Opening {matches[0].title()} settings."

    # Last resort: open System Settings root
    subprocess.Popen(["open", "-a", "System Settings"])
    return f"I opened System Settings — I couldn't find a specific panel for '{name}'."


# ── Bluetooth ─────────────────────────────────────────────────────────────────

def _bt_state() -> bool:
    """Return True if Bluetooth is currently on."""
    r = subprocess.run(
        ["system_profiler", "SPBluetoothDataType"],
        capture_output=True, text=True, timeout=6
    )
    return "state: On" in r.stdout or '"state" : "attrib_on"' in r.stdout


def toggle_bluetooth(state: str = "toggle") -> str:
    """
    Turn Bluetooth on, off, or toggle it.
    Uses blueutil if installed (brew install blueutil), otherwise
    falls back to networksetup / opening settings.
    """
    # Check for blueutil
    bt_path = subprocess.run(
        ["which", "blueutil"], capture_output=True, text=True
    ).stdout.strip()

    if bt_path:
        if state == "on":
            subprocess.run([bt_path, "--power", "1"])
            return "Bluetooth is now on."
        elif state == "off":
            subprocess.run([bt_path, "--power", "0"])
            return "Bluetooth is now off."
        else:
            cur = subprocess.run(
                [bt_path, "--power"], capture_output=True, text=True
            ).stdout.strip()
            new = "0" if cur == "1" else "1"
            subprocess.run([bt_path, "--power", new])
            return f"Bluetooth is now {'on' if new == '1' else 'off'}."

    # Fallback: open Bluetooth settings so user can toggle
    open_setting("bluetooth")
    currently_on = _bt_state()
    return (f"Bluetooth is currently {'on' if currently_on else 'off'}. "
            f"I've opened the Bluetooth settings panel for you.")


def get_bluetooth_state() -> str:
    on = _bt_state()
    return f"Bluetooth is currently {'on' if on else 'off'}."


def bluetooth_connect(device: str) -> str:
    """Connect to a paired Bluetooth device by name."""
    bt_path = subprocess.run(
        ["which", "blueutil"], capture_output=True, text=True
    ).stdout.strip()

    if bt_path:
        # List paired devices
        result = subprocess.run(
            [bt_path, "--paired"], capture_output=True, text=True, timeout=8
        )
        device_map = {}
        for line in result.stdout.strip().splitlines():
            addr_m = re.search(r"address: ([0-9a-f:-]+)", line)
            name_m = re.search(r'name: "([^"]+)"', line)
            if addr_m and name_m:
                device_map[name_m.group(1).lower()] = addr_m.group(1)

        matches = difflib.get_close_matches(
            device.lower(), device_map.keys(), n=1, cutoff=0.4
        )
        if matches:
            addr = device_map[matches[0]]
            subprocess.Popen([bt_path, "--connect", addr])
            return f"Connecting to {matches[0].title()}."

        if device_map:
            known = ", ".join(k.title() for k in list(device_map.keys())[:5])
            return f"I couldn't find '{device}'. Known devices: {known}."
        return "No paired Bluetooth devices found."

    # No blueutil: open Bluetooth settings
    open_setting("bluetooth")
    return (f"I've opened Bluetooth settings so you can connect to {device}. "
            "For automatic connection by voice, install blueutil: brew install blueutil")


def bluetooth_disconnect(device: str = None) -> str:
    """Disconnect a Bluetooth device."""
    bt_path = subprocess.run(
        ["which", "blueutil"], capture_output=True, text=True
    ).stdout.strip()

    if bt_path and device:
        result = subprocess.run(
            [bt_path, "--paired"], capture_output=True, text=True, timeout=8
        )
        device_map = {}
        for line in result.stdout.strip().splitlines():
            addr_m = re.search(r"address: ([0-9a-f:-]+)", line)
            name_m = re.search(r'name: "([^"]+)"', line)
            if addr_m and name_m:
                device_map[name_m.group(1).lower()] = addr_m.group(1)

        matches = difflib.get_close_matches(
            device.lower(), device_map.keys(), n=1, cutoff=0.4
        )
        if matches:
            addr = device_map[matches[0]]
            subprocess.Popen([bt_path, "--disconnect", addr])
            return f"Disconnected from {matches[0].title()}."

    open_setting("bluetooth")
    return "Opened Bluetooth settings to manage connections."


def list_bluetooth_devices() -> str:
    """List all paired Bluetooth devices."""
    bt_path = subprocess.run(
        ["which", "blueutil"], capture_output=True, text=True
    ).stdout.strip()

    if bt_path:
        result = subprocess.run(
            [bt_path, "--paired"], capture_output=True, text=True, timeout=8
        )
        names = re.findall(r'name: "([^"]+)"', result.stdout)
        if names:
            return "Paired devices: " + ", ".join(names) + "."
        return "No paired Bluetooth devices found."

    return "Install blueutil for device listing: brew install blueutil"


# ── WiFi ─────────────────────────────────────────────────────────────────────

def _wifi_interface() -> str:
    r = subprocess.run(
        ["networksetup", "-listallhardwareports"],
        capture_output=True, text=True
    )
    m = re.search(r"Wi-Fi.*?Device: (\w+)", r.stdout, re.DOTALL)
    return m.group(1) if m else "en0"


def toggle_wifi(state: str = "toggle") -> str:
    iface = _wifi_interface()
    if state == "on":
        subprocess.run(["networksetup", "-setairportpower", iface, "on"])
        return "WiFi is now on."
    elif state == "off":
        subprocess.run(["networksetup", "-setairportpower", iface, "off"])
        return "WiFi is now off."
    else:
        r = subprocess.run(
            ["networksetup", "-getairportpower", iface],
            capture_output=True, text=True
        )
        currently_on = "On" in r.stdout
        new = "off" if currently_on else "on"
        subprocess.run(["networksetup", "-setairportpower", iface, new])
        return f"WiFi is now {new}."


def get_wifi_state() -> str:
    iface = _wifi_interface()
    r = subprocess.run(
        ["networksetup", "-getairportpower", iface],
        capture_output=True, text=True
    )
    return "WiFi is on." if "On" in r.stdout else "WiFi is off."


def get_current_wifi() -> str:
    """Return the name of the connected WiFi network."""
    r = subprocess.run(
        ["/System/Library/PrivateFrameworks/Apple80211.framework/"
         "Versions/Current/Resources/airport", "-I"],
        capture_output=True, text=True, timeout=8
    )
    m = re.search(r"\s+SSID: (.+)", r.stdout)
    if m:
        return f"Connected to {m.group(1).strip()}."
    return "Not connected to any WiFi network."


def connect_wifi(network: str, password: str = "") -> str:
    """Connect to a WiFi network by name."""
    iface = _wifi_interface()
    if password:
        subprocess.run([
            "networksetup", "-setairportnetwork", iface, network, password
        ])
    else:
        subprocess.run(["networksetup", "-setairportnetwork", iface, network])
    time.sleep(2)
    return f"Attempting to connect to {network}."
