import psycopg2
from psycopg2.extras import execute_values
from config.settings import POSTGRES_URI

# ------------------------------------------------------------------ #
#  Candidate table columns – keep in sync with DB schema
# ------------------------------------------------------------------ #
MASTER_COLUMNS = [
    "name", "email", "phone", "location", "education",
    "skills", "hard_skills", "soft_skills",
    "companies", "job_titles", "project_titles", "project_links",
    "career_stage", "sustainability_score", "internal_or_external"
]

def get_connection():
    """Return a new PostgreSQL connection using settings in .env"""
    return psycopg2.connect(POSTGRES_URI)

# ------------------------------------------------------------------ #
#  UPSERT helper
# ------------------------------------------------------------------ #
def insert_candidate(record: dict) -> None:
    """
    Insert or update a candidate by email (unique key).
    Any missing keys become NULL in the database.
    """
    full_record = {col: record.get(col) for col in MASTER_COLUMNS}
    columns     = list(full_record.keys())
    values      = [full_record[col] for col in columns]
    placeholders = ", ".join(["%s"] * len(columns))

    updates = ", ".join(
        f"{col}=EXCLUDED.{col}" for col in columns if col != "email"
    )

    query = f"""
        INSERT INTO candidates ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT (email) DO UPDATE SET {updates};
    """

    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
    conn.close()

# ------------------------------------------------------------------ #
#  DELETE helper  ← used by Streamlit dashboard
# ------------------------------------------------------------------ #
def delete_candidate_by_email(email: str) -> None:
    """Remove a candidate row entirely based on their unique email."""
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM candidates WHERE email = %s", (email,))
    conn.close()
