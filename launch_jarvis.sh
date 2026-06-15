#!/bin/bash
# launch_jarvis.sh — Wrapper script that launches JARVIS voice assistant.
# Used by LaunchAgent and the menu bar app.

PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
JARVIS_DIR="/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Jarvis_v1"
LOG_DIR="$JARVIS_DIR/logs"

mkdir -p "$LOG_DIR"

cd "$JARVIS_DIR"
exec "$PYTHON" voice_assistant.py \
    >> "$LOG_DIR/jarvis.log" \
    2>> "$LOG_DIR/jarvis_error.log"
