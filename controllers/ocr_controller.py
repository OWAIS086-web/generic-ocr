from flask import Blueprint, render_template, request, jsonify, session
from services.ocr_service import run_full_ocr_pipeline
from services.llm_service import structure_raw_text_with_llm
from services.raw_text_to_structured_json import save_json_output
import os, json

ocr_bp = Blueprint("ocr", __name__)

@ocr_bp.route("/", methods=["GET"])
def upload_page():
    return render_template("dashboard.html")

@ocr_bp.route("/process", methods=["POST"])
def process_ui():
    """Process uploaded file and return results"""
    file = request.files["file"]
    filename = file.filename
    path = os.path.join("uploads", filename)
    file.save(path)

    # Step 1: Run OCR pipeline (extract raw text)
    result = run_full_ocr_pipeline(path)
    
    # Extract raw text from the first image
    structured_data = result.get("structured_data", [{}])[0]
    raw_text = structured_data.get("raw_text", "")
    
    # Step 2: Structure raw text using qwen2.5:1.5b
    structured_json, struct_time = structure_raw_text_with_llm(raw_text)
    
    # Add raw text to structured data
    structured_json["raw_text"] = raw_text
    
    # Step 3: Save JSON output with same name as uploaded file
    json_output_paths = save_json_output(path, structured_json)
    print(f"[OK] Saved raw JSON to: {json_output_paths['raw_json']}")
    print(f"[OK] Saved structured JSON to: {json_output_paths['structured_json']}")
    
    # Update timings
    timings = result.get("timings", {})
    timings["structuring"] = struct_time
    
    # Return structured data
    return jsonify({
        "status": "success",
        "key_value_pairs": structured_json.get("key_value_pairs", {}),
        "tables": structured_json.get("tables", []),
        "raw_text": raw_text,
        "timings": timings,
        "json_files": json_output_paths
    })

@ocr_bp.route("/edit", methods=["GET"])
def edit_page():
    """Edit page for extracted data"""
    return render_template("edit.html")

@ocr_bp.route("/api/process", methods=["POST"])
def process_api():
    """API endpoint for processing"""
    file = request.files["file"]
    path = os.path.join("uploads", file.filename)
    file.save(path)

    result = run_full_ocr_pipeline(path)
    return jsonify(result)
