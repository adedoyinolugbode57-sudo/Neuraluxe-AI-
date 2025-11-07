# =========================================================
# 🌌 Free Smart AI — Independent Flask Route
# =========================================================

from flask import Flask, request, jsonify
from free_smart_ai import FreeSmartAI

app = Flask(__name__)
free_ai = FreeSmartAI()

@app.route("/api/ai/free", methods=["POST"])
def free_ai_endpoint():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    response = free_ai.generate(prompt)
    return jsonify({"prompt": prompt, "response": response})

# -----------------------------
# Optional: Run independently
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)