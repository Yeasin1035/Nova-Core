from flask import Flask, request, jsonify, send_file
from gtts import gTTS
from io import BytesIO
import openai
import os
import tempfile
import speech_recognition as sr

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Voice generation ===
def generate_voice(text, lang='en'):
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# === Speech to text ===
def speech_to_text(audio_file):
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio_data = r.record(source)
        try:
            text = r.recognize_google(audio_data)
            return text
        except Exception as e:
            return f"[Error in speech recognition: {e}]"

# === AI text response ===
def ai_reply(user_text):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Nova, a smart, calm, and friendly AI assistant."},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e}"

# === Main voice route ===
@app.route("/nova", methods=["POST"])
def nova_voice():
    if 'file' in request.files:
        # Handle audio input
        file = request.files['file']
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            file.save(temp_audio.name)
            text = speech_to_text(temp_audio.name)
        print(f"🎤 Recognized speech: {text}")

        reply_text = ai_reply(text)
        print(f"🤖 Nova reply: {reply_text}")

        voice_fp = generate_voice(reply_text)
        return send_file(voice_fp, mimetype="audio/mp3")

    else:
        # Handle plain text input
        data = request.get_json(force=True)
        user_text = data.get("text", "")
        if not user_text:
            return jsonify({"error": "No text provided"}), 400

        reply_text = ai_reply(user_text)
        voice_fp = generate_voice(reply_text)
        return send_file(voice_fp, mimetype="audio/mp3")

@app.route("/", methods=["GET"])
def home():
    return "✅ Nova-Core Server with Voice Input is Running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
