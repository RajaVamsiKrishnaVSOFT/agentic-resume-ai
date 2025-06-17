# ✅ UPDATED: sustainability_agent.py with dynamic model config and robust fallback

import logging
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = Ollama(model=LLM_MODEL, temperature=0)

prompt = PromptTemplate(
    input_variables=["text"],
    template="""
You are an AI assistant specializing in sustainable hiring decisions.

Given the cleaned resume text below, assign only one integer score between 1 and 10,
based on how well the candidate aligns with long-term sustainable hiring principles
such as skill relevance, potential growth, adaptability, and cultural fit.

Return ONLY a single integer (1 to 10) on the first line, with NO explanation or commentary.

Resume:
{text}

=== OUTPUT A SINGLE INTEGER BELOW ===
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

def assess_sustainability(cleaned_text: str) -> int:
    """
    Returns an integer score 1–10. If the model outputs explanation text,
    fallback logic parses only the first line and ensures it's numeric.
    """
    try:
        raw = chain.invoke({"text": cleaned_text})["text"].strip()
        first_line = raw.splitlines()[0].strip()
        score = int(first_line)
        if not (1 <= score <= 10):
            logger.warning(f"Returned score {score} out of range; clamping to 1–10")
            return 0
        return score
    except Exception as e:
        logger.exception("❌ Sustainability scoring error")
        return 0

# Alias for use in pipeline/backfill
run_sustainability_agent = assess_sustainability
