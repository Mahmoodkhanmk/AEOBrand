from pydantic import BaseModel
from typing import List

class BaselineConfig(BaseModel):
    brand_name: str
    competitors: List[str]
    keywords: List[str]
    domain_context: str

class SyntheticPrompt(BaseModel):
    intent_category: str  # e.g., Informational, Comparative, Transactional
    prompt_text: str

class SyntheticPromptCollection(BaseModel):
    prompts: List[SyntheticPrompt]
