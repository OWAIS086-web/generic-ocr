import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "ocr_history.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the database tables if they don't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ocr_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT    NOT NULL,
            processed_at     TEXT    NOT NULL,
            raw_text         TEXT,
            key_value_pairs  TEXT,   -- JSON string
            tables_data      TEXT,   -- JSON string
            timings          TEXT,   -- JSON string
            total_seconds    REAL,
            doc_type         TEXT,
            doc_confidence   REAL
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database initialised.")


def save_result(filename: str, raw_text: str, key_value_pairs: dict,
                tables: list, timings: dict, doc_type: str = "General",
                doc_confidence: float = 0.0) -> int:
    """Persist an OCR result and return its new row id."""
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO ocr_history
            (filename, processed_at, raw_text, key_value_pairs, tables_data, timings, total_seconds, doc_type, doc_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            raw_text or "",
            json.dumps(key_value_pairs or {}),
            json.dumps(tables or []),
            json.dumps(timings or {}),
            timings.get("total", 0) if timings else 0,
            doc_type,
            doc_confidence
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_history():
    """Return all history rows ordered by most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ocr_history ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history_by_id(record_id: int):
    """Return a single history record as a dict, or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM ocr_history WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_history(record_id: int) -> bool:
    """Delete a history record. Returns True if a row was deleted."""
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM ocr_history WHERE id = ?", (record_id,)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
