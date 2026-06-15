# JARVIS — AI Voice Assistant for macOS

> *"Sometimes you gotta run before you can walk."* — Tony Stark

A fully local, privacy-first AI voice assistant for macOS — inspired by Iron Man's J.A.R.V.I.S. Built with Python, powered by Groq (Llama 3.3-70B), and integrated directly into your Mac's menu bar.

---

## ✨ Features

| Category | Capabilities |
|---|---|
| 🧠 **AI Intelligence** | Groq (Llama 3.3-70B) → Gemini 2.0 Flash → OpenAI GPT-4o-mini cascade |
| 🎙️ **Wake Word** | "Hey Jarvis" — always listening via OpenWakeWord (free, no account) |
| 🗣️ **Voice Output** | ElevenLabs TTS or macOS Samantha (fallback) |
| 🖥️ **App Control** | Open/close/switch 50+ macOS apps by voice |
| ⚙️ **System Control** | Volume, brightness, sleep, lock, shutdown, restart |
| 🎵 **Media Control** | Spotify/Apple Music play/pause/skip/what's playing |
| 🪟 **Window Management** | Minimize, maximize, snap left/right, full screen |
| 📁 **File System** | Create, search, open files and folders |
| 🌐 **Web & Search** | Wikipedia, WolframAlpha, DuckDuckGo, YouTube |
| 📧 **Email** | Send emails via Gmail by voice |
| 💬 **Memory** | Remembers conversation context across turns |
| ⬡ **Menu Bar App** | Native macOS menu bar — no Terminal needed |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/RogerTauraus/Jarvis_ARB_V1--.git
cd Jarvis_v1
```

### 2. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Set up API keys
```bash
cp API/agent.env.example API/agent.env
# Edit API/agent.env and fill in your keys
```

**Free keys needed:**
- **Groq** (primary LLM — fastest): [console.groq.com](https://console.groq.com) → API Keys
- **Gemini** (backup LLM): [aistudio.google.com](https://aistudio.google.com) → Get API Key

### 4. Run JARVIS
```bash
python3 voice_assistant.py
```

### 5. (Optional) Install as macOS menu bar app
```bash
python3 setup.py py2app
cp -R dist/JARVIS.app /Applications/
open /Applications/JARVIS.app
```

---

## 🧠 How the AI works

JARVIS uses a **multi-provider LLM cascade** — if one fails, it silently falls back to the next:

```
Your voice → Speech Recognition
                    ↓
           Groq (Llama 3.3-70B)   ← primary, ultra-fast
                    ↓ if unavailable
           Gemini 2.0 Flash        ← free backup
                    ↓ if unavailable
           OpenAI GPT-4o-mini      ← optional
                    ↓ if unavailable
           Offline fallback        ← time, date, jokes, etc.
                    ↓
           ElevenLabs / Samantha   ← spoken response
```

JARVIS has a **personality** — it matches your emotional tone, varies every response, and greets you differently based on the time of day.

---

## 🗣️ Example Commands

```
"Hey Jarvis, open WhatsApp"
"What is quantum computing?"
"Play music on Spotify"
"Set volume to 60"
"I'm feeling stressed today"
"Send an email to John"
"What's the time?"
"Open the App Store"
"Minimize window"
"Search Wikipedia for black holes"
"Tell me a joke"
```

---

## 🏗️ Architecture

```
Jarvis_v1/
├── voice_assistant.py          # Main loop + command processing
├── menubar_app.py              # macOS menu bar interface (rumps)
├── setup.py                   # py2app build config
├── assistant/
│   ├── ai/
│   │   ├── llm_engine.py      # Multi-provider LLM cascade + personality
│   │   ├── memory.py          # Conversation memory
│   │   └── internet_tools.py  # Online/offline detection
│   ├── automation/
│   │   ├── apps.py            # App open/close/switch (50+ apps)
│   │   ├── system.py          # Volume, brightness, sleep, lock
│   │   ├── media.py           # Spotify / Apple Music control
│   │   └── windows.py         # Window management
│   ├── filesystem/
│   │   └── files.py           # File create/search/open
│   ├── integrations/
│   │   └── macos_services.py  # AppleScript bridge
│   └── wakeword/
│       └── porcupine_listener.py  # OpenWakeWord "Hey Jarvis"
└── API/
    └── agent.env.example      # API key template
```

---

## 📦 Requirements

```
Python 3.13+
macOS 13 Ventura or later (Apple Silicon recommended)
```

Key packages: `speech_recognition`, `groq`, `google-genai`, `openai`, `elevenlabs`, `rumps`, `openwakeword`, `wikipedia`, `pyaudio`

---

## 🔑 API Keys

| Service | Required | Free Tier | Link |
|---|---|---|---|
| **Groq** | ✅ Yes | 14,400 req/day | [console.groq.com](https://console.groq.com) |
| **Gemini** | Optional | 1,500 req/day | [aistudio.google.com](https://aistudio.google.com) |
| **OpenAI** | Optional | Paid only | [platform.openai.com](https://platform.openai.com) |
| **ElevenLabs** | Optional | Limited free | [elevenlabs.io](https://elevenlabs.io) |
| **WolframAlpha** | Optional | Free tier | [developer.wolframalpha.com](https://developer.wolframalpha.com) |

---

## 🛡️ Privacy

- **No data leaves your Mac** unless you explicitly use an LLM API
- Wake word detection runs **100% locally** via OpenWakeWord
- API keys stored **only in your local `API/agent.env`** (git-ignored)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/RogerTauraus">Ashwin Baxla</a>
</p>
