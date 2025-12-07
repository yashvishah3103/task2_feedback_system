from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS globally and handle OPTIONS automatically

DATA_FILE = "data.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")

# load_data, save_data, call_llm, generate_ai_outputs definitions here

@app.route("/submit", methods=["POST"])
def submit():
    payload = request.get_json(force=True)
    rating = payload.get("rating")
    review = payload.get("review", "").strip()

    if not review or rating is None:
        return jsonify({"error": "rating and review required"}), 400

    user_msg, summary, next_actions = generate_ai_outputs(review, rating)

    entry = {
        "timestamp": int(time.time()),
        "rating": int(rating),
        "review": review,
        "ai_response": user_msg,
        "summary": summary,
        "recommendation": next_actions
    }

    data = load_data()
    data.append(entry)
    save_data(data)

    return jsonify(entry), 201

# other routes like /admin, /admin_data

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

