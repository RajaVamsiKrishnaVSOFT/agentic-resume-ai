# app/dashboard.py – Updated with improved log capturing and error display

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import subprocess
import datetime
import time
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import RAW_DIR, OUTPUT_DIR, BASE_DIR
from core.pipeline import MASTER_COLUMNS
from core.database import delete_candidate_by_email

st.set_page_config(
    page_title="ResumePulse AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .reportview-container { background:#f6f7fb; }
    .sidebar .sidebar-content {
        background:linear-gradient(120deg,#1d3557 0%,#2a9d8f 100%);
        color:#fff;
    }
    .sidebar .stButton>button {
        border-radius:8px;background:#e76f51;color:#fff;border:none;
    }
    .sidebar .stButton>button:hover { background:#ff914d; }
    table { border-radius:8px!important; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("📤 Upload Resumes")
    uploads = st.file_uploader("Upload one or more resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)

    if uploads:
        for upload in uploads:
            save_path = Path(RAW_DIR) / upload.name
            save_path.write_bytes(upload.getbuffer())
            st.success(f"Saved ➜ {upload.name}")

        if st.button("🔁 Run Pipeline"):
            with st.spinner("Running pipeline — this may take a few seconds..."):
                try:
                    result = subprocess.run(
                        [sys.executable, str(BASE_DIR / "core" / "pipeline.py")],
                        capture_output=True,
                        text=True
                    )
                    stdout = result.stdout.strip()
                    stderr = result.stderr.strip()

                    if result.returncode != 0 or stderr:
                        st.error("⚠️ Pipeline ran with errors. Check logs below.")
                    else:
                        st.success("✅ Resume(s) processed successfully!")

                    if stdout or stderr:
                        combined_logs = ""
                        if stdout:
                            combined_logs += stdout
                        if stderr:
                            combined_logs += "\n\n[stderr]\n" + stderr
                        st.text_area("🧾 Console Logs", combined_logs.strip(), height=300)
                    else:
                        st.text_area("🧾 Console Logs", "⚠️ No output captured.", height=150)

                except Exception as e:
                    st.error("❌ An unexpected error occurred while running the pipeline.")
                    st.text_area("🧾 Console Logs", str(e), height=150)

                st.cache_data.clear()
                time.sleep(1)
                st.rerun()

    st.markdown("---")
    st.header("📋 Upload Job Description (JD)")
    jd_file = st.file_uploader("Optional: Upload a JD file (txt)", type=["txt"], key="jd_file")
    if jd_file:
        jd_path = Path(BASE_DIR / "sample_jd.txt")
        jd_path.write_text(jd_file.getvalue().decode("utf-8"))
        st.success(f"✅ JD uploaded: {jd_file.name}")

@st.cache_data
def load_data():
    csv_path = Path(OUTPUT_DIR) / "combined.csv"
    return pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame(columns=MASTER_COLUMNS)

data = load_data()

st.title("🧠 ResumePulse AI Dashboard")

missing_cols = [col for col in MASTER_COLUMNS if col not in data.columns]
if missing_cols:
    st.error(f"The following required columns are missing from the CSV: {missing_cols}")
else:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Total Resumes", len(data))
    with col_b:
        st.metric("Internal", int((data["internal_or_external"] == "Internal").sum()))
    with col_c:
        st.metric("External", int((data["internal_or_external"] == "External").sum()))

    jd_display_path = Path(OUTPUT_DIR) / "jd_latest.txt"
    if jd_display_path.exists():
        st.subheader("📄 Current Job Description Used")
        st.code(jd_display_path.read_text(encoding="utf-8"), language="markdown")

    with st.expander("🔍 Filters", expanded=False):
        stage_opt = ["All"] + sorted(data["career_stage"].dropna().unique().tolist())
        stage_sel = st.selectbox("Career Stage", stage_opt)
        score_min, score_max = st.slider("Sustainability Score", 0, 10, (0, 10))
        src_sel = st.radio("Source", ["All", "Internal", "External"], horizontal=True)
        jd_min, jd_max = st.slider("JD Match Score (%)", 0, 100, (0, 100))

        if stage_sel != "All":
            data = data[data["career_stage"] == stage_sel]
        if src_sel != "All":
            data = data[data["internal_or_external"] == src_sel]

        if "sustainability_score" in data.columns:
            data["sustainability_score"] = pd.to_numeric(data["sustainability_score"], errors="coerce")
            data = data[data["sustainability_score"].between(score_min, score_max)]

        if "jd_match_score" in data.columns:
            data["jd_match_score"] = pd.to_numeric(data["jd_match_score"], errors="coerce")
            data = data[data["jd_match_score"].between(jd_min, jd_max)]

    st.subheader("📑 Processed Candidates")
    if data.empty:
        st.info("No candidates yet.")
    else:
        data_reset = data.reset_index(drop=True)
        selected = st.multiselect(
            "Select row(s) to delete",
            data_reset.index,
            format_func=lambda i: f"{data_reset.at[i,'name']} | {data_reset.at[i,'email']}"
        )
        st.dataframe(data_reset, use_container_width=True, hide_index=True)

        if selected:
            delete_btn = st.button(
                f"🗑 Delete {len(selected)} candidate(s)",
                type="primary",
                key="delete_btn",
            )
            if delete_btn:
                for idx in selected:
                    email = data_reset.at[idx, "email"]
                    delete_candidate_by_email(email)
                    for file in ["combined.csv", f"resumes_{datetime.date.today()}.csv"]:
                        path = Path(OUTPUT_DIR) / file
                        if path.exists():
                            df = pd.read_csv(path)
                            df = df[df.email != email]
                            df.to_csv(path, index=False)
                    hash_path = Path(OUTPUT_DIR) / "resume_hashes.csv"
                    if hash_path.exists():
                        df_hash = pd.read_csv(hash_path)
                        df_hash = df_hash[df_hash.filename.str.contains(email) == False]
                        df_hash.to_csv(hash_path, index=False)
                st.success("Candidate(s) deleted!")
                st.cache_data.clear()
                st.rerun()

    if not data.empty:
        st.subheader("📊 Insights")
        col1, col2 = st.columns(2)
        col1.plotly_chart(
            px.histogram(data, x="career_stage", title="Career Stage Distribution",
                         color="career_stage", template="simple_white"),
            use_container_width=True,
        )
        col2.plotly_chart(
            px.histogram(data, x="internal_or_external", title="Internal vs External",
                         color="internal_or_external", template="simple_white"),
            use_container_width=True,
        )

    st.download_button(
        "📥 Download CSV",
        data.to_csv(index=False).encode("utf-8"),
        "filtered_candidates.csv",
        "text/csv",
    )
