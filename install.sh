#!/usr/bin/env bash
# BARVIS Installation Script for macOS

set -e

echo "================================================="
echo "   BARVIS Voice Assistant — macOS Installer"
echo "================================================="
echo ""

# 1. Check OS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: BARVIS is currently only supported on macOS."
    exit 1
fi

# 2. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.10 or higher."
    echo "You can download it from python.org or via Homebrew: brew install python3"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PY_VERSION found."

# 3. Create Virtual Environment
echo "📦 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Environment File Setup
if [ ! -f "API/agent.env" ]; then
    echo "📝 Creating API/agent.env from template..."
    mkdir -p API
    if [ -f "API/agent.env.example" ]; then
        cp API/agent.env.example API/agent.env
        echo "✅ API/agent.env created. Please fill in your API keys before running."
    else
        echo "⚠️  API/agent.env.example not found. Please create API/agent.env manually."
    fi
else
    echo "✅ API/agent.env already exists."
fi

# 6. Accessibility Permissions Note
echo ""
echo "================================================="
echo "🎉 Installation Complete!"
echo "================================================="
echo ""
echo "To run BARVIS:"
echo "  1. Activate the environment: source venv/bin/activate"
echo "  2. Edit API/agent.env to add your API keys (Groq, Spotify, Porcupine, etc.)"
echo "  3. Start BARVIS: python voice_assistant.py"
echo ""
echo "⚠️  IMPORTANT macOS SETTINGS:"
echo "  - You MUST grant Terminal (or iTerm, VS Code) Accessibility permissions:"
echo "    System Settings -> Privacy & Security -> Accessibility -> (Toggle your terminal app ON)"
echo "  - This is required for BARVIS to control apps and simulate keyboard events."
echo ""
