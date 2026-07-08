#!/bin/bash
# install_macos.sh — One-time macOS integration setup for BARVIS.
# Run once: bash install_macos.sh

set -e
BARVIS_DIR="/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_NAME="com.barvis.assistant.plist"
APP_SUPPORT="$HOME/Library/Application Support/BARVIS"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║       BARVIS macOS Integration Setup         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Create log and support directories ──────────────────────────────
echo "[1/5] Creating directories..."
mkdir -p "$BARVIS_DIR/logs"
mkdir -p "$APP_SUPPORT"
echo "      ✅ Logs → $BARVIS_DIR/logs"

# ── Step 2: Make scripts executable ────────────────────────────────────────
echo "[2/5] Setting file permissions..."
chmod +x "$BARVIS_DIR/launch_barvis.sh"
echo "      ✅ launch_barvis.sh is executable"

# ── Step 3: Install LaunchAgent (background service) ───────────────────────
echo "[3/5] Installing LaunchAgent..."
mkdir -p "$LAUNCH_AGENTS"

# Unload existing agent if present
if launchctl list | grep -q "com.barvis.assistant"; then
    launchctl unload "$LAUNCH_AGENTS/$PLIST_NAME" 2>/dev/null || true
fi

# Write the plist with RunAtLoad=false (user controls via menu bar)
cat > "$LAUNCH_AGENTS/$PLIST_NAME" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.barvis.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1/launch_barvis.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1</string>
    <key>StandardOutPath</key>
    <string>/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1/logs/barvis.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1/logs/barvis_error.log</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>SessionCreate</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>/Users/ashwinrogerbaxla</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
PLIST

launchctl load "$LAUNCH_AGENTS/$PLIST_NAME"
echo "      ✅ LaunchAgent registered with macOS"

# ── Step 4: Create a clickable .command launcher on Desktop ────────────────
echo "[4/5] Creating Desktop shortcut..."
SHORTCUT="$HOME/Desktop/BARVIS Menu Bar.command"
cat > "$SHORTCUT" << SCRIPT
#!/bin/bash
# Double-click this to launch the BARVIS menu bar app
cd "/Users/ashwinrogerbaxla/Desktop/Visual Code Studio/Barvis_v1"
exec "$PYTHON" menubar_app.py
SCRIPT
chmod +x "$SHORTCUT"
echo "      ✅ Shortcut → ~/Desktop/BARVIS Menu Bar.command"

# ── Step 5: Open permissions for user to grant ─────────────────────────────
echo "[5/5] Opening Privacy & Security settings..."
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  Grant these permissions in System Settings:    │"
echo "  │                                                  │"
echo "  │  🎙  Privacy & Security → Microphone            │"
echo "  │      → Enable Terminal (and/or Python)          │"
echo "  │                                                  │"
echo "  │  ♿  Privacy & Security → Accessibility         │"
echo "  │      → Enable Terminal (and/or Python)          │"
echo "  │                                                  │"
echo "  │  🤖  Privacy & Security → Automation           │"
echo "  │      → Enable Terminal → System Events, Finder  │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║            ✅ Setup Complete!                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  HOW TO USE:"
echo ""
echo "  1. Double-click 'BARVIS Menu Bar.command' on your Desktop"
echo "     → A ⬡ icon appears in your menu bar"
echo ""
echo "  2. Click ⬡ → 'Start BARVIS'"
echo "     → Say 'Hey Barvis' to activate"
echo ""
echo "  3. To start BARVIS automatically at login:"
echo "     → Click ⬡ → 'Enable Auto-Start at Login'"
echo ""
echo "  4. Add your OpenAI key for ChatGPT responses:"
echo "     → Edit: Barvis_v1/API/agent.env"
echo "     → Add:  OPENAI_API_KEY=sk-..."
echo ""
