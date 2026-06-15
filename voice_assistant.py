import speech_recognition as sr
import datetime
import os
import time
import subprocess
import wikipedia
import webbrowser
from ecapture import ecapture as ec
import wolframalpha
import json
import requests
import smtplib
import platform
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from elevenlabs.client import ElevenLabs

# ── New module imports (non-breaking additions) ───────────────────────────────
from assistant.ai.llm_engine import ask_llm
from assistant.ai.memory import ConversationMemory
from assistant.ai.internet_tools import is_online, web_search
from assistant.automation.apps import open_app, close_app, switch_app, open_document, refresh_index
from assistant.automation.system import (
    set_volume, volume_up, volume_down, mute, unmute,
    set_brightness, sleep_mac, lock_mac, shutdown_mac, restart_mac
)
from assistant.automation.media import (
    play_pause, play, pause, next_track, prev_track, get_current_track
)
from assistant.automation.windows import (
    minimize_window, maximize_window, close_window,
    move_left, move_right, full_screen, switch_to
)
from assistant.filesystem.file_manager import FileManager
from assistant.wakeword.porcupine_listener import WakeWordListener

# Load env from API/agent.env
_env_path = os.path.join(os.path.dirname(__file__), 'API', 'agent.env')
load_dotenv(dotenv_path=_env_path)

# Initialize ElevenLabs client
_el_api_key = os.getenv('ELEVENLABS_API_KEY', '')
el_client = ElevenLabs(api_key=_el_api_key) if _el_api_key else None
VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')

# ── New module initialization ─────────────────────────────────────────────────
_memory = ConversationMemory()  # session-scoped conversation memory
_file_manager = None            # initialized after speak() is defined


def speak(text):
    """
    Speak text aloud.
    Primary  : macOS Samantha voice (always available, no API key needed)
    Optional : ElevenLabs TTS (set ELEVENLABS_API_KEY in API/agent.env to enable)
    """
    print(f"JARVIS: {text}")

    if el_client:
        try:
            audio_chunks = el_client.text_to_speech.convert(
                voice_id=VOICE_ID,
                text=text,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128",
            )
            audio_bytes = b"".join(audio_chunks)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            subprocess.run(["afplay", tmp_path], check=False)
            os.unlink(tmp_path)
            return
        except Exception:
            pass  # silently fall through to Samantha

    # macOS Samantha — clear, natural, no API needed
    subprocess.run(["say", "-v", "Samantha", "-r", "175", text], check=False)




def wishMe():
    """Greet the user with a time-aware, personality-driven opening."""
    import random
    from assistant.ai.llm_engine import get_greeting

    hour = datetime.datetime.now().hour

    # Time-aware greeting from the engine
    greeting = get_greeting()

    # Varied follow-up lines that match the time of day
    if 5 <= hour < 12:
        follow_ups = [
            "I'm fully online and ready to assist you today.",
            "All systems are running perfectly. What shall we tackle first?",
            "I've got everything prepped and ready to go. What do you need?",
        ]
    elif 12 <= hour < 17:
        follow_ups = [
            "I'm here and ready whenever you need me.",
            "What can I help you accomplish this afternoon?",
            "All systems nominal. What are we working on?",
        ]
    elif 17 <= hour < 21:
        follow_ups = [
            "How was your day? Let me know what you need.",
            "I'm here for you this evening. What can I do?",
            "Ready and waiting. What shall we do tonight?",
        ]
    else:
        follow_ups = [
            "Burning the midnight oil? I'm here to help.",
            "Still going strong. What do you need?",
            "I'm awake and fully operational. What's on your mind?",
        ]

    full_greeting = f"{greeting} {random.choice(follow_ups)}"
    speak(full_greeting)
    print(full_greeting)


def takeCommand():
    # Pause wake-word listener so both don't fight over the microphone
    try:
        _wake_listener.pause()
    except Exception:
        pass

    r = sr.Recognizer()
    statement = "None"
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.adjust_for_ambient_noise(source, duration=0.3)
            r.pause_threshold = 1
            audio = r.listen(source, timeout=8, phrase_time_limit=12)
        try:
            statement = r.recognize_google(audio, language='en-in')
            print(f"user said: {statement}\n")
        except sr.UnknownValueError:
            speak("Pardon me, please say that again.")
        except sr.RequestError:
            speak("I can't reach the speech service. Check your internet connection.")
        except Exception:
            speak("Pardon me, please say that again.")
    except Exception as e:
        print(f"[Mic error] {e}")

    # Always resume the wake-word listener
    try:
        _wake_listener.resume()
    except Exception:
        pass

    return statement


print("[JARVIS] Starting up...")
wishMe()

# ── Post-speak() module setup ─────────────────────────────────────────────────

def _confirmation_handler(prompt: str) -> bool:
    """Verbal confirmation gate for destructive file operations."""
    speak(prompt)
    response = takeCommand().lower()
    return any(w in response for w in ["yes", "confirm", "proceed", "do it", "sure"])

_file_manager = FileManager(confirm_fn=_confirmation_handler)

# Start wake-word listener in background (silent fail if key not set)
_wake_listener = WakeWordListener(
    on_wake=lambda: print("[WAKE WORD DETECTED] Activating JARVIS..."),
    keyword="jarvis"
)
_wake_listener.start()

# Log connectivity status
if is_online():
    print("[JARVIS] Online mode active. LLM + internet tools available.")
else:
    print("[JARVIS] Offline mode. Local commands only.")

if __name__ == '__main__':
    while True:
        statement = takeCommand().lower()
        if statement == "None":
            continue

        # ── Sleep / Stop commands ─────────────────────────────────────────────
        if any(p in statement for p in [
            "sleep jarvis", "jarvis sleep", "goodbye jarvis", "bye jarvis",
            "good bye", "ok bye", "shut down jarvis", "jarvis quit", "stop jarvis"
        ]):
            speak("Going to sleep. Call me whenever you need me.")
            break

        elif 'open youtube' in statement:
            webbrowser.open_new_tab("https://www.youtube.com")
            speak("youtube is open now")
            time.sleep(5)

        elif 'open google' in statement:
            webbrowser.open_new_tab("https://www.google.com")
            speak("Google chrome is open now")
            time.sleep(5)

        elif 'open gmail' in statement:
            webbrowser.open_new_tab("https://gmail.com")
            speak("Google Mail open now")
            time.sleep(5)

        elif 'wikipedia' in statement:
            speak('Searching Wikipedia...')
            query = statement.replace("wikipedia", "").strip()
            try:
                results = wikipedia.summary(query, sentences=3)
                speak("According to Wikipedia")
                print(results)
                speak(results)
            except wikipedia.exceptions.DisambiguationError:
                speak("The search term is ambiguous. Please be more specific.")
            except wikipedia.exceptions.PageError:
                speak("The page was not found. Please try a different search.")
            except Exception as e:
                speak("An error occurred while searching Wikipedia")
                print(e)

        # ── Real-time: Time ───────────────────────────────────────────────────
        elif any(p in statement for p in ['what time', 'current time', "what's the time", 'tell me the time']):
            now = datetime.datetime.now()
            hour = now.strftime("%I").lstrip("0")
            mins = now.strftime("%M")
            period = now.strftime("%p")
            if mins == "00":
                speak(f"It's {hour} {period}.")
            else:
                speak(f"It's {hour} {mins} {period}.")

        # ── Real-time: Calendar / Date ────────────────────────────────────────
        elif any(p in statement for p in ['calendar', 'what day', 'what date', "today's date", 'schedule']):
            now = datetime.datetime.now()
            day   = now.strftime("%A")
            date  = now.strftime("%B %d, %Y")
            # Try to pull today's events from macOS Calendar via AppleScript
            try:
                script = '''
                tell application "Calendar"
                    set todayStart to current date
                    set time of todayStart to 0
                    set todayEnd to todayStart + (86399)
                    set eventList to ""
                    repeat with c in every calendar
                        repeat with e in every event of c
                            set s to start date of e
                            if s >= todayStart and s <= todayEnd then
                                set eventList to eventList & summary of e & ", "
                            end if
                        end repeat
                    end repeat
                    return eventList
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=8
                ).stdout.strip().rstrip(", ")
                if result:
                    speak(f"Today is {day}, {date}. You have these events: {result}.")
                else:
                    speak(f"Today is {day}, {date}. Your calendar looks clear today.")
            except Exception:
                speak(f"Today is {day}, {date}.")

        # ── Real-time: Temperature / Weather ──────────────────────────────────
        elif any(p in statement for p in [
            'temperature', 'weather', "how hot", "how cold", "what's the weather",
            'weather today', 'current weather'
        ]):
            try:
                # Detect city from IP
                loc = requests.get("https://ipinfo.io/json", timeout=5).json()
                city    = loc.get("city", "your location")
                country = loc.get("country", "")
                # Fetch weather from wttr.in (free, no API key)
                w = requests.get(
                    f"https://wttr.in/{city}?format=%t+%C",
                    timeout=5
                ).text.strip()
                speak(f"Right now in {city}, {country}, it's {w}.")
            except Exception as e:
                speak("I couldn't fetch the weather right now. Check your internet connection.")
                print(e)

        elif "camera" in statement or "take a photo" in statement:
            try:
                ec.capture(0, "robo camera", "img.jpg")
                speak("Photo captured successfully")
            except Exception as e:
                speak("Unable to capture photo")
                print(e)

        elif 'search' in statement:
            query = statement.replace("search", "").strip()
            webbrowser.open_new_tab(f"https://www.google.com/search?q={query}")
            speak(f"Searching for {query}")
            time.sleep(5)

        elif 'ask' in statement:
            speak('I can answer to computational and geographical questions. What question do you want to ask now?')
            question = takeCommand()
            if question != "None":
                try:
                    api_key = os.getenv('WOLFRAM_API_KEY')
                    if not api_key:
                        speak(
                            "Wolfram API key not found. Please set it in your .env file")
                        continue
                    client = wolframalpha.Client(api_key)
                    res = client.query(question)
                    answer = next(res.results).text
                    speak(answer)
                    print(answer)
                except StopIteration:
                    speak("Sorry, I could not find an answer to that question")
                except Exception as e:
                    speak("An error occurred while processing your question")
                    print(e)

        elif "log off" in statement or "sign out" in statement:
            speak(
                "Ok, your pc will log off in 10 sec. Make sure you exit from all applications")
            try:
                if platform.system() == 'Windows':
                    subprocess.call(["shutdown", "/l"])
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.call(
                        ["osascript", "-e", "tell application \"System Events\" to log out"])
                elif platform.system() == 'Linux':
                    subprocess.call(["logout"])
                time.sleep(3)
            except Exception as e:
                speak("Unable to log off")
                print(e)

        elif 'email' in statement or 'send mail' in statement:
            speak("Who should I send the email to?")
            recipient = takeCommand()
            if recipient == "None":
                continue
            speak("What is the subject?")
            subject = takeCommand()
            if subject == "None":
                continue
            speak("What should I say in the email?")
            body = takeCommand()
            if body == "None":
                continue
            try:
                email = os.getenv('EMAIL')
                password = os.getenv('EMAIL_PASSWORD')

                if not email or not password:
                    speak(
                        "Email credentials not found. Please set EMAIL and EMAIL_PASSWORD in .env file")
                    continue

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.ehlo()
                server.starttls()
                server.login(email, password)

                message = MIMEMultipart()
                message['From'] = email
                message['To'] = recipient
                message['Subject'] = subject
                message.attach(MIMEText(body, 'plain'))

                server.send_message(message)
                server.quit()
                speak("Email sent successfully.")
            except smtplib.SMTPAuthenticationError:
                speak("Authentication failed. Check your email and password.")
            except smtplib.SMTPException as e:
                speak("SMTP error occurred. Please try again.")
                print(e)
            except Exception as e:
                speak(
                    "Sorry, I was unable to send the email. Please check your credentials.")
                print(e)

        # ── Feature 3: Universal App & Document Launcher ──────────────────────
        # No hardcoded list — dynamically finds ANY app or file on this Mac.

        elif any(statement.startswith(p) for p in ['open ', 'launch ', 'start ']):
            # Extract the target name
            query = (statement
                     .replace('open ', '', 1)
                     .replace('launch ', '', 1)
                     .replace('start ', '', 1)
                     .strip())
            if not query:
                speak("What would you like me to open?")
            else:
                result = open_app(query)
                # If app not found, try as a document
                if "couldn't find" in result.lower():
                    doc_result = open_document(query)
                    result = doc_result if "couldn't find" not in doc_result.lower() else result
                speak(result)

        elif 'open document' in statement or 'open file' in statement:
            query = (statement
                     .replace('open document', '')
                     .replace('open file', '')
                     .strip())
            speak(open_document(query))

        elif statement.startswith('close ') and 'close window' not in statement:
            app_name = statement.replace('close', '').strip()
            speak(close_app(app_name))

        elif statement.startswith('switch to ') or statement.startswith('go to '):
            app_name = statement.replace('switch to', '').replace('go to', '').strip()
            speak(switch_app(app_name))

        elif 'rescan apps' in statement or 'refresh apps' in statement or 'scan apps' in statement:
            speak("Rescanning your system for apps and documents, one moment.")
            speak(refresh_index())

        # ── Feature 3: System Controls ────────────────────────────────────────
        elif 'volume' in statement:
            if 'mute' in statement:
                speak(mute())
            elif 'unmute' in statement or 'un mute' in statement:
                speak(unmute())
            elif 'up' in statement or 'increase' in statement or 'louder' in statement:
                speak(volume_up())
            elif 'down' in statement or 'decrease' in statement or 'lower' in statement:
                speak(volume_down())
            else:
                # Try to extract a number: "set volume to 50"
                import re
                nums = re.findall(r'\d+', statement)
                if nums:
                    speak(set_volume(int(nums[0])))
                else:
                    speak("What volume level would you like? Say a number from 0 to 100.")

        elif 'brightness' in statement:
            import re
            nums = re.findall(r'\d+', statement)
            if nums:
                speak(set_brightness(int(nums[0])))
            else:
                speak("What brightness level? Say a number from 0 to 100.")

        elif 'sleep' in statement and ('mac' in statement or 'computer' in statement or 'system' in statement):
            speak(sleep_mac())

        elif 'lock' in statement and ('screen' in statement or 'mac' in statement):
            speak(lock_mac())

        elif 'shutdown' in statement or ('shut down' in statement and 'mac' in statement):
            speak("Ok, your Mac will shut down. Make sure you save your work.")
            speak(shutdown_mac())

        elif 'restart' in statement and ('mac' in statement or 'system' in statement or 'computer' in statement):
            speak("Restarting your Mac. Please save your work.")
            speak(restart_mac())

        # ── Feature 4: Media Controls ─────────────────────────────────────────
        elif any(w in statement for w in ['play music', 'play song', 'resume music', 'resume playback']):
            speak(play())

        elif any(w in statement for w in ['pause music', 'pause song', 'pause playback']):
            speak(pause())

        elif any(w in statement for w in ['play pause', 'toggle music', 'toggle playback']):
            speak(play_pause())

        elif any(w in statement for w in ['next song', 'next track', 'skip song', 'skip track']):
            speak(next_track())

        elif any(w in statement for w in ['previous song', 'previous track', 'last song', 'go back']):
            speak(prev_track())

        elif any(w in statement for w in ['what song', 'what\'s playing', 'current track', 'now playing']):
            speak(get_current_track())

        # ── Feature 5: Window Management ──────────────────────────────────────
        elif any(w in statement for w in ['minimize window', 'minimise window', 'minimize this']):
            speak(minimize_window())

        elif any(w in statement for w in ['maximize window', 'maximise window', 'maximize this', 'full screen']):
            speak(maximize_window())

        elif 'close window' in statement:
            speak(close_window())

        elif 'move window left' in statement or 'snap left' in statement:
            speak(move_left())

        elif 'move window right' in statement or 'snap right' in statement:
            speak(move_right())

        # ── Feature 6: File System ────────────────────────────────────────────
        elif any(w in statement for w in ['open downloads', 'open documents', 'open desktop', 'open pictures', 'open movies']):
            folder = statement.replace('open', '').strip()
            speak(_file_manager.open_folder(folder))

        elif 'recent files' in statement or 'show recent' in statement:
            speak(_file_manager.show_recent_files())

        elif statement.startswith('create folder') or statement.startswith('make folder'):
            parts = statement.replace('create folder', '').replace('make folder', '').strip()
            # Parse: "called X on desktop" or just "X"
            location = 'desktop'
            name = parts
            if ' on ' in parts:
                name, location = parts.rsplit(' on ', 1)
            speak(_file_manager.create_folder(name.strip(), location.strip()))

        elif statement.startswith('create file') or statement.startswith('make file'):
            parts = statement.replace('create file', '').replace('make file', '').strip()
            location = 'desktop'
            name = parts
            if ' on ' in parts:
                name, location = parts.rsplit(' on ', 1)
            speak(_file_manager.create_file(name.strip(), location.strip()))

        elif statement.startswith('find file') or statement.startswith('search for file'):
            query = statement.replace('find file', '').replace('search for file', '').strip()
            speak(_file_manager.search_file(query))

        elif statement.startswith('delete file') or statement.startswith('remove file'):
            path_hint = statement.replace('delete file', '').replace('remove file', '').strip()
            result = _file_manager.search_file(path_hint)
            speak(result)
            speak("Which file should I delete? Please give the full path.")
            path_response = takeCommand()
            if path_response != "None":
                speak(_file_manager.delete_file(path_response.strip()))

        # ── Feature 1: Web search (no browser) ───────────────────────────────
        elif any(p in statement for p in ['look up', 'look it up', 'what is', 'who is', 'tell me about', 'explain']):
            # Route to LLM for direct answers — no browser
            reply = ask_llm(statement, _memory)
            speak(reply)

        elif 'internet search' in statement or 'web search' in statement or 'search online' in statement:
            query = (
                statement
                .replace('internet search', '')
                .replace('web search', '')
                .replace('search online', '')
                .strip()
            )
            if query:
                result = web_search(query)
                speak(result)
            else:
                speak("What would you like me to search for online?")

        elif 'clear memory' in statement or 'forget everything' in statement:
            _memory.clear()
            speak("Conversation memory cleared. Starting fresh.")

        # ── Feature 1: LLM catch-all (LAST — preserves all existing routing) ─
        else:
            reply = ask_llm(statement, _memory)
            speak(reply)
