import json
import time
import os
import base64
import ollama
import re
from PIL import Image
import io

# ==============================
# GLOBALS
# ==============================
model_load_time = None

EXTRACTION_MODEL = "qwen2.5vl:7b"
STRUCTURING_MODEL = "qwen2.5:7b-instruct"      # STRONG text reasoning

_model_initialized = False

# ==============================
# PROMPTS
# ==============================

EXTRACTION_PROMPT_DETAILED = """
You are a high-accuracy OCR system.

Rules:
- Extract ALL visible text (printed + handwritten)
- Preserve line breaks, spacing, and layout
- Do NOT infer missing words
- Do NOT summarize
- Do NOT explain anything
- Output RAW TEXT ONLY

Start OCR now:
"""

STRUCTURING_PROMPT = """
You are a generic information extraction system.

Input is raw OCR text from ANY image type:
- documents
- handwritten notes
- vehicles
- meters / gauges
- screens / dashboards

Your tasks:
1. Extract key-value pairs (labels, readings, fields)
2. Extract tables if present
3. Detect semantic objects from text meaning

Special rules:
- If vehicle detected → extract number plate, vehicle type
- If meter/gauge detected → extract reading and unit
- If document detected → extract all fields

Return ONLY valid JSON in this exact schema:

{
  "key_value_pairs": {
    "field": "value"
  },
  "tables": [
    {
      "name": "table name",
      "headers": ["col1", "col2"],
      "rows": [["v1", "v2"]]
    }
  ],
  "detected_objects": [
    {
      "type": "object type",
      "description": "details"
    }
  ]
}

RAW OCR TEXT:
"""

# ==============================
# OLLAMA CHECK
# ==============================

def check_ollama_connection():
    try:
        ollama.list()
        return True
    except Exception as e:
        print(f"Ollama connection failed: {str(e)}")
        return False

# ==============================
# MODEL INIT
# ==============================

def load_model_directly():
    global _model_initialized, model_load_time

    if _model_initialized:
        return True

    start_time = time.time()

    if not check_ollama_connection():
        raise Exception("Ollama not running")

    models = ollama.list()
    available = [m.model for m in models.models]

    if EXTRACTION_MODEL not in available:
        raise Exception(f"Missing model: {EXTRACTION_MODEL}")

    if STRUCTURING_MODEL not in available:
        raise Exception(f"Missing model: {STRUCTURING_MODEL}")

    model_load_time = time.time() - start_time
    _model_initialized = True
    return True

# ==============================
# IMAGE → BASE64
# ==============================

def _image_to_base64(image_path):
    img = Image.open(image_path)

    if img.mode != "RGB":
        img = img.convert("RGB")

    # IMPORTANT for handwriting & bad images
    max_size = 1600
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ==============================
# STAGE 1 — OCR
# ==============================

def perform_ocr_with_gemma(image_path):
    start_time = time.time()

    if not check_ollama_connection():
        raise Exception("Ollama not running")

    image_data = _image_to_base64(image_path)

    response = ollama.chat(
        model=EXTRACTION_MODEL,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT_DETAILED,
                "images": [image_data]
            }
        ],
        options={
            "temperature": 0.0,
            "top_p": 1.0,
            "repeat_penalty": 1.05,
            "num_ctx": 6144   
        },
        stream=False
    )

    raw_text = response.get("message", {}).get("content", "").strip()

    return {
        "key_value_pairs": {},
        "tables": [],
        "detected_objects": [],
        "raw_text": raw_text
    }, round(time.time() - start_time, 2)

# ==============================
# STAGE 2 — STRUCTURE
# ==============================

def structure_raw_text_with_llm(raw_text):
    start_time = time.time()

    response = ollama.chat(
        model=STRUCTURING_MODEL,
        messages=[
            {
                "role": "user",
                "content": STRUCTURING_PROMPT + "\n" + raw_text
            }
        ],
        options={
            "temperature": 0.1,
            "top_p": 1.0,
            "num_ctx": 8192
        },
        stream=False
    )

    response_text = response.get("message", {}).get("content", "")

    try:
        match = re.search(r"\{[\s\S]*\}", response_text)
        structured = json.loads(match.group(0)) if match else {}
    except Exception:
        structured = {}

    return structured, round(time.time() - start_time, 2)

# ==============================
# BACKWARD COMPAT
# ==============================

def extract_structured_data(structured_data):
    return structured_data, 0.0
