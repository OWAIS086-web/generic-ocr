import os

class Config:
    SECRET_KEY = "086086086"
    UPLOAD_FOLDER = "uploads"
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    DATABASE_PATH = os.environ.get("DB_PATH", "ocr_history.db")
