import json
import re

def parse_raw_text_to_structured(raw_text):
    result = {"key_value_pairs": {}, "tables": [], "raw_text": raw_text}
    if not raw_text:
        return result
    lines = raw_text.split('\n')
    result["key_value_pairs"] = extract_key_value_pairs(lines)
    result["tables"] = extract_tables(lines)
    return result

def extract_key_value_pairs(lines):
    kv_pairs = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                if key and value and len(key) < 100:
                    kv_pairs[key] = value
                    continue
        if ' - ' in line:
            parts = line.split(' - ', 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                if key and value and len(key) < 100 and not key.isdigit():
                    kv_pairs[key] = value
                    continue
        words = line.split()
        if len(words) >= 2:
            first_word = words[0]
            if first_word.lower() in ['name', 'date', 'amount', 'total', 'invoice', 'id', 'email', 'phone', 'address', 'status', 'type', 'description', 'quantity', 'price', 'cost', 'tax', 'subtotal', 'customer', 'vendor', 'company', 'title', 'number', 'code', 'reference']:
                key = first_word
                value = ' '.join(words[1:])
                if value and len(key) < 100:
                    kv_pairs[key] = value
    return kv_pairs

def extract_tables(lines):
    tables = []
    table_lines = []
    in_table = False
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if table_lines and len(table_lines) > 1:
                table = parse_table_lines(table_lines)
                if table:
                    tables.append(table)
            table_lines = []
            in_table = False
            continue
        if re.search(r'\s{2,}', line_stripped) or '\t' in line:
            table_lines.append(line_stripped)
            in_table = True
        elif in_table and table_lines:
            if len(table_lines) > 1:
                table = parse_table_lines(table_lines)
                if table:
                    tables.append(table)
            table_lines = []
            in_table = False
    if table_lines and len(table_lines) > 1:
        table = parse_table_lines(table_lines)
        if table:
            tables.append(table)
    return tables

def parse_table_lines(table_lines):
    if len(table_lines) < 2:
        return None
    header_line = table_lines[0]
    headers = re.split(r'\s{2,}|\t+', header_line)
    headers = [h.strip() for h in headers if h.strip()]
    if len(headers) < 2:
        return None
    rows = []
    for row_line in table_lines[1:]:
        row_cells = re.split(r'\s{2,}|\t+', row_line)
        row_cells = [c.strip() for c in row_cells if c.strip()]
        if len(row_cells) == len(headers):
            rows.append(row_cells)
    if not rows:
        return None
    return {"name": "Table", "headers": headers, "rows": rows}

def save_json_output(filename, data):
    """Save both raw and structured JSON files"""
    base_filename = filename.rsplit('.', 1)[0]
    
    # Extract raw text if present
    raw_text = data.get("raw_text", "")
    
    # Save raw text as JSON
    raw_json_filename = base_filename + '_raw.json'
    raw_data = {"raw_text": raw_text}
    with open(raw_json_filename, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved raw text to: {raw_json_filename}")
    
    # Save structured data (without raw_text to avoid duplication)
    structured_json_filename = base_filename + '_structured.json'
    structured_data = {k: v for k, v in data.items() if k != "raw_text"}
    with open(structured_json_filename, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved structured data to: {structured_json_filename}")
    
    return {
        "raw_json": raw_json_filename,
        "structured_json": structured_json_filename
    }
