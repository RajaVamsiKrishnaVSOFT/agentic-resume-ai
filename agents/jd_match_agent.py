# agents/jd_match_agent.py
import logging
from langchain.chains import LLMChain
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = Ollama(model=LLM_MODEL, temperature=0)

match_prompt = PromptTemplate(
    input_variables=["resume_text", "job_description"],
    template="""
You are a smart assistant that compares a candidate resume to a job description.
Return only a number between 0 and 100 that reflects how well the candidate matches the job (0 = no match, 100 = perfect match).

Job Description:
{job_description}

Candidate Resume:
{resume_text}

Match Score (0-100):
"""
)

chain = LLMChain(llm=llm, prompt=match_prompt)

def match_to_job_description(resume_text: str, job_description: str) -> float:
    try:
        response = chain.invoke({
            "resume_text": resume_text,
            "job_description": job_description
        })["text"].strip()
        return float(response)
    except Exception as e:
        logger.error(f"❌ JD Match error: {e}")
        return 0.0