import sys
sys.path.insert(0, '.')

import voice_assistant

# mock takeCommand to run exactly once and then raise KeyboardInterrupt
first_call = True
def mock_takeCommand():
    global first_call
    if first_call:
        first_call = False
        print("user said: what's up Barvis")
        return "what's up barvis"
    sys.exit(0)

voice_assistant.takeCommand = mock_takeCommand
voice_assistant._wake_listener = type('MockListener', (), {'start': lambda: None, 'pause': lambda: None, 'resume': lambda: None})()

try:
    with open('voice_assistant.py', 'r') as f:
        code = f.read()
    # Strip the if __name__ block and just run the while loop
    code = code.replace("if __name__ == '__main__':", "if True:")
    exec(code, voice_assistant.__dict__)
except SystemExit:
    pass
except Exception as e:
    print("Error:", e)
