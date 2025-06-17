# ✅ Enhanced watcher.py with hashing, deduplication, logging, and robustness

import time
import json
import shutil
import logging
import hashlib
import pdfplumber
import pandas as pd
import docx
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config.settings import RAW_DIR, CLEANED_DIR, JSON_DIR, OUTPUT_DIR, BASE_DIR
from agents.cleaner_agent import run_cleaning_agent
from agents.extractor_agent import run_extraction_agent
from agents.classifier_agent import classify_career_stage, classify_skills
from agents.sustainability_agent import assess_sustainability
from agents.internal_check_agent import check_internal_candidate
from database import insert_candidate
from core.pipeline import MASTER_COLUMNS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HASH_FILE = OUTPUT_DIR / "resume_hashes.csv"

# Load existing hashes
if HASH_FILE.exists():
    seen_hashes = set(pd.read_csv(HASH_FILE)["hash"].dropna())
else:
    seen_hashes = set()


def read_file_content(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    elif file_path.suffix.lower() == ".docx":
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return file_path.read_text(errors='ignore')


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def process_file(path: Path):
    try:
        logger.info(f"📄 Processing new resume: {path.name}")
        text = read_file_content(path)
        text_hash = hash_text(text)

        if text_hash in seen_hashes:
            logger.info(f"⏩ Skipping duplicate resume: {path.name}")
            return

        cleaned = run_cleaning_agent(text)
        (CLEANED_DIR / f"{path.stem}.txt").write_text(cleaned)

        rec = run_extraction_agent(cleaned)
        with open(JSON_DIR / f"{path.stem}.json", "w") as f:
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
                logger.warning(f"⚠️ Score out of bounds: {score}")
                score = 0
        except Exception as e:
            logger.error(f"❌ Sustainability score error: {e}")
            score = 0
        rec["sustainability_score"] = score

        rec["internal_or_external"] = check_internal_candidate(cleaned)
        full = {col: rec.get(col, "") for col in MASTER_COLUMNS}
        insert_candidate(full)

        combined = OUTPUT_DIR / "combined.csv"
        append = True
        if combined.exists():
            existing = pd.read_csv(combined)
            if full["email"] in existing["email"].values:
                append = False
                logger.info(" → Duplicate email, skipped combined.csv")

        if append:
            df = pd.DataFrame([full])
            df.to_csv(combined, mode="a", header=not combined.exists(), index=False)
            today_file = OUTPUT_DIR / f"resumes_{pd.Timestamp.now().date()}.csv"
            df.to_csv(today_file, mode="a", header=not today_file.exists(), index=False)
            logger.info(" → Appended to CSVs")

        # Append hash
        pd.DataFrame([{"hash": text_hash}]).to_csv(HASH_FILE, mode="a", header=not HASH_FILE.exists(), index=False)
        seen_hashes.add(text_hash)

        shutil.move(path, BASE_DIR / "data" / "processed" / path.name)
        logger.info(f"✅ Moved to processed/{path.name}")

    except Exception as e:
        logger.exception(f"❌ Failed to process {path.name}: {e}")


class ResumeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith((".pdf", ".docx", ".txt")):
            time.sleep(1)
            process_file(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith((".pdf", ".docx", ".txt")):
            time.sleep(1)
            process_file(Path(event.src_path))


def start_watcher():
    observer = Observer()
    observer.schedule(ResumeHandler(), str(RAW_DIR), recursive=False)
    observer.start()
    print(f"👀 Watching resumes in {RAW_DIR} ... Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_watcher()