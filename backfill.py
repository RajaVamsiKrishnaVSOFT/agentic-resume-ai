# === backfill.py (Enhanced with hashing + logging) ===
import logging
import json
import shutil
import hashlib
import pandas as pd
from pathlib import Path
from config.settings import RAW_DIR, CLEANED_DIR, JSON_DIR, OUTPUT_DIR, BASE_DIR
from core.database import insert_candidate
from agents.cleaner_agent import run_cleaning_agent
from agents.extractor_agent import run_extraction_agent
from agents.classifier_agent import classify_career_stage, classify_skills
from agents.sustainability_agent import assess_sustainability
from agents.internal_check_agent import check_internal_candidate
from core.pipeline import MASTER_COLUMNS

import pdfplumber
import docx

HASH_LOG = OUTPUT_DIR / "resume_hashes.csv"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def is_duplicate(resume_hash: str) -> bool:
    if not HASH_LOG.exists():
        return False
    existing = pd.read_csv(HASH_LOG)
    return resume_hash in existing["hash"].values

def log_hash(resume_hash: str):
    mode = "a" if HASH_LOG.exists() else "w"
    df = pd.DataFrame([{"hash": resume_hash}])
    df.to_csv(HASH_LOG, mode=mode, header=not HASH_LOG.exists(), index=False)

def read_file_content(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    elif file_path.suffix.lower() == ".docx":
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return file_path.read_text(errors='ignore')

def backfill():
    files = list(Path(RAW_DIR).iterdir())
    results = []

    for file in files:
        try:
            text = read_file_content(file)
            resume_hash = compute_hash(text)
            if is_duplicate(resume_hash):
                logger.info(f"⚠️ Duplicate resume skipped: {file.name}")
                continue

            cleaned = run_cleaning_agent(text)
            (CLEANED_DIR / f"{file.stem}.txt").write_text(cleaned)

            rec = run_extraction_agent(cleaned)
            with open(JSON_DIR / f"{file.stem}.json", "w") as f:
                json.dump(rec, f, indent=2)

            rec["career_stage"] = classify_career_stage(cleaned)
            skills_json = classify_skills(rec.get("skills", ""))
            rec["hard_skills"] = "; ".join(skills_json.get("hard_skills", []))
            rec["soft_skills"] = "; ".join(skills_json.get("soft_skills", []))
            rec["phone"] = str(rec.get("phone", ""))

            try:
                raw_score = assess_sustainability(cleaned)
                score_line = str(raw_score).strip().splitlines()[0]
                score = int(score_line)
                if not (1 <= score <= 10):
                    logger.warning(f"⚠️ Sustainability score out of bounds: {score}")
                    score = 0
            except Exception as e:
                logger.error(f"❌ Sustainability score error: {e}")
                score = 0
            rec["sustainability_score"] = score

            rec["internal_or_external"] = check_internal_candidate(cleaned)
            full = {col: rec.get(col, "") for col in MASTER_COLUMNS}
            insert_candidate(full)
            results.append(full)

            log_hash(resume_hash)
            shutil.move(file, BASE_DIR / "data" / "processed" / file.name)
            logger.info(f"✅ Processed and moved: {file.name}")

        except Exception as e:
            logger.exception(f"❌ Error processing {file.name}: {e}")

    if results:
        df = pd.DataFrame(results)
        df = df.reindex(columns=MASTER_COLUMNS)
        df.to_csv(OUTPUT_DIR / "resume_backfill_summary.csv", index=False)
    logger.info("✅ Backfill complete.")

if __name__ == "__main__":
    backfill()
