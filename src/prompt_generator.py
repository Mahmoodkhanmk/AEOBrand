import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from models import BaselineConfig, SyntheticPromptCollection

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

# Initialize OpenAI Client (will pick up OPENAI_API_KEY from env automatically)
# We handle the case where it might be None for safe fallback testing
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

def generate_synthetic_prompts(config: BaselineConfig, num_prompts: int = 10) -> SyntheticPromptCollection:
    """
    Calls the LLM to dynamically generate semantic prompt permutations 
    based on the baseline configuration.
    """
    if not client:
        raise ValueError("OPENAI_API_KEY is not set. Please set it in your .env file.")

    system_prompt = f"""
    You are an expert Synthetic Data Generator for an Answer Engine Optimization (AEO) system.
    Your task is to generate realistic, user-intent search queries that consumers might ask Large Language Models 
    (like ChatGPT, Gemini) regarding the following domain.
    
    Domain Context: {config.domain_context}
    Target Brand: {config.brand_name}
    Competitors: {', '.join(config.competitors)}
    Keywords: {', '.join(config.keywords)}
    
    Generate {num_prompts} varied prompts. Ensure a mix of:
    - Informational (e.g., "What are the best tools for X?")
    - Comparative (e.g., "Compare [Brand] and [Competitor]")
    - Transactional (e.g., "How much does [Brand] cost for enterprise?")
    
    You must return the result as a STRICTLY formatted JSON adhering to the following schema:
    {{
        "prompts": [
            {{
                "intent_category": "Informational | Comparative | Transactional",
                "prompt_text": "The generated prompt question"
            }}
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please generate the synthetic prompts."}
        ]
    )
    
    result_json = response.choices[0].message.content
    data = json.loads(result_json)
    
    # Validate and parse into Pydantic models
    return SyntheticPromptCollection(**data)

def mock_generate_prompts(config: BaselineConfig) -> SyntheticPromptCollection:
    """Fallback generator for local testing without an API key."""
    return SyntheticPromptCollection(prompts=[
        {"intent_category": "Informational", "prompt_text": f"What is the best way to handle {config.keywords[0]}?"},
        {"intent_category": "Comparative", "prompt_text": f"How does {config.brand_name} compare to {config.competitors[0]}?"},
        {"intent_category": "Transactional", "prompt_text": f"Where can I buy {config.brand_name} software?"},
        {"intent_category": "Informational", "prompt_text": f"Top tools for {config.domain_context}"},
        {"intent_category": "Comparative", "prompt_text": f"Is {config.brand_name} better than {config.competitors[1]} for {config.keywords[1]}?"}
    ])

if __name__ == "__main__":
    # Example usage / Test harness
    test_config = BaselineConfig(
        brand_name="AEOBrand",
        competitors=["BrandX", "BrandY"],
        keywords=["Enterprise AI Visibility", "Answer Engine Optimization", "LLM Analytics"],
        domain_context="B2B SaaS platform for tracking brand representation across generative AI search engines."
    )
    
    print("--- Starting Prompt Synthesis ---")
    if os.getenv("OPENAI_API_KEY"):
        print("API Key found. Generating real semantic permutations...")
        try:
            collection = generate_synthetic_prompts(test_config, num_prompts=5)
            for i, p in enumerate(collection.prompts, 1):
                print(f"{i}. [{p.intent_category}] {p.prompt_text}")
        except Exception as e:
            print(f"Error during generation: {e}")
    else:
        print("No OPENAI_API_KEY found. Using mock generator for demonstration...")
        collection = mock_generate_prompts(test_config)
        for i, p in enumerate(collection.prompts, 1):
            print(f"{i}. [{p.intent_category}] {p.prompt_text}")
        
        print("\n[!] To use the real LLM, create a .env file and add your OPENAI_API_KEY.")
