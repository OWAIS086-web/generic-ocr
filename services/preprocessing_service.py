from PIL import Image, ImageEnhance
import cv2
import numpy as np

def preprocess_image(image_path):
    """
    Preprocess image to enhance text readability.
    Adjusts contrast, brightness, and applies denoising.
    """
    # Load image with PIL
    img = Image.open(image_path)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    
    # Enhance brightness
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)
    
    # Convert to numpy array for OpenCV operations
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Apply bilateral filter to reduce noise while preserving edges
    img_cv = cv2.bilateralFilter(img_cv, 9, 75, 75)
    
    # Convert back to PIL Image
    img_processed = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    
    return img_processed

def image_to_base64(image):
    """Convert PIL Image to base64 string for API calls."""
    import base64
    from io import BytesIO
    
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')
