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
from assistant.automation.browser import (
    youtube_play, youtube_toggle_pause, youtube_next, youtube_fullscreen,
    youtube_mute, youtube_volume, browser_search, browser_go_to,
    browser_go_back, browser_go_forward, browser_refresh, browser_scroll,
    browser_scroll_top, browser_scroll_bottom, browser_new_tab, browser_close_tab,
    browser_get_page_title, click_link, click_search_result, click_button,
    type_in_field, press_enter_on_page, get_page_links,
)
from assistant.automation.app_controls import (
    send_imessage, open_messages_chat,
    create_note, append_to_latest_note,
    add_reminder, list_reminders,
    open_maps, get_directions,
    facetime_call, facetime_audio_call,
    compose_mail, add_calendar_event,
)
from assistant.automation.window_control import (
    handle_in_window_command, get_window_context, extract_ordinal,
    get_frontmost_app, is_browser_active,
)
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

        # ── Contextual in-window commands (highest priority after sleep) ──────
        # Handles: "open first link", "click second result", "type X",
        # "click Sign In", "press enter", "what links are on this page", etc.
        # Routes to the correct handler based on whatever window is active.
        elif any(p in statement for p in [
            "open the first", "open the second", "open the third", "open the fourth", "open the fifth",
            "click the first", "click the second", "click the third",
            "open first link", "open second link", "open first result", "open second result",
            "click first", "click second", "click third",
            "select the first", "select the second",
            "go to the first", "go to the second",
            "open this link", "click this link",
            "list links", "what links", "show links",
            "page title", "what page", "current page",
            "press enter", "hit enter", "submit the form",
        ]) or (
            statement.startswith("type ") and is_browser_active()
        ) or (
            statement.startswith("click ") and "link" not in statement
            and "app" not in statement and is_browser_active()
        ) or (
            statement.startswith("write ") and is_browser_active()
        ):
            ctx_response = handle_in_window_command(statement)
            if ctx_response:
                speak(ctx_response)
            else:
                speak("I'm not sure what to do in this window. Try saying 'open first link' or 'click sign in'.")

        # ── YouTube smart commands (search & play, pause, next, fullscreen) ──
        elif any(p in statement for p in ['play', 'watch', 'search']) and 'youtube' in statement:
            # "play X on youtube" / "watch X youtube" / "search youtube for X"
            query = (
                statement
                .replace('play', '').replace('watch', '').replace('search', '')
                .replace('for', '').replace('on youtube', '').replace('youtube', '')
                .strip()
            )
            if query:
                speak(f"Searching YouTube for {query}, one moment.")
                speak(youtube_play(query))
            else:
                browser_go_to("https://www.youtube.com")
                speak("YouTube is open.")

        elif 'open youtube' in statement:
            browser_go_to("https://www.youtube.com")
            speak("YouTube is open.")

        elif 'pause video' in statement or 'pause youtube' in statement or 'play video' in statement:
            speak(youtube_toggle_pause())

        elif 'next video' in statement or 'skip video' in statement or 'skip youtube' in statement:
            speak(youtube_next())

        elif 'youtube fullscreen' in statement or 'fullscreen youtube' in statement:
            speak(youtube_fullscreen())

        elif 'mute youtube' in statement or 'unmute youtube' in statement:
            speak(youtube_mute())

        # ── Google & web search ──────────────────────────────────────────────
        elif 'open google' in statement:
            browser_go_to("https://www.google.com")
            speak("Google is open.")

        elif any(p in statement for p in ['search google', 'google search', 'search the web', 'search online']) and 'youtube' not in statement:
            query = (
                statement
                .replace('search google for', '').replace('search google', '')
                .replace('google search', '').replace('search the web for', '')
                .replace('search online for', '').replace('search online', '')
                .strip()
            )
            speak(browser_search(query, 'google'))

        elif 'open gmail' in statement:
            browser_go_to("https://gmail.com")
            speak("Gmail is open.")

        # ── General browser controls ─────────────────────────────────────────
        elif 'scroll down' in statement:
            speak(browser_scroll('down'))

        elif 'scroll up' in statement:
            speak(browser_scroll('up'))

        elif 'scroll to top' in statement or 'go to top' in statement:
            speak(browser_scroll_top())

        elif 'scroll to bottom' in statement or 'go to bottom' in statement:
            speak(browser_scroll_bottom())

        elif statement in ('go back', 'browser back', 'back') or 'go back in browser' in statement:
            speak(browser_go_back())

        elif 'go forward' in statement or 'browser forward' in statement:
            speak(browser_go_forward())

        elif 'refresh page' in statement or 'reload page' in statement or 'refresh browser' in statement:
            speak(browser_refresh())

        elif 'new tab' in statement:
            url_match = ''
            if 'open' in statement:
                url_match = statement.replace('open new tab', '').replace('new tab', '').replace('open', '').strip()
            speak(browser_new_tab(url_match))

        elif 'close tab' in statement:
            speak(browser_close_tab())

        elif 'go to' in statement and any(tld in statement for tld in ['.com', '.org', '.net', '.io', '.co', '.in']):
            url = statement.replace('go to', '').replace('open', '').strip()
            speak(browser_go_to(url))

        # ── iMessage ─────────────────────────────────────────────────────────
        elif any(p in statement for p in ['send a message to', 'text', 'send message to', 'message to']):
            # "send message to John saying hey" / "text John hey"
            import re
            m = re.search(r'(?:send (?:a )?message to|text|message to)\s+(.+?)\s+(?:saying|that)\s+(.+)', statement)
            if m:
                contact, msg = m.group(1).strip(), m.group(2).strip()
                speak(f"Sending message to {contact}.")
                speak(send_imessage(contact, msg))
            else:
                # Just open Messages
                contact = (
                    statement
                    .replace('send a message to', '').replace('send message to', '')
                    .replace('text', '').replace('message to', '').strip()
                )
                if contact:
                    speak(open_messages_chat(contact))
                else:
                    speak("Who would you like to message?")

        # ── Notes ────────────────────────────────────────────────────────────
        elif any(p in statement for p in ['create a note', 'make a note', 'add to notes', 'write a note']):
            content = (
                statement
                .replace('create a note', '').replace('make a note', '')
                .replace('add to notes', '').replace('write a note', '')
                .lstrip(' saying that').strip()
            )
            if not content:
                speak("What should I write in the note?")
                content = takeCommand()
            speak(create_note('JARVIS', content))

        elif 'add to my note' in statement or 'append to note' in statement:
            content = statement.replace('add to my note', '').replace('append to note', '').strip()
            speak(append_to_latest_note(content))

        # ── Reminders ────────────────────────────────────────────────────────
        elif any(p in statement for p in ['remind me', 'set a reminder', 'add a reminder', 'add reminder']):
            task = (
                statement
                .replace('remind me to', '').replace('remind me', '')
                .replace('set a reminder to', '').replace('set a reminder', '')
                .replace('add a reminder to', '').replace('add a reminder', '')
                .replace('add reminder', '').strip()
            )
            if not task:
                speak("What should I remind you about?")
                task = takeCommand()
            speak(add_reminder(task))

        elif any(p in statement for p in ['what are my reminders', "show my reminders", 'read my reminders', 'list reminders']):
            speak(list_reminders())

        # ── Maps & Directions ────────────────────────────────────────────────
        elif any(p in statement for p in ['directions to', 'navigate to', 'how do i get to', 'take me to']):
            dest = (
                statement
                .replace('directions to', '').replace('navigate to', '')
                .replace('how do i get to', '').replace('take me to', '').strip()
            )
            mode = 'w' if 'walk' in statement else 'd'
            speak(get_directions(dest, mode))

        elif 'show' in statement and 'maps' in statement or 'open maps' in statement:
            location = (
                statement
                .replace('show me', '').replace('on maps', '')
                .replace('open maps', '').replace('maps', '').strip()
            )
            if location:
                speak(open_maps(location))
            else:
                open_maps('')
                speak("Maps is open.")

        # ── FaceTime ─────────────────────────────────────────────────────────
        elif any(p in statement for p in ['facetime', 'video call', 'call via facetime']):
            contact = (
                statement
                .replace('facetime', '').replace('video call', '')
                .replace('call via facetime', '').replace('call', '').strip()
            )
            speak(facetime_call(contact) if contact else "Who would you like to FaceTime?")

        elif 'audio call' in statement or 'phone call' in statement:
            contact = (
                statement
                .replace('audio call', '').replace('phone call', '')
                .replace('call', '').strip()
            )
            speak(facetime_audio_call(contact) if contact else "Who would you like to call?")

        # ── Mail compose ─────────────────────────────────────────────────────
        elif 'compose email' in statement or 'write email' in statement or 'draft email' in statement:
            import re
            m = re.search(r'(?:to|for)\s+([\w\s]+?)(?:\s+about|\s+regarding|$)', statement)
            to_addr = m.group(1).strip() if m else ''
            speak(compose_mail(to_addr))

        # ── Calendar events ───────────────────────────────────────────────────
        elif any(p in statement for p in ['add event', 'add to calendar', 'schedule a', 'create event']):
            speak("What should I call the event?")
            title = takeCommand()
            speak("What date and time?")
            start_time = takeCommand()
            speak(add_calendar_event(title, start_time))

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
