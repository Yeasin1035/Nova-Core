from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import os
import random
import time

app = Flask(__name__)

# Offline fallback messages
OFFLINE_RESPONSES = [
    "Sorry, I'm offline right now.",
    "Connection lost. Trying to reconnect.",
    "Nova Core is currently in offline mode."
]

@app.route('/')
def home():
    return "🧠 Nova Core is online and ready!"

@app.route('/api/text', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        user_text = data.get("text", "")

        if not user_text:
            return jsonify({"error": "No text provided"}), 400

        # Simulate AI logic
        reply_text = f"You said: {user_text}. Nova Core acknowledges."

        # Convert reply to speech (gTTS)
        tts = gTTS(text=reply_text, lang="en")
        filename = f"reply_{int(time.time())}.mp3"
        tts.save(filename)

        return jsonify({
            "status": "ok",
            "reply_text": reply_text,
            "audio_url": f"/audio/{filename}"
        })

    except Exception as e:
        offline_msg = random.choice(OFFLINE_RESPONSES)
        tts = gTTS(text=offline_msg, lang="en")
        filename = f"offline_{int(time.time())}.mp3"
        tts.save(filename)
        return jsonify({
            "status": "offline",
            "reply_text": offline_msg,
            "audio_url": f"/audio/{filename}"
        })

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_file(filename, mimetype="audio/mpeg")

if __name__ == '__main__':
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
