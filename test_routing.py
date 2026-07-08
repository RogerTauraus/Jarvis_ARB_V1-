import sys
sys.path.insert(0, '.')
from voice_assistant import route_command, _memory

def mock_speak(text):
    print("MOCK SPEAK:", text)

# Override speak to avoid actual TTS hanging
import voice_assistant
voice_assistant.speak = mock_speak

print("Routing command...")
route_command("what's up barvis")
print("Done routing.")
