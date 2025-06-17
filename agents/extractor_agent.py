import json
import logging
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import LLMChain
from config.settings import LLM_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize your LLM
llm = Ollama(model=LLM_MODEL, temperature=0)

# 1. Prompt that explicitly asks for every field
prompt_template = PromptTemplate(
    input_variables=["cleaned_text"],
    template="""
You are an expert resume parser. Given the cleaned resume text below, extract exactly the following fields and return them as a JSON object:

- name            : Full name  
- email           : Email address  
- phone           : Phone number  
- location        : Current location  
- education       : Education details  
- skills          : Comma-separated list of skills  
- companies       : Comma-separated list of past employers  
- job_titles      : Comma-separated list of job titles held  
- project_titles  : Comma-separated list of project titles  
- project_links   : Comma-separated list of project URLs  

If any field is absent, return it as an empty string (or empty list for multi-value fields).  
Return *only* the JSON object—no extra commentary.

Resume Text:
{cleaned_text}
"""
)

chain = LLMChain(llm=llm, prompt=prompt_template)

# 2. Default values for any missing keys
required_fields = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "education": "",
    "skills": "",
    "companies": "",
    "job_titles": "",
    "project_titles": "",
    "project_links": ""
}

def run_extraction_agent(cleaned_text: str) -> dict:
    try:
        response = chain.invoke({"cleaned_text": cleaned_text})["text"].strip()
        parsed = json.loads(response)
    except Exception as e:
        logger.exception("❌ Extraction error")
        parsed = {}

    for key, default in required_fields.items():
        parsed.setdefault(key, default)

    # Normalize lists to comma-separated strings
    for key in ["skills", "companies", "job_titles", "project_titles", "project_links"]:
        value = parsed.get(key, "")
        if isinstance(value, list):
            parsed[key] = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            parsed[key] = ", ".join(f"{k}: {v}" for k, v in value.items())
        elif isinstance(value, (set, tuple)):
            parsed[key] = ", ".join(str(v) for v in list(value))

    logger.info(f"✅ Extracted: {parsed}")
    return parsed
