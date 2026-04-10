"""
Annotation Service (EasyOCR backend)
======================================
1. Runs EasyOCR on an image → word bounding boxes + text + confidence.
2. Fuzzy-matches VLLM-structured KV values against OCR words.
3. Draws coloured bounding boxes with Pillow:
     • Cyan  (0,220,255) – all OCR words
     • Gold  (255,200,0) – KV-matched words / phrases
4. Returns (annotated_b64: str, ocr_boxes: list[dict]).

ocr_boxes item schema:
  { "text": str, "conf": float, "x": int, "y": int, "w": int, "h": int,
    "matched_key": str | None }
"""

import base64
import io
import time
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Lazy EasyOCR singleton ────────────────────────────────────────────────────
_easy_reader = None

def _get_easy_reader():
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        print("[annotation] Initialising EasyOCR (en + ar)…")
        t0 = time.time()
        # Include Arabic ('ar') for bilingual documents
        try:
            _easy_reader = easyocr.Reader(['en', 'ar'], gpu=True)
        except Exception:
            _easy_reader = easyocr.Reader(['en'], gpu=True)
        print(f"[annotation] EasyOCR ready in {time.time()-t0:.2f}s")
    return _easy_reader


# ── Helpers ───────────────────────────────────────────────────────────────────

def _poly_to_xywh(bbox):
    """Convert polygon [[x,y],…] to axis-aligned bbox (x,y,w,h)."""
    xs = [pt[0] for pt in bbox]
    ys = [pt[1] for pt in bbox]
    x, y = int(min(xs)), int(min(ys))
    w, h = int(max(xs)) - x, int(max(ys)) - y
    return x, y, max(w, 1), max(h, 1)


def _normalise(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _words_match(ocr_text: str, kv_value: str) -> bool:
    ov = _normalise(kv_value)
    ot = _normalise(ocr_text)
    if not ov or len(ov) < 2:
        return False
    if ov in ot or ot in ov:
        return True
    v_toks = set(ov.split())
    t_toks = set(ot.split())
    if not v_toks:
        return False
    return len(v_toks & t_toks) / len(v_toks) >= 0.6


def _try_load_font(size=13):
    for name in ["arial.ttf", "ArialUnicode.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


# ── Main entry point ──────────────────────────────────────────────────────────

def annotate_image(image_path: str, kv_pairs: dict) -> tuple:
    """
    Parameters
    ----------
    image_path : str   Path to the original uploaded image.
    kv_pairs   : dict  { "Field Name": "value", … } from VLLM structuring.

    Returns
    -------
    (annotated_b64: str, ocr_boxes: list[dict])
    """
    t0 = time.time()

    # 1. Load image
    pil_img = Image.open(image_path).convert("RGB")
    img_w, img_h = pil_img.size

    # Resize large images for reasonable web display
    MAX_DIM = 1600
    scale = 1.0
    if max(img_w, img_h) > MAX_DIM:
        scale = MAX_DIM / max(img_w, img_h)
        pil_img = pil_img.resize((int(img_w * scale), int(img_h * scale)), Image.Resampling.LANCZOS)
        img_w, img_h = pil_img.size

    # 2. Run EasyOCR
    reader = _get_easy_reader()
    np_img = np.array(pil_img)
    results = reader.readtext(np_img, detail=1)

    ocr_boxes = []
    for (bbox, text, conf) in results:
        try:
            # Scale coordinates if image was resized (bbox is already in resized space)
            x, y, w, h = _poly_to_xywh(bbox)
            ocr_boxes.append({
                "text": text.strip(),
                "conf": round(float(conf), 3),
                "x": x, "y": y, "w": w, "h": h,
                "matched_key": None,
            })
        except Exception:
            continue

    print(f"[annotation] EasyOCR found {len(ocr_boxes)} boxes")

    # 3. Match KV values → OCR boxes
    for box in ocr_boxes:
        for key, value in kv_pairs.items():
            if _words_match(box["text"], str(value)):
                box["matched_key"] = key
                break

    matched_count = sum(1 for b in ocr_boxes if b["matched_key"])
    print(f"[annotation] {matched_count} KV matches found")

    # 4. Draw annotations with Pillow
    overlay     = pil_img.convert("RGBA").copy()
    draw        = ImageDraw.Draw(overlay, "RGBA")
    font_label  = _try_load_font(12)

    # Colours  (R,G,B,A)
    COLOR_OCR_FILL   = (0,   220, 255,  35)
    COLOR_OCR_BORDER = (0,   220, 255, 200)
    COLOR_KV_FILL    = (255, 200,   0,  60)
    COLOR_KV_BORDER  = (255, 180,   0, 230)
    COLOR_LABEL_BG   = (20,  20,  40, 200)
    COLOR_LABEL_FG   = (255, 255, 255, 255)

    for box in ocr_boxes:
        x, y, w, h = box["x"], box["y"], box["w"], box["h"]
        x2, y2 = x + w, y + h
        is_kv  = box["matched_key"] is not None

        fill        = COLOR_KV_FILL   if is_kv else COLOR_OCR_FILL
        border      = COLOR_KV_BORDER if is_kv else COLOR_OCR_BORDER
        bw          = 2               if is_kv else 1

        draw.rectangle([x, y, x2, y2], fill=fill, outline=border, width=bw)

        if is_kv:
            label = f"  {box['matched_key'][:20]}  "
            try:
                bb = font_label.getbbox(label)
                lw, lh = bb[2] - bb[0], bb[3] - bb[1]
            except Exception:
                lw, lh = len(label) * 7, 14
            lx = max(x, 0)
            ly = max(y - lh - 2, 0)
            draw.rectangle([lx, ly, lx + lw, ly + lh], fill=COLOR_LABEL_BG)
            draw.text((lx + 2, ly), label, font=font_label, fill=COLOR_LABEL_FG)

    # 5. Composite and encode as base64 JPEG
    annotated = Image.alpha_composite(pil_img.convert("RGBA"), overlay).convert("RGB")

    buf = io.BytesIO()
    annotated.save(buf, format="JPEG", quality=88, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    print(f"[annotation] Done in {time.time()-t0:.2f}s — image size {img_w}x{img_h}")
    return b64, ocr_boxes
