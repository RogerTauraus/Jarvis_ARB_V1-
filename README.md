# JARVIS — AI Voice Assistant for macOS

Not Siri. Not Alexa. Something actually useful.

JARVIS runs locally on your Mac, wakes up when you say **"Hey Jarvis"**, and does what you tell it — opens apps, controls your browser, plays YouTube, sends messages, toggles Bluetooth, checks the weather, reads your calendar. All by voice. No clicking required.

---

## What it can actually do

### Open anything
Say *"Open Spotify"*, *"Open Settings"*, *"Open my resume"* — it opens it. JARVIS scans every app on your Mac at startup so there's no hardcoded list to maintain. Works with 130+ apps out of the box.

### Browser control (no clicking)
Works with Chrome, Safari, Opera GX.

```
"Open Google"                         → opens Google in Chrome
"Search Star Wars on Google"          → searches and shows results
"Play Interstellar trailer on YouTube"→ searches and auto-plays it
"Open the first link"                 → clicks link #1 on whatever page is open
"Open the second result"              → clicks search result #2
"Scroll down" / "Go back"            → exactly what it sounds like
"New tab" / "Close tab"              → tab management
```

### Compound commands
JARVIS understands multi-step instructions in one go:

> *"Open Chrome and then search Star Wars and then open the first result"*

It breaks that into 3 steps and does all of them in sequence.

### Settings navigation
Goes directly to the right panel — no hunting through menus.

```
"Open Bluetooth settings"    → jumps to Bluetooth panel
"Open Display settings"      → jumps to Displays
"Open WiFi settings"         → jumps to Wi-Fi
"Open Notification settings" → you get the idea
```
Works for 30+ system settings panels.

### Bluetooth & WiFi
```
"Turn on Bluetooth"          → turns it on
"Turn off Bluetooth"         → turns it off
"Connect to AirPods"         → connects to your paired device by name
"Turn off WiFi"              → kills WiFi
"What network am I on?"      → tells you
```

### Native apps — all by voice
```
"Text John saying I'll be late"         → sends iMessage
"Create a note buy groceries"           → creates note in Notes
"Remind me to call mum"                 → adds to Reminders
"What are my reminders?"                → reads them out
"Directions to the airport"             → opens Maps with route
"FaceTime Mum"                          → starts a FaceTime call
"Compose email to my boss"              → opens Mail compose window
"Add event to calendar"                 → asks you the details and adds it
```

### Real-time info
```
"What time is it?"     → "It's 3:23 PM"
"What's the date?"     → "Today is Monday, June 16"
"What's the weather?"  → "37°C, clear skies in Mumbai" (auto-detects location)
"What's on my calendar today?" → reads today's events
```

### System controls
Volume, brightness, sleep, lock, restart, shutdown — all by voice.

### Music
Play, pause, next, previous, now playing — controls Spotify and Apple Music.

---

## Setup

**Requirements:** Python 3.10+, macOS 12+

```bash
git clone https://github.com/RogerTauraus/Jarvis_ARB_V1-.git
cd Jarvis_ARB_V1-
pip install -r requirements.txt
```

**Get a free API key** (for the AI brain) at [console.groq.com](https://console.groq.com) — no credit card needed.

Create `API/agent.env`:
```
GROQ_API_KEY=your_key_here
```

**Run it:**
```bash
python voice_assistant.py
```

Say **"Hey Jarvis"** to activate. Say **"Sleep Jarvis"** to stop.

---

## One-time setup you should know about

**Accessibility permission (for full app control):**
System Settings → Privacy & Security → Accessibility → add Terminal

**Enable in-browser typing/button clicking:**
Chrome → View → Developer → Allow JavaScript from Apple Events

Without these, most things still work — these just unlock the last bits.

---

## How it works under the hood

```
You speak
  → Wake word detected (OpenWakeWord, runs locally)
  → Google Speech Recognition converts audio to text
  → JARVIS tries to match a command pattern
  → If no match → LLM (Groq) parses intent and figures out what to do
  → Executes the action (AppleScript / Python / System call)
  → Speaks the response back (pyttsx3)
```

For browser link clicking specifically: instead of injecting JavaScript (which Chrome blocks by default), JARVIS fetches the page HTML with Python, pulls out the link URLs, and navigates Chrome directly. No permissions, no fuss.

---

## File structure

```
voice_assistant.py              ← main loop, all command routing
assistant/
  ai/
    llm_engine.py               ← Groq → Gemini → offline fallback chain
    memory.py                   ← keeps conversation context
    internet_tools.py           ← web search
  automation/
    apps.py                     ← scans + launches all apps dynamically
    browser.py                  ← browser automation (URL-based, no JS needed)
    app_controls.py             ← Messages, Notes, Reminders, Maps, FaceTime, Mail
    system_settings.py          ← Settings panels, Bluetooth, WiFi
    window_control.py           ← detects active window, routes contextual commands
    intent_router.py            ← LLM parses compound/natural language commands
    system.py                   ← volume, brightness, sleep, shutdown
    media.py                    ← music playback
  wakeword/
    porcupine_listener.py       ← wake word engine
```

---

## Common issues

**"It says it's opening something but nothing happens"**
Fixed in the latest version. Was a Chrome JS restriction issue — now uses direct URL navigation instead.

**"Open first link says I'm not sure what to do"**
Also fixed. Now works regardless of which app is frontmost.

**Microphone errors (PaMacCore AUHAL -50)**
Fixed. The wake word listener properly releases the mic before each command.

**Wake word not working**
```bash
pip install openwakeword onnxruntime pyaudio
```

---

## Quick reference

```
Hey Jarvis                    → wake up
Sleep Jarvis                  → go to sleep
Open [any app]                → launches it
Open [setting] settings       → opens that settings panel
Open the first link           → clicks first link on current page
Search [X] on Google          → searches Google
Play [song] on YouTube        → finds and plays it
Turn on/off Bluetooth         → toggles Bluetooth
Connect to [device]           → connects Bluetooth device
Text [contact] saying [msg]   → sends iMessage
Remind me to [task]           → adds to Reminders
What's the weather?           → tells you, with your location
[X] and then [Y] and then [Z] → does all three in order
```

---

*Built by [@RogerTauraus](https://github.com/RogerTauraus)*
