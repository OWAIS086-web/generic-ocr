"""
PaddleOCR Service - Accurate OCR with text coordinates
Supports: Handwriting, printed text, numbers, license plates, etc.
"""

import cv2
import time
from paddleocr import PaddleOCR
import numpy as np

# Initialize PaddleOCR (supports multiple languages)
ocr = None

def initialize_paddle_ocr():
    """Initialize PaddleOCR with English and Arabic support"""
    global ocr
    if ocr is None:
        print("Initializing PaddleOCR...")
        start = time.time()
        ocr = PaddleOCR(use_angle_cls=True, lang='en')  # English + angle detection
        elapsed = time.time() - start
        print(f"✓ PaddleOCR initialized in {elapsed:.2f}s")
    return ocr

def extract_text_with_coordinates(image_path):
    """
    Extract text and coordinates using PaddleOCR
    Returns: List of dicts with text, confidence, and bounding box coordinates
    """
    try:
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print("Stage 1: Extracting Text with Coordinates (PaddleOCR)")
        print(f"{'='*60}")
        
        # Initialize OCR
        paddle_ocr = initialize_paddle_ocr()
        
        # Read image
        print(f"Reading image: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            raise Exception(f"Failed to read image: {image_path}")
        
        print(f"Image size: {image.shape}")
        
        # Perform OCR
        print("Performing OCR extraction...")
        result = paddle_ocr.ocr(image_path, cls=True)
        
        # Process results
        extracted_data = []
        for line in result:
            for word_info in line:
                # word_info format: (coordinates, (text, confidence))
                coords, (text, confidence) = word_info
                
                # Convert coordinates to dict
                bbox = {
                    'top_left': [float(coords[0][0]), float(coords[0][1])],
                    'top_right': [float(coords[1][0]), float(coords[1][1])],
                    'bottom_right': [float(coords[2][0]), float(coords[2][1])],
                    'bottom_left': [float(coords[3][0]), float(coords[3][1])]
                }
                
                extracted_data.append({
                    'text': text.strip(),
                    'confidence': float(confidence),
                    'coordinates': bbox
                })
        
        ocr_time = time.time() - start_time
        
        print(f"✓ Extracted {len(extracted_data)} text elements")
        print(f"✓ OCR completed in {ocr_time:.2f}s")
        print(f"{'='*60}\n")
        
        return extracted_data, ocr_time
    
    except Exception as e:
        print(f"Error in PaddleOCR extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def format_extracted_text(extracted_data):
    """
    Format extracted text for LLM processing
    Groups text by proximity (lines)
    """
    try:
        print("Formatting extracted text...")
        
        # Sort by Y coordinate (top to bottom)
        sorted_data = sorted(extracted_data, key=lambda x: x['coordinates']['top_left'][1])
        
        # Group into lines (texts with similar Y coordinates)
        lines = []
        current_line = []
        current_y = None
        y_threshold = 20  # pixels
        
        for item in sorted_data:
            y = item['coordinates']['top_left'][1]
            
            if current_y is None or abs(y - current_y) < y_threshold:
                current_line.append(item)
                if current_y is None:
                    current_y = y
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [item]
                current_y = y
        
        if current_line:
            lines.append(current_line)
        
        # Format as readable text
        formatted_text = ""
        for line in lines:
            line_text = " ".join([item['text'] for item in line])
            formatted_text += line_text + "\n"
        
        print(f"✓ Formatted into {len(lines)} lines")
        
        return formatted_text.strip(), extracted_data
    
    except Exception as e:
        print(f"Error formatting text: {str(e)}")
        raise

def visualize_ocr_results(image_path, extracted_data, output_path=None):
    """
    Visualize OCR results with bounding boxes
    Useful for debugging and verification
    """
    try:
        print("Visualizing OCR results...")
        
        image = cv2.imread(image_path)
        if image is None:
            return
        
        # Draw bounding boxes
        for item in extracted_data:
            coords = item['coordinates']
            
            # Convert to integer coordinates
            pts = np.array([
                coords['top_left'],
                coords['top_right'],
                coords['bottom_right'],
                coords['bottom_left']
            ], dtype=np.int32)
            
            # Draw rectangle
            cv2.polylines(image, [pts], True, (0, 255, 0), 2)
            
            # Put text
            text = item['text']
            confidence = item['confidence']
            label = f"{text} ({confidence:.2f})"
            
            cv2.putText(
                image,
                label,
                tuple(map(int, coords['top_left'])),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1
            )
        
        # Save visualization
        if output_path is None:
            output_path = image_path.replace('.', '_ocr_viz.')
        
        cv2.imwrite(output_path, image)
        print(f"✓ Visualization saved to: {output_path}")
        
        return output_path
    
    except Exception as e:
        print(f"Error visualizing results: {str(e)}")
        return None

def get_high_confidence_text(extracted_data, min_confidence=0.7):
    """
    Filter extracted text by confidence threshold
    Returns only high-confidence extractions
    """
    high_conf = [item for item in extracted_data if item['confidence'] >= min_confidence]
    low_conf = [item for item in extracted_data if item['confidence'] < min_confidence]
    
    print(f"High confidence ({min_confidence}+): {len(high_conf)} items")
    print(f"Low confidence (<{min_confidence}): {len(low_conf)} items")
    
    return high_conf, low_conf
