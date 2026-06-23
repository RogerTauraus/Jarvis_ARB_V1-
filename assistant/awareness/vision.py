"""
vision.py — Visual intelligence for JARVIS.

Analyze what the camera sees (webcam), or analyze any image file.
Uses OpenCV (already installed) for webcam capture.
Vision AI: Groq llama-4-scout (primary) → Gemini 2.0 Flash (fallback)

Commands:
  "what do you see" / "look at this" → webcam snapshot → AI description
  "analyze this image" → current clipboard image or screenshot
  "what am I holding" → webcam + AI
"""

import cv2
import base64
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


# ── Webcam capture ────────────────────────────────────────────────────────────

def capture_webcam(camera_index: int = 0) -> str:
    """
    Capture a frame from the webcam and save to a temp file.
    Returns the file path, or "" on failure.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.warning("Webcam not accessible.")
        return ""

    # Allow camera to warm up (2 frames)
    for _ in range(2):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return ""

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    path = tmp.name
    tmp.close()

    cv2.imwrite(path, frame)
    return path if os.path.exists(path) and os.path.getsize(path) > 1000 else ""


# ── Image analysis via Vision AI ─────────────────────────────────────────────

def analyze_image(image_path: str, question: str = "") -> str:
    """
    Send an image to Vision AI and return a description.
    Works with webcam frames, screenshots, or any image file.
    """
    from dotenv import load_dotenv
    import os as _os
    _env = _os.path.join(_os.path.dirname(__file__), '..', '..', 'API', 'agent.env')
    load_dotenv(_env)

    if not os.path.exists(image_path):
        return "I couldn't find the image to analyze."

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"Couldn't read the image: {e}"

    # Determine mime type
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    q = question or (
        "Describe what you see in this image in detail. "
        "Mention objects, people, text, colors, and any notable features. "
        "Be conversational and speak as if you're describing it to someone."
    )

    # Primary: Groq Vision
    try:
        from groq import Groq
        key = _os.getenv("GROQ_API_KEY", "")
        if key:
            client = Groq(api_key=key)
            resp = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:{mime};base64,{img_b64}"
                    }},
                    {"type": "text", "text": q}
                ]}],
                max_tokens=400,
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.debug(f"Groq Vision error: {e}")

    # Fallback: Gemini
    try:
        from google import genai
        import PIL.Image
        key = _os.getenv("GEMINI_API_KEY", "")
        if key:
            client = genai.Client(api_key=key)
            img = PIL.Image.open(image_path)
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[img, q]
            )
            return resp.text.strip()
    except Exception as e:
        logger.debug(f"Gemini Vision error: {e}")

    return "I couldn't analyze the image right now — Vision API unavailable."


# ── Main public functions ────────────────────────────────────────────────────

def describe_what_i_see(question: str = "") -> str:
    """
    Capture webcam and describe what JARVIS sees.
    Main entry point for "what do you see" / "look at this" commands.
    """
    path = capture_webcam()
    if not path:
        # No webcam? Fall back to screen description
        from assistant.awareness.screen_reader import describe_screen
        return describe_screen(question or "What's on the screen?")

    try:
        q = question or "What do you see? Describe this clearly and conversationally."
        result = analyze_image(path, q)
        return result or "I looked but couldn't quite make it out."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def analyze_whats_in_front(question: str = "") -> str:
    """What the user is pointing at or holding."""
    return describe_what_i_see(
        question or "What object or thing is in front of the camera? What is the person holding or showing?"
    )


def read_text_in_image(question: str = "") -> str:
    """Read and speak any text visible in the webcam frame."""
    path = capture_webcam()
    if not path:
        from assistant.awareness.screen_reader import read_screen_text
        return read_screen_text()

    try:
        q = "Read all the text you can see in this image. Speak it clearly as if reading it aloud."
        result = analyze_image(path, q)
        return result or "I couldn't read any text in the image."
    finally:
        if os.path.exists(path):
            os.unlink(path)


def identify_object() -> str:
    """Identify what object is in front of the camera."""
    path = capture_webcam()
    if not path:
        return "Camera not available."
    try:
        q = (
            "What is the main object in this image? "
            "Name it and briefly describe what it's used for. "
            "Be direct: start with 'That looks like a...' or 'That's a...'"
        )
        return analyze_image(path, q) or "I couldn't identify that."
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'API', 'agent.env'))

    print("=== Webcam Test ===")
    path = capture_webcam()
    if path:
        print(f"Captured: {path} ({os.path.getsize(path)} bytes)")
        print("Analyzing...")
        print(analyze_image(path))
        os.unlink(path)
    else:
        print("No webcam available — testing with screenshot")
        from assistant.awareness.screen_reader import capture_screen
        path = capture_screen()
        if path:
            print(analyze_image(path, "What app is open?"))
            os.unlink(path)
