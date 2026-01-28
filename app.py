from flask import Flask
from controllers.ocr_controller import ocr_bp
import time
import os

app = Flask(__name__)
app.config.from_object("config.Config")
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.register_blueprint(ocr_bp)

# Initialize model once at startup
def initialize_app():
    """Initialize Ollama model once when app starts"""
    print("\n" + "="*60)
    print("Starting OCR Application...")
    print("="*60)
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
    app.run(debug=True)
