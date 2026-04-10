import ollama
import time
import json
import re
from services.llm_service import EXTRACTION_MODEL, _image_to_base64, check_ollama_connection

CLASSIFICATION_PROMPT = """
You are a document classification expert. 
Analyze the provided document image and categorize it into one of these types:
- Invoice
- Passport
- Emirates ID
- Resident Identity Card
- Driving License
- Vehicle Registration (Mulkiya)
- Electricity/Water Bill
- Medical Report
- Academic Transcript
- General (Default for anything else)

Return ONLY a valid JSON object in this format:
{
  "doc_type": "The Category",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}
"""

def classify_document(image_path):
    """
    Perform zero-shot document classification using the Vision LLM.
    """
    start_time = time.time()
    
    if not check_ollama_connection():
        return {"doc_type": "General", "confidence": 0.0, "reasoning": "Ollama not reachable"}, 0.0

    try:
        image_data = _image_to_base64(image_path)
        
        response = ollama.chat(
            model=EXTRACTION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": CLASSIFICATION_PROMPT,
                    "images": [image_data]
                }
            ],
            options={
                "temperature": 0.0,
                "num_ctx": 2048,
                "num_gpu": -1
            },
            stream=False
        )
        
        content = response.get("message", {}).get("content", "")
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            result = json.loads(match.group(0))
        else:
            result = {"doc_type": "General", "confidence": 0.0, "reasoning": "JSON not found"}
            
    except Exception as e:
        print(f"[Classification Error] {e}")
        result = {"doc_type": "General", "confidence": 0.0, "reasoning": str(e)}

    return result, round(time.time() - start_time, 2)
