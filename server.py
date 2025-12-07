from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DATA_FILE = "data.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def call_llm(prompt, model="mistralai/mistral-7b-instruct", timeout=30):
    if not API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300,
    }
    r = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    resp = r.json()
    return resp["choices"][0]["message"]["content"]

def generate_ai_outputs(review, rating):
    prompt = f"""
Review: \"{review}\"
Rating: {rating}

Produce ONLY valid JSON with exactly three keys:
{{"response_to_user": "...", "summary":"...", "next_actions":"..."}}

- response_to_user: A short friendly reply to the reviewer.
- summary: One-line summary of the review.
- next_actions: 1-2 recommended actions for the business (short).
"""
    try:
        text = call_llm(prompt)
        import re
        pattern = re.compile(r'\{.*\}', re.DOTALL)
        m = pattern.search(text)
        if m:
            parsed = json.loads(m.group(0))
            return parsed.get("response_to_user", ""), parsed.get("summary", ""), parsed.get("next_actions", "")
        else:
            parsed = json.loads(text)
            return parsed.get("response_to_user", ""), parsed.get("summary", ""), parsed.get("next_actions", "")
    except Exception as e:
        print("LLM error:", e)
        return ("Thanks — we got your review!", "AI error: could not generate summary.", "Contact the reviewer or inspect details.")

@app.route("/")
def serve_user_dashboard():
    return send_from_directory("user_dashboard", "index.html")

@app.route("/admin")
def serve_admin_dashboard():
    return send_from_directory("admin_dashboard", "index.html")

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

@app.route("/admin_data", methods=["GET"])
def admin_data():
    data = load_data()
    return jsonify(data), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
