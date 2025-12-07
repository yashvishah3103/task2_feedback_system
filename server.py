import os
import time
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DATA_FILE = "data.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")


# -------------------- Helpers --------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def call_llm(prompt):
    if not API_KEY:
        return "Error: Missing OpenRouter API key on server."

    headers = {
        "Authorization": f"Bearer " + API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "model": "google/gemini-2.0-flash-lite-preview-02-05:free",   # cheap + fast
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }

    r = requests.post(OPENROUTER_URL, headers=headers, json=body)

    if r.status_code != 200:
        return f"OpenRouter Error ({r.status_code}): {r.text}"

    try:
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "Error: Invalid LLM response"


def generate_ai_outputs(review, rating):
    prompt = f"""
    You are an AI writing assistant.  
    Return ONLY a JSON object. No extra text. No markdown.

    Rating: {rating}
    Review: {review}

    JSON format:
    {{
        "user_msg": "short friendly message for the user",
        "summary": "1 paragraph summary of the review",
        "next_actions": "clear recommended business action"
    }}
    """

    response = call_llm(prompt)

    # --- Parse JSON safely ---
    try:
        data = json.loads(response)
        user_msg = data.get("user_msg", "Thank you for your feedback!")
        summary = data.get("summary", "Summary unavailable.")
        next_actions = data.get("next_actions", "No recommendations.")
    except:
        # Fallback — never return empty responses
        user_msg = "Thank you for your review!"
        summary = f"The user rated {rating}/5 and said: {review}"
        next_actions = "Consider improving key areas mentioned."

    return user_msg, summary, next_actions


# -------------------- Routes --------------------

@app.route("/")
def home():
    return jsonify({"message": "Backend running"}), 200


# ------ FIX: Add GET handler to prevent 405 -------

@app.route("/submit", methods=["GET"])
def submit_info():
    return jsonify({"info": "Use POST to submit reviews"}), 200


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True)
    rating = data.get("rating")
    review = data.get("review", "").strip()

    if rating is None or not review:
        return jsonify({"error": "rating and review required"}), 400

    ai_msg, summary, next_actions = generate_ai_outputs(review, rating)

    entry = {
        "timestamp": int(time.time()),
        "rating": int(rating),
        "review": review,
        "ai_response": ai_msg,
        "summary": summary,
        "recommendation": next_actions
    }

    all_data = load_data()
    all_data.append(entry)
    save_data(all_data)

    return jsonify(entry), 201


@app.route("/admin_data", methods=["GET"])
def admin_data():
    return jsonify(load_data()), 200


@app.route("/admin", methods=["GET"])
def admin_page():
    return jsonify({"info": "Admin dashboard backend OK"}), 200
    
@app.route("/test_key")
def test_key():
    return jsonify({"API_KEY_loaded": API_KEY is not None})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
