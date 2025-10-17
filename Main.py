# main.py
import os
import time
import random
import tempfile
from flask import Flask, request, jsonify, send_file, abort
from gtts import gTTS

# Try to import openai if available
try:
    import openai
except Exception:
    openai = None

app = Flask(__name__)

# Simple offline fallback replies
OFFLINE_RESPONSES = [
    "Sorry, I'm offline right now.",
    "Connection lost. I will try again soon.",
    "Nova Core is currently running in offline mode."
]

# Utility: save TTS to mp3 and return filename
def tts_to_mp3(text, lang="en", slow=False):
    fn = f"reply_{int(time.time())}_{random.randint(1000,9999)}.mp3"
    # gTTS creates MP3 directly
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(fn)
    return fn

# Helper: transcribe using OpenAI Whisper (if API key present)
def transcribe_audio_with_openai(filepath):
    if not openai:
        raise RuntimeError("openai package not installed")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    openai.api_key = key
    with open(filepath, "rb") as f:
        # Use the OpenAI audio transcription endpoint
        # Note: model name may vary by availability. "whisper-1" is standard.
        resp = openai.Audio.transcribe(model="whisper-1", file=f)
    return resp["text"]

# Helper: ask ChatGPT-like model for reply (if API key present)
def chatgpt_reply(prompt, language_hint=None):
    if not openai:
        raise RuntimeError("openai package not installed")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    openai.api_key = key
    # Use chat completion (model may vary; change if unavailable)
    messages = [
        {"role": "system", "content": "You are Nova, a calm friendly multilingual assistant."},
        {"role": "user", "content": prompt}
    ]
    # Use a compact model to reduce latency & cost; change as needed
    resp = openai.ChatCompletion.create(
        model=os.environ.get("OPENAI_CHAT_MODEL","gpt-4o-mini"),
        messages=messages,
        max_tokens=500,
        temperature=0.6
    )
    return resp.choices[0].message["content"].strip()

@app.route("/")
def index():
    return "✅ Nova Core is online and ready!"

@app.route("/api/process", methods=["POST"])
def process():
    """
    Accepts:
    - multipart form-data with field "audio" (file)  OR
    - application/json with {"text": "..."}
    Optional form fields:
    - prefer_voice: "male"|"female" (currently informational)
    - lang: language code hint like "en" or "bn"
    """
    # Basic device auth (optional)
    device_key = os.environ.get("DEVICE_KEY")
    header_key = request.headers.get("x-device-key")
    if device_key and header_key != device_key:
        return jsonify({"error": "unauthorized"}), 401

    prefer_voice = request.form.get("prefer_voice") if request.form else None
    lang_hint = request.form.get("lang") or request.args.get("lang") or "en"

    # Case A: audio file uploaded
    if "audio" in request.files:
        audio_file = request.files["audio"]
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        audio_file.save(tmp_path)

        # If OpenAI key configured, transcribe, then use ChatGPT; else fallback
        if os.environ.get("OPENAI_API_KEY") and openai:
            try:
                transcript = transcribe_audio_with_openai(tmp_path)
            except Exception as ex:
                # transcription failed -> fallback response
                transcript = None
                print("Transcription error:", ex)
        else:
            transcript = None

        # If we got a transcript, get AI reply; else return offline fallback
        if transcript:
            try:
                reply_text = chatgpt_reply(transcript, language_hint=lang_hint)
            except Exception as ex:
                print("ChatGPT error:", ex)
                reply_text = random.choice(OFFLINE_RESPONSES)
        else:
            # No transcription available — ask client to send text instead or return fallback
            reply_text = random.choice(OFFLINE_RESPONSES)

        # Determine TTS language code to pass to gTTS (simple heuristic)
        tts_lang = "en" if lang_hint.startswith("en") else ("bn" if lang_hint.startswith("bn") else "en")

        # Create MP3 via gTTS
        mp3file = tts_to_mp3(reply_text, lang=tts_lang)
        # Clean temp audio upload
        try:
            os.remove(tmp_path)
        except:
            pass

        return jsonify({
            "status": "ok",
            "reply_text": reply_text,
            "audio_url": f"/audio/{mp3file}"
        })

    # Case B: JSON text input (useful for browser testing / fallback)
    if request.is_json:
        body = request.get_json()
        user_text = body.get("text", "").strip()
        if not user_text:
            return jsonify({"error": "no text provided"}), 400

        if os.environ.get("OPENAI_API_KEY") and openai:
            try:
                reply_text = chatgpt_reply(user_text, language_hint=lang_hint)
            except Exception as e:
                print("ChatGPT error:", e)
                reply_text = random.choice(OFFLINE_RESPONSES)
        else:
            # Lightweight offline logic: echo + simple canned behaviour
            # (This ensures you can demo even when no OpenAI key is set.)
            if user_text.lower().startswith("hello") or user_text.lower().startswith("hi"):
                reply_text = "Hello! I am Nova. How can I help you today?"
            elif "time" in user_text.lower():
                reply_text = f"The current server time is {time.strftime('%I:%M %p')}."
            else:
                reply_text = "Nova (offline): I received your message but advanced AI is not available."

        # TTS
        # choose language for voices: if user included "lang" in json, use it.
        tts_lang = body.get("lang", "en")
        mp3file = tts_to_mp3(reply_text, lang=tts_lang)

        return jsonify({
            "status": "ok",
            "reply_text": reply_text,
            "audio_url": f"/audio/{mp3file}"
        })

    # Nothing usable in request
    return jsonify({"error": "no audio file or text provided"}), 400

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    if not os.path.exists(filename):
        abort(404)
    return send_file(filename, mimetype="audio/mpeg")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
