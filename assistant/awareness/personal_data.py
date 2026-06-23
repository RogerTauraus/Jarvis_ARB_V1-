"""
personal_data.py — Read Notes, Mail, Messages from macOS via AppleScript.

No third-party services. Data stays on device.
Requires macOS Accessibility + Full Disk Access for Terminal (for Messages DB).
"""

import subprocess
import sqlite3
import os
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")


# ── AppleScript runner ────────────────────────────────────────────────────────

def _run_applescript(script: str, timeout: int = 10) -> str:
    """Run an AppleScript and return its output."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        logger.debug(f"AppleScript error: {e}")
        return ""


# ── Notes ─────────────────────────────────────────────────────────────────────

def search_notes(query: str) -> str:
    """
    Search Apple Notes for content matching the query.
    Returns a spoken summary of matching notes.
    """
    script = '''
    tell application "Notes"
        set results to ""
        set allNotes to notes
        repeat with n in allNotes
            set t to name of n
            set b to ""
            try
                set b to plaintext of n
            end try
            if t contains "QUERY" or b contains "QUERY" then
                set results to results & t & ": " & (text 1 thru (min of 150 (count of b)) of b) & " | "
            end if
        end repeat
        if results is "" then
            return "NO_MATCH"
        end if
        return results
    end tell
    '''.replace("QUERY", query)

    raw = _run_applescript(script, timeout=15)

    if not raw or raw == "NO_MATCH":
        return f"I couldn't find any notes about {query}."

    entries = [e.strip() for e in raw.split("|") if e.strip()]
    if not entries:
        return f"Nothing in your notes about {query}."

    if len(entries) == 1:
        return f"Found one note — {entries[0]}"

    titles = [e.split(":")[0] for e in entries[:5]]
    return f"Found {len(entries)} notes about {query}. Top ones: {', '.join(titles)}. Want me to read any of them?"


def read_latest_notes(count: int = 3) -> str:
    """Read the N most recent notes."""
    script = f'''
    tell application "Notes"
        set results to ""
        set allNotes to notes
        set cnt to count of allNotes
        if cnt is 0 then return "No notes found"
        repeat with i from 1 to {count}
            if i > cnt then exit repeat
            set n to item i of allNotes
            set t to name of n
            set b to ""
            try
                set b to plaintext of n
            end try
            set bLen to count of b
            if bLen > 200 then
                set preview to (text 1 thru 200 of b)
            else
                set preview to b
            end if
            set results to results & t & ": " & preview & " || "
        end repeat
        return results
    end tell
    '''
    raw = _run_applescript(script, timeout=15)
    if not raw or raw == "No notes found":
        return "Your notes appear to be empty."

    entries = [e.strip() for e in raw.split("||") if e.strip()]
    if not entries:
        return "Couldn't read your notes right now."

    parts = [f"Note {i+1}: {e}" for i, e in enumerate(entries)]
    return "Here are your recent notes. " + " Next, ".join(parts)


# ── Mail ──────────────────────────────────────────────────────────────────────

def get_recent_emails(count: int = 5, sender_filter: str = "") -> str:
    """
    Read recent emails from Mail app.
    Optionally filter by sender name/address.
    """
    filter_line = f'if (sender of m) contains "{sender_filter}" then' if sender_filter else ""
    end_filter  = "end if" if sender_filter else ""

    script = f'''
    tell application "Mail"
        set output to ""
        set cnt to 0
        set msgs to messages of inbox
        repeat with m in msgs
            if cnt >= {count} then exit repeat
            {filter_line}
            set s to subject of m
            set snd to sender of m
            set dt to date received of m
            set output to output & s & " | from: " & snd & " | " & (dt as string) & " || "
            set cnt to cnt + 1
            {end_filter}
        end repeat
        if output is "" then return "NO_MAIL"
        return output
    end tell
    '''
    raw = _run_applescript(script, timeout=15)

    if not raw or raw == "NO_MAIL":
        if sender_filter:
            return f"No recent emails from {sender_filter}."
        return "Your inbox looks empty or Mail isn't open."

    entries = [e.strip() for e in raw.split("||") if e.strip()]
    if not entries:
        return "Couldn't read emails right now."

    if sender_filter:
        spoken = f"Found {len(entries)} emails from {sender_filter}. "
    else:
        spoken = f"You have {len(entries)} recent emails. "

    for i, entry in enumerate(entries[:3]):
        parts = entry.split("|")
        subject = parts[0].strip() if parts else "No subject"
        sender  = parts[1].replace("from:", "").strip() if len(parts) > 1 else "Unknown"
        spoken += f"Number {i+1}: {subject}, from {sender}. "

    if len(entries) > 3:
        spoken += f"And {len(entries)-3} more."
    return spoken


def search_emails(query: str, count: int = 5) -> str:
    """Search email subjects and senders for a query."""
    script = f'''
    tell application "Mail"
        set output to ""
        set cnt to 0
        set msgs to messages of inbox
        repeat with m in msgs
            if cnt >= {count} then exit repeat
            set s to subject of m
            set snd to sender of m
            if s contains "{query}" or snd contains "{query}" then
                set output to output & s & " | from: " & snd & " || "
                set cnt to cnt + 1
            end if
        end repeat
        if output is "" then return "NO_MATCH"
        return output
    end tell
    '''
    raw = _run_applescript(script, timeout=15)
    if not raw or raw == "NO_MATCH":
        return f"No emails found matching {query}."

    entries = [e.strip() for e in raw.split("||") if e.strip()]
    spoken = f"Found {len(entries)} emails about {query}. "
    for i, e in enumerate(entries[:3]):
        parts = e.split("|")
        subject = parts[0].strip()
        spoken += f"{i+1}: {subject}. "
    return spoken


# ── Messages ──────────────────────────────────────────────────────────────────

def get_messages_from(contact: str, count: int = 5) -> str:
    """
    Read recent iMessages from a contact.
    Tries AppleScript first, then SQLite DB (needs Full Disk Access).
    """
    # Method 1: AppleScript (works for open conversations)
    result = _messages_via_applescript(contact, count)
    if result:
        return result

    # Method 2: SQLite direct read (needs Full Disk Access)
    result = _messages_via_sqlite(contact, count)
    if result:
        return result

    return (
        f"I couldn't read messages from {contact}. "
        "Make sure Messages is open, or grant Full Disk Access to Terminal in System Settings."
    )


def _messages_via_applescript(contact: str, count: int) -> str:
    script = f'''
    tell application "Messages"
        set output to ""
        set targetChats to chats
        repeat with c in targetChats
            set chatName to name of c
            if chatName contains "{contact}" then
                set msgs to messages of c
                set start to (count of msgs) - {count} + 1
                if start < 1 then set start to 1
                repeat with i from start to (count of msgs)
                    set m to item i of msgs
                    set txt to text of m
                    set output to output & txt & " | "
                end repeat
                return output
            end if
        end repeat
        return "NO_MATCH"
    end tell
    '''
    raw = _run_applescript(script, timeout=12)
    if not raw or raw == "NO_MATCH":
        return ""

    messages = [m.strip() for m in raw.split("|") if m.strip()]
    if not messages:
        return ""

    spoken = f"Recent messages from {contact}: "
    for i, msg in enumerate(messages[-3:], 1):
        spoken += f"Message {i}: {msg[:120]}. "
    return spoken


def _messages_via_sqlite(contact: str, count: int) -> str:
    """Read messages from the local SQLite database (requires Full Disk Access)."""
    if not os.path.exists(_MESSAGES_DB):
        return ""
    try:
        conn = sqlite3.connect(_MESSAGES_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.text
            FROM message m
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE h.id LIKE ? AND m.text IS NOT NULL
            ORDER BY m.date DESC
            LIMIT ?
        """, (f"%{contact}%", count))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return ""

        spoken = f"Recent messages from {contact}: "
        for i, (text,) in enumerate(reversed(rows), 1):
            spoken += f"{i}: {text[:100]}. "
        return spoken
    except Exception as e:
        logger.debug(f"SQLite messages error: {e}")
        return ""


# ── Unified search ────────────────────────────────────────────────────────────

def search_all(query: str) -> str:
    """
    Search across Notes and Mail for a query.
    Returns a combined spoken response.
    """
    results = []

    note_result = search_notes(query)
    if "couldn't find" not in note_result and "Nothing in" not in note_result:
        results.append(f"In Notes: {note_result}")

    mail_result = search_emails(query, count=3)
    if "No emails found" not in mail_result:
        results.append(f"In Mail: {mail_result}")

    if not results:
        return f"I couldn't find anything about {query} in your notes or email."

    return " Also, ".join(results)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Notes ===")
    print(read_latest_notes(3))
    print()
    print("=== Emails ===")
    print(get_recent_emails(3))
    print()
    print("=== Search Notes for 'python' ===")
    print(search_notes("python"))
