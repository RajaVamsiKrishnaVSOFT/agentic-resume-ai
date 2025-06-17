# ✅ UPDATED: internal_check_agent.py with dynamic model config and improved handling

import logging
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = Ollama(model=LLM_MODEL, temperature=0)

# ——— Internal vs External Classifier ——————————————————————————————————————
prompt = PromptTemplate(
    input_variables=["text"],
    template="""
You are an AI assistant that determines whether a candidate is
“Internal” (already at V-Soft Consulting if their e-mail contains @vsoftconsulting.com) or “External” (new to the company).
Return *only* the single word: Internal or External.

Resume:
{text}
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

def check_internal_candidate(cleaned_text: str) -> str:
    """
    Returns "Internal" if the candidate appears to be a current V-Soft employee,
    otherwise "External". Defaults to External on ambiguity or errors.
    """
    try:
        label = chain.invoke({"text": cleaned_text})["text"].strip()
        if label in ["Internal", "External"]:
            return label
        logger.warning(f"Unexpected label '{label}' — defaulting to External")
        return "External"
    except Exception as e:
        logger.exception("❌ Internal check error")
        return "External"

# Alias for backfill.py or legacy import
run_internal_check_agent = check_internal_candidate

