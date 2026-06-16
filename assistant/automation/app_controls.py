"""
assistant/automation/app_controls.py — In-app control for native macOS apps.

Controls: Messages, Notes, Reminders, Maps, FaceTime, Calendar, Mail.
All via AppleScript — no extra dependencies.
"""

import subprocess
import urllib.parse
import logging
import re

logger = logging.getLogger(__name__)


def _run(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        if r.returncode != 0:
            logger.warning(f"AppleScript stderr: {r.stderr.strip()}")
        return r.stdout.strip()
    except Exception as e:
        logger.warning(f"app_controls AppleScript error: {e}")
        return ""


# ── iMessage / Messages ───────────────────────────────────────────────────────

def send_imessage(contact: str, message: str) -> str:
    """Send an iMessage to a contact by name or phone number."""
    safe_contact = contact.replace('"', "'")
    safe_msg     = message.replace('"', "'")
    script = f'''
    tell application "Messages"
        activate
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_contact}" of targetService
        send "{safe_msg}" to targetBuddy
    end tell
    '''
    result = _run(script)
    if "error" in result.lower():
        return (f"I couldn't find '{contact}' in Messages. "
                "Make sure the name matches your contact list exactly.")
    return f"Message sent to {contact}."


def open_messages_chat(contact: str) -> str:
    """Open a Messages conversation with a contact."""
    safe = contact.replace('"', "'")
    script = f'''
    tell application "Messages"
        activate
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe}" of targetService
        open conversation of targetBuddy
    end tell
    '''
    _run(script)
    return f"Opened chat with {contact}."


# ── Notes ────────────────────────────────────────────────────────────────────

def create_note(title: str, content: str = "") -> str:
    """Create a new note in the Notes app."""
    safe_title   = title.replace('"', "'")
    safe_content = content.replace('"', "'")
    body = f"{title}\\n\\n{content}" if content else title
    script = f'''
    tell application "Notes"
        activate
        tell account "iCloud"
            make new note with properties {{name:"{safe_title}", body:"{safe_content}"}}
        end tell
    end tell
    '''
    _run(script)
    return f"Note '{title}' created in Notes."


def append_to_latest_note(content: str) -> str:
    """Append text to the most recently modified note."""
    safe = content.replace('"', "'")
    script = f'''
    tell application "Notes"
        activate
        set n to note 1 of default account
        set body of n to (body of n) & "\\n{safe}"
    end tell
    '''
    _run(script)
    return f"Added to your latest note."


# ── Reminders ─────────────────────────────────────────────────────────────────

def add_reminder(task: str, due_date: str = None) -> str:
    """Add a reminder to the default Reminders list."""
    safe_task = task.replace('"', "'")
    if due_date:
        safe_date = due_date.replace('"', "'")
        script = f'''
        tell application "Reminders"
            activate
            set r to make new reminder with properties {{name:"{safe_task}"}}
            set due date of r to date "{safe_date}"
        end tell
        '''
    else:
        script = f'''
        tell application "Reminders"
            activate
            make new reminder with properties {{name:"{safe_task}"}}
        end tell
        '''
    _run(script)
    return f"Reminder added: '{task}'."


def list_reminders() -> str:
    """Read out incomplete reminders."""
    script = '''
    tell application "Reminders"
        set incompleteList to {}
        repeat with r in (reminders whose completed is false)
            set end of incompleteList to name of r
        end repeat
        return incompleteList
    end tell
    '''
    result = _run(script)
    if not result:
        return "You have no pending reminders."
    items = [i.strip() for i in result.split(",") if i.strip()]
    if not items:
        return "You have no pending reminders."
    if len(items) == 1:
        return f"You have one reminder: {items[0]}."
    joined = ", ".join(items[:-1]) + f", and {items[-1]}"
    return f"You have {len(items)} reminders: {joined}."


# ── Maps ──────────────────────────────────────────────────────────────────────

def open_maps(location: str) -> str:
    """Show a location in Apple Maps."""
    encoded = urllib.parse.quote(location)
    subprocess.Popen(["open", f"maps://?q={encoded}"])
    return f"Showing {location} in Maps."


def get_directions(destination: str, mode: str = "d") -> str:
    """
    Get directions to a destination.
    mode: 'd' = driving, 'w' = walking, 'r' = transit
    """
    encoded = urllib.parse.quote(destination)
    url = f"maps://?daddr={encoded}&dirflg={mode}"
    subprocess.Popen(["open", url])
    mode_str = {"d": "driving", "w": "walking", "r": "transit"}.get(mode, "driving")
    return f"Getting {mode_str} directions to {destination}."


# ── FaceTime ──────────────────────────────────────────────────────────────────

def facetime_call(contact: str) -> str:
    """Start a FaceTime video call."""
    # Try to find the contact's number/email via Contacts
    safe = contact.replace('"', "'")
    script = f'''
    tell application "Contacts"
        set p to first person whose name contains "{safe}"
        set v to value of first phone of p
        return v
    end tell
    '''
    info = _run(script)
    target = info if info else contact
    subprocess.Popen(["open", f"facetime:{urllib.parse.quote(target)}"])
    return f"Starting FaceTime call with {contact}."


def facetime_audio_call(contact: str) -> str:
    """Start a FaceTime audio call."""
    safe = contact.replace('"', "'")
    script = f'''
    tell application "Contacts"
        set p to first person whose name contains "{safe}"
        set v to value of first phone of p
        return v
    end tell
    '''
    info = _run(script)
    target = info if info else contact
    subprocess.Popen(["open", f"facetime-audio:{urllib.parse.quote(target)}"])
    return f"Starting audio call with {contact}."


# ── Mail ──────────────────────────────────────────────────────────────────────

def compose_mail(to: str, subject: str = "", body: str = "") -> str:
    """Open a new Mail compose window."""
    safe_to      = to.replace('"', "'")
    safe_subject = subject.replace('"', "'")
    safe_body    = body.replace('"', "'")
    script = f'''
    tell application "Mail"
        activate
        set newMsg to make new outgoing message with properties {{
            subject:"{safe_subject}",
            content:"{safe_body}",
            visible:true
        }}
        tell newMsg
            make new to recipient with properties {{address:"{safe_to}"}}
        end tell
    end tell
    '''
    _run(script)
    return f"Opened a new email to {to}."


# ── Calendar ─────────────────────────────────────────────────────────────────

def add_calendar_event(title: str, start: str, end: str = None) -> str:
    """Add an event to the default calendar."""
    safe_title = title.replace('"', "'")
    safe_start = start.replace('"', "'")
    if end:
        safe_end = end.replace('"', "'")
        script = f'''
        tell application "Calendar"
            activate
            tell calendar 1
                make new event with properties {{
                    summary:"{safe_title}",
                    start date:date "{safe_start}",
                    end date:date "{safe_end}"
                }}
            end tell
        end tell
        '''
    else:
        script = f'''
        tell application "Calendar"
            activate
            tell calendar 1
                make new event with properties {{
                    summary:"{safe_title}",
                    start date:date "{safe_start}"
                }}
            end tell
        end tell
        '''
    _run(script)
    return f"Event '{title}' added to your calendar."
