"""Centralized, environment-driven application configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
# Load local development overrides. Existing process environment variables take precedence.
load_dotenv(BASE_DIR / ".env", override=False)
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
PROCESSED_DIR = DATA_DIR / "processed"

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_RECORDS_PER_FILE = int(os.getenv("MAX_RECORDS_PER_FILE", "5000"))
MAX_FIELD_CHARS = int(os.getenv("MAX_FIELD_CHARS", "20000"))
ALLOWED_EXTENSIONS = {".json", ".csv", ".txt"}

_DEFAULT_CORS_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

for directory in (INPUT_DIR, PROCESSED_DIR):
    directory.mkdir(parents=True, exist_ok=True)
