# JARVIS — AI Voice Assistant for macOS

> *"Something of a localised Siri."* — Inspired by Iron Man's J.A.R.V.I.S.

A fully local, voice-activated AI assistant for macOS. Say **"Hey Jarvis"** and talk to your computer naturally — no typing, no clicking. JARVIS opens apps, controls your browser, reads your calendar, plays YouTube, sends messages, and more.

---

## Features

### 🎙️ Voice Activation
- Wake word: **"Hey Jarvis"** (free, fully local via OpenWakeWord)
- Natural conversation — no robot phrases, no scripted sign-offs
- Sleep: *"Sleep Jarvis"* / Wake: restart the assistant

### 🌐 Browser Automation (Chrome / Safari / Opera GX)
JARVIS controls your browser in real time — no extensions needed.

| Say | What happens |
|-----|-------------|
| *"Open Google"* | Launches Chrome and opens Google |
| *"Open [website].com"* | Navigates directly to any URL |
| *"Search Google for quantum computing"* | Opens search results |
| *"Play Interstellar trailer on YouTube"* | Searches and auto-plays |
| **`"Open the first link"`** | Clicks the 1st visible link on the page |
| **`"Open the second result"`** | Clicks the 2nd search result |
| **`"Click Sign In"`** | Clicks any button/link by its text |
| **`"Type hello in the search box"`** | Types into the active text field |
| *"Press enter"* | Submits the focused form |
| *"Scroll down / up"* | Scrolls the current page |
| *"Go back / forward"* | Browser history navigation |
| *"Refresh page"* | Reloads the current tab |
| *"New tab"* / *"Close tab"* | Tab management |
| *"Pause video"* / *"Next video"* | YouTube playback control |
| *"YouTube fullscreen"* | Toggle fullscreen |

### 📱 App Launcher — Fully Dynamic
No hardcoded list. JARVIS scans **every app on your Mac** at startup.

| Say | What happens |
|-----|-------------|
| *"Open Settings"* | Opens System Settings |
| *"Open Spotify"* | Launches Spotify |
| *"Open FL Studio"* | Launches FL Studio 2025 |
| *"Launch Steam"* | Opens Steam |
| *"Open my resume"* | Finds & opens file from Desktop/Documents/Downloads |
| *"Rescan apps"* | Refreshes index after installing new apps |

### 💬 Native App Control (AppleScript)
| Command | App |
|---------|-----|
| *"Text John saying I'll be late"* | Messages — sends iMessage |
| *"Create a note buy groceries"* | Notes — creates new note |
| *"Remind me to call mum"* | Reminders — adds task |
| *"What are my reminders?"* | Reminders — reads aloud |
| *"Directions to Mumbai airport"* | Maps — driving route |
| *"FaceTime Mum"* | FaceTime — starts video call |
| *"Compose email to boss"* | Mail — opens compose window |
| *"Add event to calendar"* | Calendar — creates event |

### ⏱️ Real-Time Info
| Say | Returns |
|-----|---------|
| *"What time is it?"* | "It's 3:23 PM" |
| *"What day is it?"* | "Today is Monday, June 16" |
| *"What's the weather?"* | "37°C, Haze in Patna" (auto-detects location) |
| *"What's on my calendar?"* | Reads today's events from macOS Calendar |

### 🔊 System Controls
Volume, brightness, sleep, lock, restart, shutdown — all by voice.

### 🎵 Music Control
Play, pause, next, previous, now playing — controls Spotify/Apple Music.

---

## Setup

### Requirements
```
Python 3.10+
macOS 12+
```

### Install
```bash
git clone https://github.com/RogerTauraus/Jarvis_ARB_V1-.git
cd Jarvis_ARB_V1-
pip install -r requirements.txt
```

### Configure API Keys
Create `API/agent.env`:
```env
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here   # optional fallback
```
Get a free Groq key at [console.groq.com](https://console.groq.com) (no credit card needed).

### Run
```bash
python voice_assistant.py
```

Say **"Hey Jarvis"** to activate.

---

## How It Works

```
You speak → Microphone → Wake word detected (OpenWakeWord)
         → Google Speech Recognition → Intent parsed
         → Route to handler:
              Browser automation (AppleScript + JS injection)
              App launcher (dynamic scan + fuzzy match)
              Native app control (AppleScript)
              Real-time data (weather, time, calendar)
              LLM fallback (Groq/Gemini for conversation)
         → Text-to-speech response (pyttsx3)
```

### Architecture
```
voice_assistant.py        ← Main loop, command routing
assistant/
  ai/
    llm_engine.py         ← Groq → Gemini → offline fallback
    memory.py             ← Conversation context
    internet_tools.py     ← Web search
  automation/
    apps.py               ← Dynamic app scanner & launcher
    browser.py            ← Browser automation (JS injection)
    app_controls.py       ← Messages, Notes, Reminders, Maps, FaceTime
    window_control.py     ← Real-time window context & link clicking
    system.py             ← Volume, brightness, system commands
    media.py              ← Music playback
  wakeword/
    porcupine_listener.py ← OpenWakeWord / Porcupine engine
```

---

## Troubleshooting

**JARVIS says it will open something but nothing happens**
- Grant Accessibility access: *System Settings → Privacy & Security → Accessibility → add Terminal / your Python*
- Grant Microphone access: same path → Microphone

**PaMacCore AUHAL -50 errors in log**
- Fixed in v1.1 — wake-word listener now releases mic before each command

**Wake word not detected**
```bash
pip install openwakeword onnxruntime pyaudio
```

---

## Voice Command Quick Reference

```
Open [any app]           Open the first/second link    Play [song] on YouTube
Search Google for [X]    Text [contact] saying [msg]   What time is it?
Remind me to [task]      Directions to [place]         What's the weather?
Scroll down / up         Go back / forward             Pause video / Next video
Click [button text]      Type [text]                   Sleep Jarvis
```

---

*Built by [@RogerTauraus](https://github.com/RogerTauraus)*
