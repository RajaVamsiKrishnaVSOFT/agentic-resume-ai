# config/settings.py

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent
if BASE_DIR.name == "config":
    BASE_DIR = BASE_DIR.parent

# === Data Paths ===
DATA_DIR     = BASE_DIR / "data"
RAW_DIR      = DATA_DIR / "resumes_raw"
CLEANED_DIR  = DATA_DIR / "cleaned"
JSON_DIR     = DATA_DIR / "extracted_json"
OUTPUT_DIR   = DATA_DIR / "output"
LOG_DIR      = BASE_DIR / "logs"

# Create directories if missing
for d in (DATA_DIR, RAW_DIR, CLEANED_DIR, JSON_DIR, OUTPUT_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# === PostgreSQL Settings ===
DB_NAME     = os.getenv("POSTGRES_DB", "agentic_resume_ai")
DB_USER     = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
DB_HOST     = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT     = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# === LLM Model (local or cloud) ===
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
