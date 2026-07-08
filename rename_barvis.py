import os
import sys

# We will search and replace in all python, shell, and text files.
TARGET_EXTENSIONS = {'.py', '.sh', '.md', '.plist', '.example', ''}
# Ignore files that shouldn't be touched or are binaries
IGNORE_DIRS = {'.git', '__pycache__', 'env', 'venv'}

def replace_in_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception:
        return
        
    new_content = content
    # Replace carefully
    new_content = new_content.replace('BARVIS', 'BARVIS')
    new_content = new_content.replace('Barvis', 'Barvis')
    new_content = new_content.replace('barvis', 'barvis')
    
    # BUT wait! OpenWakeWord uses a model string "hey_jarvis". If we change that, it breaks the model loading.
    # So we revert the model string specifically.
    new_content = new_content.replace('hey_jarvis', 'hey_jarvis')
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for file in files:
        ext = os.path.splitext(file)[1]
        if ext in TARGET_EXTENSIONS or file in ['requirements.txt', 'setup.py']:
            replace_in_file(os.path.join(root, file))

# Rename files that contain barvis
for root, dirs, files in os.walk('.', topdown=False):
    for name in files:
        if 'barvis' in name.lower():
            old_path = os.path.join(root, name)
            # Case preserving replace
            new_name = name.replace('barvis', 'barvis').replace('Barvis', 'Barvis').replace('BARVIS', 'BARVIS')
            new_path = os.path.join(root, new_name)
            os.rename(old_path, new_path)
            print(f"Renamed {old_path} to {new_path}")
            
print("Rename complete.")
