# BARVIS — AI Voice Assistant for macOS

Not Siri. Not Alexa. Something actually useful.

BARVIS runs locally on your Mac, wakes up when you say **"Hey Barvis"**, and does what you tell it — opens apps, controls your browser, plays YouTube, sends messages, toggles Bluetooth, checks the weather, reads your calendar. All by voice. No clicking required.

---

## 🚀 What it can actually do

### 1. In-App Context Awareness (New!)
BARVIS doesn't just open apps; it knows how to use them.

```
"In App Store search for Fortnite"   → Opens App Store directly to the results
"In Chrome click the Sign In button" → Clicks it (no mouse needed)
"In Chrome fill in the email field"  → Types your email
"In Telegram search for John"        → Uses Cmd+F to find John
"In Finder search for budget"        → Opens Finder search
```

**Context Memory**: If you say *"Open App Store"* and then follow up with *"Search for Fortnite in it"*, BARVIS remembers the active app and routes the search correctly.

### 2. Open anything
Say *"Open Spotify"*, *"Open Settings"*, *"Open my resume"* — it opens it. BARVIS scans every app on your Mac at startup so there's no hardcoded list to maintain. Works with 130+ apps out of the box.

### 3. Browser control (no clicking)
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

### 4. Compound commands
BARVIS understands multi-step instructions in one go:
> *"Open Chrome and then search Star Wars and then open the first result"*

### 5. Settings navigation
Goes directly to the right panel — no hunting through menus.
```
"Open Bluetooth settings"    → jumps to Bluetooth panel
"Open Display settings"      → jumps to Displays
"Open WiFi settings"         → jumps to Wi-Fi
```

### 6. Native apps — all by voice
```
"Text John saying I'll be late"         → sends iMessage
"Create a note buy groceries"           → creates note in Notes
"Remind me to call mum"                 → adds to Reminders
"What are my reminders?"                → reads them out
"Directions to the airport"             → opens Google Maps with route
"FaceTime Mum"                          → starts a FaceTime call
"Compose email to my boss"              → opens Mail compose window
"Add event to calendar"                 → asks you the details and adds it
```

### 7. Music (Spotify Auto-Play!)
Play, pause, next, previous, volume controls.
If you provide Spotify API credentials, BARVIS will fetch the exact track URI in the background and auto-play it perfectly without touching the UI.
```
"Play Jungle Book"         → Finds the song on Spotify and plays it
"Play the current song"    → Resumes playback
"Next track"               → Skips
```

---

## ⚙️ Setup Instructions

**Requirements:** macOS 12+, Python 3.10+

### Step 1: Install
Clone the repository and run the automated installer script:
```bash
git clone https://github.com/RogerTauraus/Barvis_ARB_V1-.git
cd Barvis_ARB_V1-
./install.sh
```

### Step 2: Configure API Keys
The installer will create an `API/agent.env` file. You need to open this file and add your API keys:

1. **Groq (The Brain)**: Get a free key at [console.groq.com](https://console.groq.com)
2. **Picovoice Porcupine (Wake word)**: Get a free key at [picovoice.ai/console](https://picovoice.ai/console/)
3. **Spotify (Auto-play)**: Create a free app at [developer.spotify.com](https://developer.spotify.com/dashboard) and paste the Client ID / Secret.

### Step 3: Run
```bash
source venv/bin/activate
python voice_assistant.py
```
Say **"Hey Barvis"** to activate. Say **"Sleep Barvis"** to stop.

---

## ⚠️ Important macOS Permissions
You MUST grant your Terminal (or VS Code / iTerm) **Accessibility** permissions for BARVIS to control apps and simulate keystrokes:
1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Toggle your terminal app ON.

*For Chrome in-page clicking to work reliably, you must also enable `Allow JavaScript from Apple Events` in Chrome's Developer menu.*

---

## 🧠 How it works under the hood

```
You speak
  → Wake word detected (Porcupine / OpenWakeWord)
  → Google Speech Recognition converts audio to text
  → BARVIS tries to match a command pattern
  → If no match → LLM (Groq) parses intent and figures out what to do
  → Executes the action (AppleScript / Python / System call)
  → Speaks the response back (ElevenLabs / pyttsx3)
```

---

*Built by [@RogerTauraus](https://github.com/RogerTauraus)*
