import os
from flask import Flask, request, jsonify, send_file
from uuid import uuid4
import yt_dlp
from gtts import gTTS
import openai

UPLOAD_DIR = "uploads"
SONG_DIR = "songs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SONG_DIR, exist_ok=True)

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------------------------
# Helper: Save raw WAV bytes
# ----------------------------
def save_raw_wav(raw_bytes):
    file_id = str(uuid4())
    wav_path = os.path.join(UPLOAD_DIR, f"{file_id}.wav")
    with open(wav_path, "wb") as f:
        f.write(raw_bytes)
    return wav_path, file_id

# ----------------------------
# Helper: TTS generator
# ----------------------------
def synthesize_to_mp3(text, out_path, lang="en"):
    tts = gTTS(text=text, lang=lang)
    tts.save(out_path)
    return out_path

# ----------------------------
# Speech-to-text (using Whisper API)
# ----------------------------
def transcribe_audio(wav_path):
    try:
        with open(wav_path, "rb") as f:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        return response
    except Exception as e:
        return f"Transcription failed: {e}"

# ----------------------------
# AI Chat
# ----------------------------
def ai_reply(text):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", 
                 "content": "You are Nova, a smart, calm, friendly AI assistant."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"AI Error: {e}"

# ----------------------------
# MAIN ROUTE — /nova
# Handles raw WAV or multipart
# ----------------------------
@app.route("/nova", methods=["POST"])
def nova_route():
    # Priority: raw WAV body
    if request.data:
        raw_bytes = request.data
    # fallback: multipart file
    elif "file" in request.files:
        raw_bytes = request.files["file"].read()
    else:
        return jsonify({"error": "No audio received"}), 400

    wav_path, file_id = save_raw_wav(raw_bytes)

    # 1. Transcribe WAV
    user_text = transcribe_audio(wav_path)

    # 2. Get AI reply
    reply_text = ai_reply(user_text)

    # 3. Generate MP3
    mp3_path = os.path.join(UPLOAD_DIR, f"{file_id}.mp3")
    synthesize_to_mp3(reply_text, mp3_path)

    # 4. Return MP3 directly
    return send_file(mp3_path, mimetype="audio/mpeg")

# ----------------------------
# MUSIC SEARCH ROUTE — /music
# ----------------------------
@app.route("/music", methods=["POST"])
def music_route():
    data = request.get_json()
    query = data.get("query", "").strip()

    if query == "":
        return jsonify({"error": "Empty query"}), 400

    file_id = str(uuid4())
    out_path = os.path.join(SONG_DIR, f"{file_id}.mp3")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            title = info["entries"][0]["title"]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    file_url = request.host_url + f"songs/{file_id}.mp3"

    return jsonify({
        "title": title,
        "url": file_url
    })

# ----------------------------
# Serve song files
# ----------------------------
@app.route("/songs/<name>")
def serve_song(name):
    return send_file(os.path.join(SONG_DIR, name), mimetype="audio/mpeg")

# ----------------------------
# Root Check
# ----------------------------
@app.route("/")
def home():
    return "✅ Nova-Core v4 Server Running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
