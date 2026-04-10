from flask import Flask, jsonify, render_template
from controllers.ocr_controller import ocr_bp
import time
import os

app = Flask(__name__)
app.config.from_object("config.Config")
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Health check route (before Blueprint)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "OCR API"}), 200

# Root route - serve dashboard HTML
@app.route("/", methods=["GET"])
def root():
    try:
        return render_template("dashboard.html")
    except Exception as e:
        return jsonify({"status": "ready", "service": "OCR API", "version": "1.0"}), 200

app.register_blueprint(ocr_bp)

# Initialize model once at startup
def initialize_app():
    """Initialize Ollama model and database once when app starts"""
    print("\n" + "="*60)
    print("Starting OCR Application...")
    print("="*60)

    # Initialize database
    try:
        from models.database import init_db
        init_db()
    except Exception as e:
        print(f"[WARNING] DB init failed: {str(e)}")

    # Load LLM model
    try:
        from services.llm_service import load_model_directly
        start = time.time()
        load_model_directly()
        elapsed = time.time() - start
        print(f"[OK] Application ready in {elapsed:.2f}s")
        print("="*60 + "\n")
    except Exception as e:
        print(f"[ERROR] Initialization failed: {str(e)}")
        print("Make sure Ollama is running: ollama serve")
        print("="*60 + "\n")
        raise

# Initialize on app creation
initialize_app()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Routes registered:")
    print("="*60)
    for rule in app.url_map.iter_rules():
        print(f"{rule.rule} → {rule.endpoint} {list(rule.methods - {'OPTIONS', 'HEAD'})}")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
