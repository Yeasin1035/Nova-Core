from flask import Flask, request, jsonify
from gtts import gTTS
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Nova Core server is online!"

@app.route('/speak', methods=['POST'])
def speak():
    data = request.get_json()
    text = data.get("text", "")
    language = data.get("lang", "en")
    tts = gTTS(text=text, lang=language)
    tts.save("reply.mp3")
    return jsonify({"status": "success", "file": "reply.mp3"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # <-- auto-detect Render port
    app.run(host='0.0.0.0', port=port)
