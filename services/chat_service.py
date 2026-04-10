import ollama
import time
import json
from services.llm_service import STRUCTURING_MODEL, check_ollama_connection

CHAT_SYSTEM_PROMPT = """
You are an expert Document Assistant. Your goal is to help users understand and query the contents of a specific document that has been scanned.
You have the full context of the document text and structured fields.

Guidelines:
1. Ground your answers ONLY in the provided document data.
2. If the user asks for something NOT in the document, politely say it's not visible.
3. Be concise and professional.
4. Support Arabic and English naturally based on the user's query and document content.
"""

def query_document(user_query, doc_context, chat_history=None):
    """
    Process a chat query about a specific document.
    """
    start_time = time.time()
    
    if not check_ollama_connection():
        return "ERROR: AI service (Ollama) is not reachable.", 0.0

    # Build the context string
    context_str = f"DOCUMENT CONTENT (JSON/TEXT):\n{json.dumps(doc_context, indent=2)}\n\n"
    
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {"role": "user", "content": context_str + "USER QUESTION: " + user_query}
    ]

    # Add history if provided (future expansion)
    if chat_history:
        # Simplified history handling
        pass

    try:
        response = ollama.chat(
            model=STRUCTURING_MODEL,
            messages=messages,
            options={
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_gpu": -1
            },
            stream=False
        )
        
        answer = response.get("message", {}).get("content", "").strip()
        
    except Exception as e:
        print(f"[Chat Error] {e}")
        answer = f"I encountered an error processing your query: {str(e)}"

    return answer, round(time.time() - start_time, 2)
