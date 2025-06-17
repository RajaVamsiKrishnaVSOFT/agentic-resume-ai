# app/core/pipeline.py – Final fixed version: ensures all columns present in CSV
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
import shutil
import logging
import hashlib
import pandas as pd
import pdfplumber
import docx
from pathlib import Path
from config.settings import RAW_DIR, CLEANED_DIR, JSON_DIR, OUTPUT_DIR, BASE_DIR
from agents.cleaner_agent import run_cleaning_agent
from agents.extractor_agent import run_extraction_agent
from agents.classifier_agent import classify_career_stage, classify_skills
from agents.sustainability_agent import assess_sustainability
from agents.internal_check_agent import check_internal_candidate
from agents.jd_match_agent import match_to_job_description
from core.database import insert_candidate

MASTER_COLUMNS = [
    "name", "email", "phone", "location", "education",
    "skills", "hard_skills", "soft_skills",
    "companies", "job_titles", "project_titles", "project_links",
    "career_stage", "sustainability_score", "internal_or_external",
    "jd_match_score"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

HASH_LOG = OUTPUT_DIR / "resume_hashes.csv"
if not HASH_LOG.exists():
    pd.DataFrame(columns=["filename", "hash"]).to_csv(HASH_LOG, index=False)

JD_FILE_PATH = BASE_DIR / "sample_jd.txt"
JD_DISPLAY_PATH = OUTPUT_DIR / "jd_latest.txt"

def load_job_description():
    logger.info("📥 Loading Job Description from sample_jd.txt...")
    if JD_FILE_PATH.exists():
        jd_text = JD_FILE_PATH.read_text(encoding="utf-8")
        JD_DISPLAY_PATH.write_text(jd_text, encoding="utf-8")
        return jd_text
    return ""

def compute_file_hash(file_path) -> str:
    logger.info(f"🔒 Computing SHA-256 hash for {file_path}...")
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def read_file_content(file_path) -> str:
    logger.info(f"📖 Reading content from file: {file_path}")
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    elif file_path.endswith(".txt"):
        return open(file_path, 'r', errors='ignore').read()
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

def process_resume(file_path) -> dict:
    logger.info(f"🧹 Cleaning resume: {file_path}")
    raw_text = read_file_content(file_path)
    cleaned = run_cleaning_agent(raw_text)

    logger.info("📁 Saving cleaned resume text...")
    (CLEANED_DIR / f"{Path(file_path).stem}.txt").write_text(cleaned, encoding="utf-8")

    logger.info("🔍 Extracting structured data from resume...")
    record = run_extraction_agent(cleaned)

    for k in ["education", "project_titles", "project_links"]:
        if isinstance(record.get(k), (list, dict)):
            record[k] = json.dumps(record[k])

    logger.info("📝 Writing extracted data to JSON file...")
    with open(JSON_DIR / f"{Path(file_path).stem}.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    logger.info("📊 Enriching candidate with classification and scores...")
    record["career_stage"] = classify_career_stage(cleaned)

    logger.info("🎯 Classifying skills into hard and soft...")
    skills_json = classify_skills(record.get("skills", ""))
    record["hard_skills"] = "; ".join(skills_json.get("hard_skills", []))
    record["soft_skills"] = "; ".join(skills_json.get("soft_skills", []))
    record["phone"] = str(record.get("phone", ""))

    logger.info("♻️ Scoring candidate sustainability...")
    score = assess_sustainability(cleaned)
    record["sustainability_score"] = score if 1 <= score <= 10 else 0

    logger.info("🏢 Checking internal/external status...")
    record["internal_or_external"] = check_internal_candidate(cleaned)

    try:
        jd_text = load_job_description()
        logger.info("📌 Matching resume to job description...")
        jd_score = match_to_job_description(cleaned, jd_text)
        record["jd_match_score"] = round(jd_score, 2)
    except Exception as e:
        logger.error(f"JD match error: {e}")
        record["jd_match_score"] = 0.0

    return record

def main():
    files = os.listdir(RAW_DIR)
    logger.info(f"📂 Found {len(files)} files in {RAW_DIR}")

    hash_df = pd.read_csv(HASH_LOG)
    known_hashes = set(hash_df["hash"].values)

    for i, fname in enumerate(files, 1):
        logger.info(f"[{i}/{len(files)}] 🚀 Processing file: {fname}")
        path = os.path.join(RAW_DIR, fname)
        file_hash = compute_file_hash(path)
        if file_hash in known_hashes:
            logger.warning(f"[{i}] ⚠️ Duplicate file detected, skipping: {fname}")
            continue

        try:
            rec = process_resume(path)

            # Normalize and ensure all values are string-safe
            full = {}
            for col in MASTER_COLUMNS:
                val = rec.get(col, "")
                if isinstance(val, list):
                    full[col] = ", ".join(str(v) for v in val)
                elif isinstance(val, dict):
                    full[col] = json.dumps(val)
                elif pd.isna(val):
                    full[col] = ""
                else:
                    full[col] = str(val)

            logger.info("🧠 Inserting candidate into database...")
            insert_candidate(full)

            combined = OUTPUT_DIR / "combined.csv"
            append = True
            if combined.exists():
                existing = pd.read_csv(combined)
                if full["email"] in existing["email"].values:
                    logger.info(f"[{i}] ✉️ Email already in CSV. Skipping append.")
                    append = False
            if append:
                df = pd.DataFrame([full])
                df.to_csv(combined, mode="a", header=not combined.exists(), index=False)
                today_file = OUTPUT_DIR / f"resumes_{pd.Timestamp.now().date()}.csv"
                df.to_csv(today_file, mode="a", header=not today_file.exists(), index=False)
                logger.info(f"[{i}] 📈 Appended to CSV.")

            shutil.move(path, BASE_DIR / "data" / "processed" / fname)
            hash_df.loc[len(hash_df)] = {"filename": fname, "hash": file_hash}
            logger.info(f"[{i}] ✅ Completed and moved: {fname}")

        except Exception as e:
            logger.exception(f"[{i}] ❌ Error processing {fname}: {e}")
            with open(OUTPUT_DIR / "error.log", "a") as f:
                f.write(f"{pd.Timestamp.now()} - {fname} - ERROR: {str(e)}\n")

    hash_df.to_csv(HASH_LOG, index=False)
    logger.info("🧾 Hash log updated.")

if __name__ == "__main__":
    main()
