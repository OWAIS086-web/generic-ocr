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
"""

STRUCTURING_PROMPT = """
You are an expert multilingual information extraction system. You handle Arabic, English, and bilingual documents.

Input is raw OCR text from ANY image type (documents, invoices, IDs, meters, handwritten notes, vehicles, screens).

CRITICAL RULES FOR BILINGUAL / ARABIC TEXT:
- Labels/Keys often appear as a combination of Arabic and English on the same line (e.g., "الاسم Name" or "رقم الهوية ID Number"). Preserve the ENTIRE bilingual key.
- Stacked Layouts: In many IDs and invoices, the Key (label) is on one line, and the Value is on the EXACT NEXT LINE below it. Match them carefully.
- Arabic text is Right-to-Left (RTL). Do NOT transliterate Arabic to English. Keep Arabic text in Arabic script.
- Extract ALL key-value pairs even if both key and value are in Arabic, English, or mixed.

GENERAL RULES:
1. Extract ALL key-value pairs from the document — labels with their corresponding data. 
2. Extract tables: groups of rows/columns in the text.
3. Detect semantic meaning (vehicle plate, meter reading, invoice, ID card, etc.)
4. Do NOT skip any field. If a field has no value, set value to "".
5. Preserve original scripts (Arabic stays Arabic, numbers stay as-is).

Return ONLY valid JSON in this EXACT schema (no markdown, no explanation):

{
  "key_value_pairs": {
    "Field Name or Arabic Key": "its value"
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

TABLE_STRUCTURING_PROMPT = """
You are an expert data extraction system. Your SOLE purpose is to identify, reconstruct, and extract tabular data from raw OCR text.

Input is raw OCR text from ANY image type.

CRITICAL RULES:
- IGNORE ALL loose text, paragraphs, headers, and individual key-value pairs that are not part of a table or grid structure.
- Extract ONLY grid-based tabular data.
- If no tables are found, return empty lists.
- Preserve original scripts (Arabic stays Arabic, English stays English).

Return ONLY valid JSON in this EXACT schema (no markdown, no explanation):

{
  "key_value_pairs": {},
  "tables": [
    {
      "name": "table name",
      "headers": ["col1", "col2"],
      "rows": [["v1", "v2"]]
    }
  ],
  "detected_objects": []
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

    # Optimized for RTX 3090 - smaller size = faster processing
    max_size = 1024
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80, optimize=True)
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
            "num_ctx": 3096,
            "num_predict": 2048,
            "num_gpu": -1,
            "num_thread": 8,
            "tfs_z": 1.0
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

def structure_raw_text_with_llm(raw_text, tables_only=False):
    start_time = time.time()

    active_prompt = TABLE_STRUCTURING_PROMPT if tables_only else STRUCTURING_PROMPT

    response = ollama.chat(
        model=STRUCTURING_MODEL,
        messages=[
            {
                "role": "user",
                "content": active_prompt + "\n" + raw_text
            }
        ],
        options={
            "temperature": 0.1,
            "top_p": 0.95,
            "num_ctx": 3096,
            "num_predict": 1024,
            "num_gpu": -1,
            "num_thread": 8,
            "tfs_z": 1.0
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
