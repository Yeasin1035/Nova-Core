import sys, types
if sys.version_info >= (3, 13):
    sys.modules['aifc'] = types.ModuleType('aifc')

from flask import Flask, request, jsonify, send_file
from gtts import gTTS
from io import BytesIO
import openai
import os
import random

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Helper ===
def generate_voice(text, lang='en'):
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# === Route for AI reply ===
@app.route("/nova", methods=["POST"])
def nova_reply():
    data = request.get_json()
    user_input = data.get("text", "")
    lang = data.get("lang", "en")

    if not user_input:
        return jsonify({"error": "No input text provided"}), 400

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Nova, a smart and friendly AI assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Sorry, something went wrong: {e}"

    fp = generate_voice(reply, lang=lang)
    return send_file(fp, mimetype="audio/mp3")

@app.route("/", methods=["GET"])
def home():
    return "✅ Nova-Core server is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    import os
import yt_dlp
from flask import Flask, request, jsonify, send_file
from uuid import uuid4

MUSIC_FOLDER = "songs"
os.makedirs(MUSIC_FOLDER, exist_ok=True)

@app.route("/music", methods=["POST"])
def music_search():
    data = request.get_json()
    query = data.get("query", "")

    if not query:
        return jsonify({"error": "No song name provided"}), 400

    # generate temporary file name
    file_id = str(uuid4())
    out_path = os.path.join(MUSIC_FOLDER, f"{file_id}.mp3")

    # yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    }

    # search and download
    search_query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
        title = info["entries"][0]["title"]

    # generate public HTTP URL for ESP32
    file_url = request.host_url + f"songs/{file_id}.mp3"

    return jsonify({
        "title": title,
        "url": file_url
    })

# route to serve saved MP3 files
@app.route("/songs/<filename>")
def serve_song(filename):
    return send_file(os.path.join(MUSIC_FOLDER, filename), mimetype="audio/mpeg")
