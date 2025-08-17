import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

# Use OpenAI if key exists, else None (fallback to rules)

def get_llm() -> Optional[BaseChatModel]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    from langchain_openai import ChatOpenAI
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0.2)

root_cause_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an SRE. Given an ITOps event and past cases, produce a concise root cause hypothesis and first remediation step."),
    ("user", "Event: {event}\nSimilarCases: {similar}\nRespond in two sentences."),
])
