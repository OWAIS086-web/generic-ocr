from flask import Blueprint, render_template, request, jsonify, session, send_from_directory
from services.ocr_service import run_full_ocr_pipeline
from services.llm_service import structure_raw_text_with_llm
from services.raw_text_to_structured_json import save_json_output
from services.annotation_service import annotate_image
from services.classification_service import classify_document
from services.chat_service import query_document
from models.database import save_result, get_all_history, get_history_by_id, delete_history
import os, json, time

ocr_bp = Blueprint("ocr", __name__)

@ocr_bp.route("/", methods=["GET"])
def upload_page():
    return render_template("dashboard.html")

def _execute_ocr_pipeline(path, filename, extract_kv=True, extract_tables_only=False, do_annotate=True, do_classify=True, skip_json_save=False):
    """Internal helper to run the full OCR/AI pipeline on a given file path"""
    # Step 1: Run OCR pipeline (extract raw text via vision LLM)
    result = run_full_ocr_pipeline(path)

    # Extract raw text from the first image
    structured_data = result.get("structured_data", [{}])[0]
    raw_text = structured_data.get("raw_text", "")
    timings = result.get("timings", {})
    
    # Step 1.5: Auto-Classification
    doc_type = "General"
    doc_confidence = 0.0
    if do_classify:
        try:
            class_res, class_time = classify_document(path)
            doc_type = class_res.get("doc_type", "General")
            doc_confidence = class_res.get("confidence", 0.0)
            timings["classification"] = class_time
            print(f"[OK] Classification: {doc_type} ({doc_confidence}) in {class_time}s")
        except Exception as e:
             print(f"[WARN] Classification failed: {e}")

    if extract_kv or extract_tables_only:
        # Step 2: Structure raw text using LLM
        structured_json, struct_time = structure_raw_text_with_llm(raw_text, tables_only=extract_tables_only)
        timings["structuring"] = struct_time
    else:
        structured_json = {}
        timings["structuring"] = 0.0

    # Add raw text to structured data
    structured_json["raw_text"] = raw_text

    # Step 3: Annotation – strictly conditional
    annotated_image_b64 = None
    ocr_boxes = []
    if do_annotate:
        try:
            from services.annotation_service import annotate_image
            ann_start = time.time()
            annotated_image_b64, ocr_boxes = annotate_image(
                path,
                structured_json.get("key_value_pairs", {})
            )
            timings["annotation"] = round(time.time() - ann_start, 2)
            print(f"[OK] Annotation done in {timings['annotation']}s ({len(ocr_boxes)} boxes)")
        except Exception as e:
            print(f"[WARN] Annotation failed: {e}")

    # Step 4: Save JSON output (skip for bulk processing)
    json_output_paths = {}
    if not skip_json_save:
        json_output_paths = save_json_output(path, structured_json)

    # Step 5: Persist result to database
    try:
        record_id = save_result(
            filename=filename,
            raw_text=raw_text,
            key_value_pairs=structured_json.get("key_value_pairs", {}),
            tables=structured_json.get("tables", []),
            timings=timings,
            doc_type=doc_type,
            doc_confidence=doc_confidence
        )
    except Exception as e:
        print(f"[DB WARNING] Could not save to DB: {e}")
        record_id = None

    return {
        "status": "success",
        "record_id": record_id,
        "filename": filename,
        "key_value_pairs": structured_json.get("key_value_pairs", {}),
        "tables": structured_json.get("tables", []),
        "raw_text": raw_text,
        "timings": timings,
        "json_files": json_output_paths,
        "annotated_image": annotated_image_b64,
        "ocr_boxes": ocr_boxes,
        "doc_type": doc_type,
        "doc_confidence": doc_confidence
    }

@ocr_bp.route("/process", methods=["POST"])
def process_ui():
    """Process uploaded file and return results"""
    file = request.files["file"]
    filename = os.path.basename(file.filename)
    path = os.path.join("uploads", filename)
    file.save(path)

    # Check Key-Pair extraction mode
    extract_kv = request.form.get("extract_kv", "true") == "true"
    extract_tables_only = request.form.get("extract_tables_only", "false") == "true"
    do_annotate = request.form.get("annotate_image", "true") == "true"
    do_classify = request.form.get("auto_classify", "true") == "true"

    res = _execute_ocr_pipeline(path, filename, extract_kv, extract_tables_only, do_annotate, do_classify)
    return jsonify(res)

@ocr_bp.route("/process-data-file", methods=["POST"])
def process_data_file():
    """Process a file that already exists in the data/ folder"""
    try:
        data = request.json
        filename = data.get("filename")
        if not filename:
            return jsonify({"status": "error", "message": "Missing filename"}), 400
            
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        path = os.path.join(data_dir, filename)
        
        if not os.path.exists(path):
            return jsonify({"status": "error", "message": f"File not found: {filename}"}), 404
            
        # Default flags for data processing
        extract_kv = data.get("extract_kv", True)
        extract_tables_only = data.get("extract_tables_only", False)
        do_annotate = data.get("annotate_image", False)
        do_classify = data.get("auto_classify", True)
        
        # Determine paths
        custom_dir = data.get("custom_path", "data")
        root_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(root_dir, custom_dir, filename)
        
        if not os.path.exists(path):
            return jsonify({"status": "error", "message": f"File not found: {path}"}), 404

        # Skip JSON save for bulk processing
        res = _execute_ocr_pipeline(path, filename, extract_kv, extract_tables_only, do_annotate, do_classify, skip_json_save=True)
        return jsonify(res)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@ocr_bp.route("/chat", methods=["POST"])
def doc_chat():
    """Chat with a document using its context"""
    try:
        data = request.json
        user_query = data.get("query")
        # Context can be passed from frontend (all extracted fields)
        doc_context = data.get("context", {})
        
        if not user_query:
            return jsonify({"status": "error", "message": "No query provided"})
            
        answer, chat_time = query_document(user_query, doc_context)
        
        return jsonify({
            "status": "success",
            "answer": answer,
            "time": chat_time
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@ocr_bp.route("/edit", methods=["GET"])
def edit_page():
    """Edit page for extracted data"""
    return render_template("edit.html")

@ocr_bp.route("/settings", methods=["GET"])
def settings_page():
    """Global application settings page"""
    return render_template("settings.html")

@ocr_bp.route("/bulk-upload", methods=["GET"])
def bulk_upload_page():
    """Bulk upload page for folder selection and parallel processing"""
    return render_template("bulk_upload.html")

# ───────────────────────── HISTORY ─────────────────────────

@ocr_bp.route("/history", methods=["GET"])
def history_page():
    """History page – list all past OCR scans"""
    records = get_all_history()
    # Decode JSON fields for the template
    for r in records:
        try:
            r["key_value_pairs"] = json.loads(r.get("key_value_pairs") or "{}")
        except Exception:
            r["key_value_pairs"] = {}
        try:
            r["tables_data"] = json.loads(r.get("tables_data") or "[]")
        except Exception:
            r["tables_data"] = []
        try:
            r["timings"] = json.loads(r.get("timings") or "{}")
        except Exception:
            r["timings"] = {}
    return render_template("history.html", records=records)

@ocr_bp.route("/history/<int:record_id>", methods=["GET"])
def history_detail(record_id):
    """Return a single history record as JSON (for modal)"""
    record = get_history_by_id(record_id)
    if not record:
        return jsonify({"status": "error", "message": "Not found"}), 404
    # Decode JSON blobs
    for field in ("key_value_pairs", "tables_data", "timings"):
        try:
            record[field] = json.loads(record.get(field) or "null")
        except Exception:
            record[field] = None
    return jsonify({"status": "success", "record": record})

@ocr_bp.route("/history/<int:record_id>", methods=["DELETE"])
def history_delete(record_id):
    """Delete a single history record"""
    ok = delete_history(record_id)
    if ok:
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Not found"}), 404

# ───────────────────────────────── QUICK SAMPLE ────────────────────────────────

@ocr_bp.route("/quick-sample", methods=["GET"])
def quick_sample_page():
    """Quick sample / demo page with gallery of data folder images"""
    import glob
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    exts = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff')
    images = []
    for ext in exts:
        images.extend(glob.glob(os.path.join(data_dir, ext)))
    image_names = [os.path.basename(p) for p in sorted(images)]
    return render_template("quick_sample.html", images=image_names)

@ocr_bp.route("/data-images", methods=["GET"])
def list_data_images():
    """Return JSON list of available sample images from a specific folder"""
    import glob
    custom_path = request.args.get("path", "data")
    root_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(root_dir, custom_path)
    
    if not os.path.exists(data_dir):
        return jsonify({"images": [], "error": f"Path not found: {custom_path}"})
        
    exts = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff')
    images = []
    for ext in exts:
        images.extend(glob.glob(os.path.join(data_dir, ext)))
    return jsonify({"images": [os.path.basename(p) for p in sorted(images)], "resolved_path": custom_path})

from flask import send_from_directory

@ocr_bp.route("/data/<path:filename>", methods=["GET"])
def serve_data_image(filename):
    """Serve an image from the default data/ folder"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    return send_from_directory(data_dir, filename)

@ocr_bp.route("/stream-bulk-file", methods=["GET"])
def stream_bulk_file():
    """Stream a file from a custom bulk path"""
    custom_path = request.args.get("path", "data")
    filename = request.args.get("filename")
    root_dir = os.path.dirname(os.path.dirname(__file__))
    full_dir = os.path.join(root_dir, custom_path)
    return send_from_directory(full_dir, filename)

# ───────────────────────────────── API ENDPOINTS ────────────────────────────────

@ocr_bp.route("/api/process", methods=["POST"])
def process_api():
    """API endpoint for processing"""
    file = request.files["file"]
    filename = os.path.basename(file.filename)
    path = os.path.join("uploads", filename)
    file.save(path)

    result = run_full_ocr_pipeline(path)
    return jsonify(result)

@ocr_bp.route("/api/extract", methods=["POST"])
def extract_api():
    """
    API endpoint to extract specific key-value pairs and tables from image

    Form Parameters:
    - file: Image file to process (required)
    - keys: Comma-separated list of key-pairs to extract (optional, returns all if not specified)

    Example:
    POST /api/extract
    Form Data:
      - file: <image_file>
      - keys: name,amount,date,invoice_number
    """
    try:
        # Validate file upload
        if "file" not in request.files:
            return jsonify({
                "status": "error",
                "message": "Missing required parameter: file",
                "example": "POST /api/extract with form data: file=<image>, keys=name,amount"
            }), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({
                "status": "error",
                "message": "No file selected"
            }), 400
        
        # Get requested keys from form data
        keys_param = request.form.get("keys", "")
        
        # Save uploaded file
        filename = os.path.basename(file.filename)
        path = os.path.join("uploads", filename)
        file.save(path)
        
        # Run OCR pipeline
        result = run_full_ocr_pipeline(path)
        
        # Extract key-value pairs and tables from first image
        structured_data = result.get("structured_data", [{}])[0]
        key_value_pairs = structured_data.get("key_value_pairs", {})
        tables = structured_data.get("tables", [])
        
        # Filter by requested keys if specified
        if keys_param:
            requested_keys = [k.strip().lower() for k in keys_param.split(",")]
            filtered_pairs = {}
            for key, value in key_value_pairs.items():
                if key.lower() in requested_keys:
                    filtered_pairs[key] = value
            key_value_pairs = filtered_pairs
        
        return jsonify({
            "status": "success",
            "file_name": file.filename,
            "key_value_pairs": key_value_pairs,
            "tables": tables
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
