from flask import Flask, request, jsonify, send_file
from gtts import gTTS
from io import BytesIO
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Helper ===
def generate_voice(text, lang='en', gender='male'):
    tts = gTTS(text=text, lang=lang, slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# === Main Nova AI route ===
@app.route("/nova", methods=["POST"])
def nova_reply():
    data = request.get_json()
    user_input = data.get("text", "")
    lang = data.get("lang", "en")
    gender = data.get("gender", "male")

    if not user_input:
        return jsonify({"error": "No input text provided"}), 400

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Nova, a smart, calm, and friendly AI assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Sorry, something went wrong: {e}"

    fp = generate_voice(reply, lang=lang, gender=gender)
    return send_file(fp, mimetype="audio/mp3")

# === Homepage ===
@app.route("/", methods=["GET"])
def home():
    return "✅ Nova-Core server is running and ready!"

# === Test Route ===
@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "status": "online",
        "message": "Nova Core is working perfectly!",
        "version": "1.0.0"
    })

# === Health Check ===
@app.route("/ping", methods=["GET"])
def ping():
    return "pong"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
