#!/bin/bash
# launch_barvis.sh — Wrapper script that launches BARVIS voice assistant.
# Used by LaunchAgent and the menu bar app.

PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
BARVIS_DIR="/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1"
LOG_DIR="$BARVIS_DIR/logs"

mkdir -p "$LOG_DIR"

cd "$BARVIS_DIR"
exec "$PYTHON" voice_assistant.py \
    >> "$LOG_DIR/barvis.log" \
    2>> "$LOG_DIR/barvis_error.log"
