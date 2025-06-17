# 🧠 ResumePulse AI

An intelligent resume processing and candidate screening system powered by open-source LLMs, CrewAI agents, and a modular backend pipeline.

## 🚀 Features

- 🧹 Resume cleaning with formatting normalization
- 🔍 Field extraction (name, skills, experience, etc.)
- 🤖 Skill classification into hard & soft skills
- ♻️ Sustainability scoring (1–10) for long-term fit
- 🎯 JD-Resume match scoring (0–100)
- 🆔 Internal vs External classification
- 📊 Streamlit dashboard for filtering, deleting, and exporting candidates
- 🧠 Local inference using Ollama + Mistral
- 🗃️ PostgreSQL + CSV storage
- 🛠️ Ready to migrate to Next.js frontend and FastAPI backend

## 📂 Folder Structure

agentic_resume_ai/
├── agents/ ← AI agent modules (extractor, cleaner, classifier, etc.)
├── core/ ← Pipeline, DB, and watcher logic
├── app/ ← Streamlit frontend
├── data/ ← Raw, processed, and output resume data
├── config/ ← Settings and environment variables
├── crewai_engine/ ← CrewAI orchestration layer (WIP)
├── requirements.txt ← Python dependencies
├── .env ← Model + DB credentials
└── README.md


## 🛠 How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Streamlit app
streamlit run app/dashboard.py

🔐 Authentication (coming soon)
Add password login or role-based access using streamlit-authenticator or move to Next.js + next-auth.

📦 Tech Stack
Python, LangChain, Ollama, PostgreSQL

Streamlit (UI), Plotly (visuals)

CrewAI (modular agent flow)

🧪 Status
✅ Fully functional backend
🟢 Frontend migration to Next.js in progress

✍️ Author
Raja Vamsi Krishna Amjala
🚀 Built under V-Soft Consulting | MIT License


---

Let me know when you'd like to commit and push this to GitHub — I’ll walk you through the commands again if needed.
