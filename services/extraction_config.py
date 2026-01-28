"""
Advanced extraction configuration for different document types.
Use document-specific prompts to improve accuracy.
"""

# Document type specific prompts for better accuracy
INVOICE_PROMPT = """Analyze this INVOICE document and extract ALL information accurately in this JSON format:

{
    "document_type": "invoice",
    "key_value_pairs": {
        "invoice_number": "exact number as shown",
        "invoice_date": "exact date as shown",
        "due_date": "exact date or null",
        "vendor_name": "company name",
        "vendor_address": "full address",
        "customer_name": "customer/bill-to name",
        "customer_address": "full address",
        "currency": "currency symbol or code"
    },
    "tables": [
        {
            "name": "line_items",
            "headers": ["Item Description", "Quantity", "Unit Price", "Total"],
            "rows": [
                ["Item 1", "qty1", "price1", "total1"],
                ["Item 2", "qty2", "price2", "total2"]
            ]
        }
    ],
    "line_items": [
        {"description": "item name exactly", "quantity": "number", "unit_price": "price", "total": "amount"},
        {"description": "item name exactly", "quantity": "number", "unit_price": "price", "total": "amount"}
    ],
    "totals": {
        "subtotal": "amount as shown",
        "tax": "tax amount or null",
        "shipping": "shipping cost or null",
        "total": "final total amount"
    },
    "raw_text": "complete document text"
}

RULES:
1. Find and extract invoice number (not order number or PO)
2. Extract invoice date in format shown, and due date if present
3. Identify vendor (seller) and customer (buyer) information
4. Extract all line items with exact descriptions, quantities, and prices
5. Identify and total amounts (subtotal, tax if applicable, final total)
6. Preserve all numbers exactly - no rounding or modification
7. Return ONLY valid JSON, nothing else"""

RECEIPT_PROMPT = """Analyze this RECEIPT document and extract in this JSON format:

{
    "document_type": "receipt",
    "key_value_pairs": {
        "receipt_number": "number",
        "date": "date as shown",
        "time": "time if shown or null",
        "merchant_name": "store/business name",
        "merchant_address": "location if shown",
        "payment_method": "cash/card/etc"
    },
    "line_items": [
        {"description": "item name", "quantity": "qty", "price": "unit_price", "total": "line_total"}
    ],
    "totals": {
        "subtotal": "subtotal",
        "tax": "tax amount",
        "total": "final amount",
        "paid": "amount paid"
    },
    "raw_text": "all text"
}

RULES:
1. Extract receipt number and date/time
2. Find merchant/store name and location
3. List all items purchased with quantities and prices
4. Extract payment information
5. Preserve all amounts exactly"""

PO_PROMPT = """Analyze this PURCHASE ORDER and extract in this JSON format:

{
    "document_type": "purchase_order",
    "key_value_pairs": {
        "po_number": "number",
        "po_date": "date",
        "vendor_name": "supplier name",
        "vendor_contact": "address/phone",
        "ship_to": "destination address",
        "delivery_date": "expected delivery",
        "po_total": "total amount"
    },
    "line_items": [
        {"description": "item", "quantity": "qty", "unit_price": "price", "total": "amount"}
    ],
    "raw_text": "all text"
}

RULES:
1. Extract PO number and date
2. Find vendor (supplier) details
3. Extract ship-to address and delivery date
4. List all ordered items with quantities and prices
5. Extract total amount"""

CONTRACT_PROMPT = """Analyze this CONTRACT/AGREEMENT and extract in this JSON format:

{
    "document_type": "contract",
    "key_value_pairs": {
        "contract_type": "type of contract",
        "contract_date": "date",
        "contract_number": "if shown",
        "party1_name": "first party",
        "party1_address": "address",
        "party2_name": "second party",
        "party2_address": "address",
        "effective_date": "date",
        "end_date": "date if shown"
    },
    "key_terms": {
        "term1": "value",
        "payment_terms": "terms if mentioned",
        "renewal_terms": "renewal info"
    },
    "raw_text": "key paragraphs of contract"
}

RULES:
1. Extract contract type and dates
2. Identify all parties and their contact information
3. Extract key terms and conditions
4. Note payment and renewal terms
5. Include important clauses"""

FORM_PROMPT = """Analyze this FORM and extract ALL filled-in fields in this JSON format:

{
    "document_type": "form",
    "form_name": "name of form if visible",
    "form_fields": {
        "field_label": "filled_value",
        "field_label2": "filled_value2"
    },
    "checkboxes": {
        "checkbox_label": "checked/unchecked"
    },
    "raw_text": "all visible text"
}

RULES:
1. Extract all form field labels and their filled values
2. Note which checkboxes are checked
3. Preserve exact values as entered
4. Include all visible fields even if blank
5. Return exact text as shown"""


def get_document_specific_prompt(document_type="generic"):
    """Get the appropriate extraction prompt for document type."""
    prompts = {
        "invoice": INVOICE_PROMPT,
        "receipt": RECEIPT_PROMPT,
        "po": PO_PROMPT,
        "purchase_order": PO_PROMPT,
        "contract": CONTRACT_PROMPT,
        "form": FORM_PROMPT,
        "generic": None  # Use default
    }
    return prompts.get(document_type.lower(), None)


# Document type detection patterns
DOCUMENT_TYPE_PATTERNS = {
    "invoice": [
        r"invoice\s*#?(\d+)",
        r"inv\s*#?(\d+)",
        r"bill of sale",
        r"invoice amount",
        r"bill to.*ship to"
    ],
    "receipt": [
        r"receipt\s*#?(\d+)",
        r"receipt number",
        r"total\s*\$?\s*\d+",
        r"cash register",
        r"thank you",
        r"merchant"
    ],
    "po": [
        r"purchase order",
        r"p\.?o\.?\s*#?(\d+)",
        r"po number",
        r"ship to",
        r"delivery date"
    ],
    "contract": [
        r"contract",
        r"agreement",
        r"terms.*conditions",
        r"signature",
        r"dated.*\d+",
        r"between.*and"
    ],
    "form": [
        r"form\s*#?(\d+)",
        r"please fill in",
        r"checkbox",
        r"signature line",
        r"applicant.*information"
    ]
}


def detect_document_type(text):
    """Detect document type from OCR text."""
    import re
    text_lower = text.lower()
    
    for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        matches = sum(1 for pattern in patterns if re.search(pattern, text_lower, re.IGNORECASE))
        if matches >= 2:  # At least 2 patterns match
            return doc_type
    
    return "generic"
