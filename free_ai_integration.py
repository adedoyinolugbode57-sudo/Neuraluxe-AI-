# =========================================================
# 🌌 Free Smart AI — Neuraluxe-AI Integration
# =========================================================

from flask import Blueprint, request, jsonify
from free_smart_ai import FreeSmartAI

# Create a blueprint so it can be registered in main app
free_ai_bp = Blueprint("free_ai", __name__, url_prefix="/api/ai/free")

free_ai = FreeSmartAI()

@free_ai_bp.route("/", methods=["POST"])
def free_ai_endpoint():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    response = free_ai.generate(prompt)
    return jsonify({"prompt": prompt, "response": response})

# Optional: standalone run for testing
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(free_ai_bp)
    app.run(host="0.0.0.0", port=5050, debug=True)