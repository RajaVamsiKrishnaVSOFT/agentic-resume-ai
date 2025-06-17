# ✅ FIXED: cleaner_agent.py with proper chain.invoke()['text'] handling

import logging
from functools import lru_cache
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——— INIT LLM ———————————————————————————————————————————————
llm = Ollama(model=LLM_MODEL, temperature=0)

# ——— PROMPT (only return the cleaned text) —————————————————————
prompt = PromptTemplate(
    input_variables=["raw_text"],
    template="""
You are a resume‐cleaning assistant. Given the raw resume text below, produce **only** the cleaned resume:

• Remove irrelevant boilerplate (e.g. “References available on request”)  
• Standardize bullets to “- ” at the start of each line  
• Normalize whitespace (single blank line between sections)  
• Preserve all contact details, headings, and dates  
• Do not add or change any content  

Raw Resume:
{raw_text}

===OUTPUT ONLY THE CLEANED TEXT BELOW===  
"""
)

chain = LLMChain(llm=llm, prompt=prompt)

@lru_cache(maxsize=128)
def _clean(raw_text: str) -> str:
    try:
        return chain.invoke({"raw_text": raw_text})["text"].strip()
    except Exception as e:
        logger.exception("❌ Cleaning failed")
        return raw_text

def run_cleaning_agent(raw_text: str) -> str:
    """
    Cleans the given raw resume text and returns the cleaned version.
    Uses an LRU cache so repeated calls with the same text are instant.
    """
    return _clean(raw_text)

# alias for backwards compatibility
run_cleaner_agent = run_cleaning_agent
