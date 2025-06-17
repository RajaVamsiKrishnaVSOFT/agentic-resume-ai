# ✅ UPDATED: classifier_agent.py with dynamic model config and error handling

import json
import logging
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = Ollama(model=LLM_MODEL, temperature=0)

# ——— Career Stage Classifier ————————————————————————————————————————
stage_prompt = PromptTemplate(
    input_variables=["text"],
    template="""
You are an AI assistant that classifies career stages.
Given the resume text below, return *only* one of:
  - Entry-level
  - Mid-level
  - Senior-level

Resume:
{text}
"""
)
stage_chain = LLMChain(llm=llm, prompt=stage_prompt)

def classify_career_stage(cleaned_text: str) -> str:
    try:
        label = stage_chain.invoke({"text": cleaned_text})["text"].strip()
        return label if label in ["Entry-level", "Mid-level", "Senior-level"] else "Unknown"
    except Exception as e:
        logger.exception("❌ Career stage classification error")
        return "Unknown"

# ——— Skills Splitter ————————————————————————————————————————————————
skill_prompt = PromptTemplate(
    input_variables=["skills_text"],
    template="""
You are an AI assistant that splits skills lists.
Given this comma- or newline-separated list of skills, split them into two categories:
  • hard_skills (technical/programming skills)  
  • soft_skills (communication, teamwork, leadership, etc.)

Return *only* a JSON object with exactly two keys: "hard_skills" and "soft_skills", each an array of strings.

Skills:
{skills_text}
"""
)
skill_chain = LLMChain(llm=llm, prompt=skill_prompt)

def classify_skills(skills_text: str) -> dict:
    try:
        raw = skill_chain.invoke({"skills_text": skills_text})["text"].strip()
        parsed = json.loads(raw)
        return {
            "hard_skills": parsed.get("hard_skills", []),
            "soft_skills": parsed.get("soft_skills", [])
        }
    except Exception as e:
        logger.exception("❌ Skills classification error")
        return {"hard_skills": [], "soft_skills": []}

# ——— Aliases for backward compatibility ———————————————————————————————
run_classification_agent       = classify_career_stage
run_skill_classification_agent = classify_skills