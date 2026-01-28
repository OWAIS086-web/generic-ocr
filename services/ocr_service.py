import cv2
import time
import os
from services.preprocessing_service import preprocess_image
from services.llm_service import perform_ocr_with_gemma, extract_structured_data
from services.pdf_service import pdf_to_images

def run_full_ocr_pipeline(path):
    """
    Complete OCR pipeline (Single-stage optimized):
    Single pass with llava-phi3 - Extracts text AND structured data directly from image
    CPU optimized, faster than 2-stage pipeline, more accurate with fine-tuned prompts
    """
    
    pipeline_start = time.time()
    images = [path]
    if path.lower().endswith(".pdf"):
        images = pdf_to_images(path)

    all_structured_data = []
    timings = {
        "preprocessing": 0,
        "structured_extraction": 0,
        "total": 0
    }

    for img_path in images:
        print(f"\n{'='*60}")
        print(f"Processing image: {img_path}")
        print(f"{'='*60}")
        
        # Step 1: Preprocess the image
        print("\nStep 1: Preprocessing image...")
        prep_start = time.time()
        preprocessed_img = preprocess_image(img_path)
        timings["preprocessing"] += time.time() - prep_start
        
        # Save preprocessed image temporarily
        temp_path = img_path.replace('.', '_preprocessed.')
        preprocessed_img.save(temp_path)
        
        # Step 2: llava-phi3 - Extract structured data directly (combines text extraction + structuring)
        print("\nStep 2: Extracting TEXT")
        extract_start = time.time()
        structured_data, extract_time = perform_ocr_with_gemma(temp_path)
        timings["structured_extraction"] += extract_time
        
        all_structured_data.append(structured_data)
        
        # Clean up temporary files
        try:
            os.remove(temp_path)
        except:
            pass

    timings["total"] = time.time() - pipeline_start

    return {
        "structured_data": all_structured_data,
        "status": "success",
        "timings": timings
    }
