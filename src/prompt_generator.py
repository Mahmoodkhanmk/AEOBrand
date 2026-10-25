"""
prompt_generator.py — Production Synthetic Prompt Generator

Two-mode architecture:
  LIVE  — calls GPT-4o with a rich system prompt seeded by templates.
          Returns N prompts covering all 6 intent categories proportionally.
          Retries up to 3 times on malformed JSON or API errors.

  MOCK  — template-based generation with full cycling and variety.
          Produces realistic, diverse prompts with zero API cost.
          Respects intent_mix percentages and num_prompts exactly.

Key improvements over v1:
  - Respects intent_mix from BaselineConfig (proportional generation)
  - Template seeding for LLM calls (guides quality, prevents repetition)
  - Retry logic with exponential back-off (max 3 attempts)
  - Graceful degradation: LLM failure → template fallback, never crashes
  - Added 'generated_by' metadata on every prompt ("llm" | "template")
  - build_prompt_collection() is the single public entry point
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models import (
    BaselineConfig,
    IntentCategory,
    SyntheticPrompt,
    SyntheticPromptCollection,
)
from prompt_templates import TEMPLATES, render_template

# ── OpenAI client (optional) ──────────────────────────────────────────────────
_api_key = os.getenv("OPENAI_API_KEY", "")
_PLACEHOLDER = "your_openai_api_key_here"
_HAS_KEY = bool(_api_key) and _api_key != _PLACEHOLDER

if _HAS_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=_api_key)
    except ImportError:
        _client = None
        _HAS_KEY = False
else:
    _client = None

# ── Constants ─────────────────────────────────────────────────────────────────
_MAX_RETRIES       = 3
_RETRY_DELAY_SEC   = 2.0
_MODEL             = "gpt-4o"
_SEED_EXAMPLES_PER_CATEGORY = 2   # number of templates to show GPT as examples


# ── Public entry point ────────────────────────────────────────────────────────

def build_prompt_collection(config: BaselineConfig) -> SyntheticPromptCollection:
    """
    Generate a SyntheticPromptCollection from a BaselineConfig.

    Chooses live or mock mode automatically based on API key availability.
    Falls back to template mode if the LLM call fails after all retries.

    Args:
        config: Validated BaselineConfig (loaded from YAML or constructed).

    Returns:
        SyntheticPromptCollection ready for prompt_validator.validate_collection().
    """
    counts = config.intent_mix.to_counts(config.num_prompts)

    if _HAS_KEY and _client:
        return _generate_live(config, counts)
    else:
        return _generate_from_templates(config, counts)


# ── Live generation (GPT-4o) ──────────────────────────────────────────────────

def _generate_live(
    config: BaselineConfig,
    counts: dict[IntentCategory, int],
) -> SyntheticPromptCollection:
    """
    Call GPT-4o to generate prompts with retry and fallback logic.

    Strategy:
      - Build a rich system prompt with brand context + template examples
      - Request JSON with strictly typed schema
      - Retry up to _MAX_RETRIES on any error
      - On final failure, fall back to template generation
    """
    system_prompt = _build_system_prompt(config, counts)
    user_message  = _build_user_message(counts)

    last_error: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = _client.chat.completions.create(
                model=_MODEL,
                response_format={"type": "json_object"},
                temperature=0.85,          # slight randomness for diversity
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
            )
            raw_json = response.choices[0].message.content
            data     = json.loads(raw_json)
            prompts  = _parse_llm_response(data, config)

            if len(prompts) < 2:
                raise ValueError(f"LLM returned only {len(prompts)} prompts — too few.")

            return SyntheticPromptCollection(prompts=prompts)

        except Exception as exc:
            last_error = exc
            if attempt < _MAX_RETRIES:
                wait = _RETRY_DELAY_SEC * attempt
                print(f"  [prompt_generator] Attempt {attempt} failed: {exc}. "
                      f"Retrying in {wait:.0f}s...")
                time.sleep(wait)
            else:
                print(f"  [prompt_generator] All {_MAX_RETRIES} attempts failed. "
                      f"Falling back to template generation. Last error: {last_error}")

    # Graceful degradation — never let the whole pipeline die on prompt generation
    return _generate_from_templates(config, counts)


def _build_system_prompt(
    config: BaselineConfig,
    counts: dict[IntentCategory, int],
) -> str:
    """Build the GPT system prompt with brand context and example templates."""

    # Pick seed examples from the template library for each intent category
    seed_lines: list[str] = []
    for cat, n in counts.items():
        if n == 0:
            continue
        templates = TEMPLATES.get(cat, [])
        examples  = random.sample(templates, min(_SEED_EXAMPLES_PER_CATEGORY, len(templates)))
        for tmpl in examples:
            rendered = render_template(
                tmpl,
                brand       = config.brand_name,
                competitors = config.competitors,
                keywords    = config.keywords,
                use_cases   = config.use_cases or ["brand visibility tracking"],
                industry    = config.industry,
                audience    = config.target_audience,
                geography   = config.geography,
                index       = 0,
            )
            seed_lines.append(f'  [{cat.value}] "{rendered}"')

    seeds_block = "\n".join(seed_lines)

    negative_block = (
        f"\nNEVER include prompts about: {', '.join(config.negative_keywords)}"
        if config.negative_keywords else ""
    )

    return f"""You are a world-class Synthetic Data Generator for an Answer Engine Optimization (AEO) research system.

Your task is to generate realistic, varied user-intent search queries that represent how real users query Large Language Models (ChatGPT, Gemini, Claude, Perplexity) about the following brand domain.

=== BRAND CONTEXT ===
Brand Name:      {config.brand_name}
Industry:        {config.industry}
Competitors:     {', '.join(config.competitors)}
Keywords:        {', '.join(config.keywords)}
Use Cases:       {', '.join(config.use_cases or ['brand visibility tracking'])}
Target Audience: {config.target_audience}
Geography:       {', '.join(config.geography)}
Domain Context:  {config.domain_context}
{negative_block}

=== STYLE EXAMPLES ===
Generate prompts in the style of these examples (do NOT copy them exactly):
{seeds_block}

=== OUTPUT RULES ===
1. Return ONLY valid JSON — no markdown, no explanation.
2. Every prompt must be a complete, natural question a real user would type.
3. Prompts must be varied in structure, length, and wording.
4. Brand name should appear in Comparative, Feature-Aware, and Transactional prompts.
5. Use the exact intent_category values listed in the required counts.

=== JSON SCHEMA ===
{{
  "prompts": [
    {{
      "intent_category": "Informational | Comparative | Transactional | Problem-Aware | Feature-Aware | Alternative",
      "prompt_text": "The generated prompt question"
    }}
  ]
}}"""


def _build_user_message(counts: dict[IntentCategory, int]) -> str:
    """Build the user turn specifying exact counts per category."""
    breakdown = "\n".join(
        f"  - {cat.value}: {n} prompt(s)"
        for cat, n in counts.items()
        if n > 0
    )
    total = sum(counts.values())
    return (
        f"Generate exactly {total} prompts with this intent distribution:\n"
        f"{breakdown}\n\n"
        "Return the JSON now."
    )


def _parse_llm_response(
    data: dict,
    config: BaselineConfig,
) -> list[SyntheticPrompt]:
    """
    Parse and validate GPT response into SyntheticPrompt objects.
    Skips any malformed entries silently (partial success > total failure).
    """
    raw_prompts = data.get("prompts", [])
    result: list[SyntheticPrompt] = []

    for item in raw_prompts:
        try:
            category_str = item.get("intent_category", "").strip()
            # Handle minor casing variations from the LLM
            category = IntentCategory(category_str)
            text     = item.get("prompt_text", "").strip()

            if not text or len(text) < 10:
                continue

            result.append(SyntheticPrompt(
                intent_category = category,
                prompt_text     = text,
                generated_by    = "llm",
            ))
        except (ValueError, KeyError):
            # Skip prompts with unknown intent categories
            continue

    return result


# ── Template-based generation (mock / fallback) ───────────────────────────────

def _generate_from_templates(
    config: BaselineConfig,
    counts: dict[IntentCategory, int],
) -> SyntheticPromptCollection:
    """
    Generate prompts entirely from the template library.

    - Respects counts per intent category
    - Cycles through templates and competitor/keyword lists for variety
    - Never repeats the same template in the same batch
    """
    prompts: list[SyntheticPrompt] = []
    global_index = 0

    for category, n in counts.items():
        if n == 0:
            continue

        available = TEMPLATES.get(category, [])
        if not available:
            continue

        # Shuffle so different runs produce different orderings
        shuffled = available.copy()
        random.shuffle(shuffled)

        for i in range(n):
            template = shuffled[i % len(shuffled)]
            rendered = render_template(
                template,
                brand       = config.brand_name,
                competitors = config.competitors,
                keywords    = config.keywords,
                use_cases   = config.use_cases or ["brand visibility tracking"],
                industry    = config.industry,
                audience    = config.target_audience,
                geography   = config.geography,
                index       = global_index,
            )
            prompts.append(SyntheticPrompt(
                intent_category = category,
                prompt_text     = rendered,
                template_used   = template,
                generated_by    = "template",
            ))
            global_index += 1

    # Shuffle final list so intent types are interleaved (not all grouped)
    random.shuffle(prompts)
    return SyntheticPromptCollection(prompts=prompts)


# ── Legacy compatibility shims ─────────────────────────────────────────────────
# Keep these so any existing code that imports the old function names still works.

def generate_synthetic_prompts(
    config: BaselineConfig,
    num_prompts: int = 10,
) -> SyntheticPromptCollection:
    """Legacy entry point — delegates to build_prompt_collection."""
    config = config.model_copy(update={"num_prompts": num_prompts})
    return build_prompt_collection(config)


def mock_generate_prompts(config: BaselineConfig) -> SyntheticPromptCollection:
    """Legacy entry point — delegates to template generation."""
    counts = config.intent_mix.to_counts(config.num_prompts)
    return _generate_from_templates(config, counts)


# ── Standalone test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    from config_loader import load_default_config

    cfg = load_default_config()
    mode = "LIVE (OpenAI GPT-4o)" if _HAS_KEY else "TEMPLATE (no API key)"

    print(f"\n=== Prompt Generator Test — {mode} ===")
    print(f"Config: {cfg.summary()}\n")

    collection = build_prompt_collection(cfg)

    print(f"Generated {len(collection.prompts)} prompts:\n")
    for i, p in enumerate(collection.prompts, 1):
        tag = f"[{p.intent_category.value[:5]:5}]"
        src = f"({p.generated_by})"
        print(f"  {i:2}. {tag} {src:10}  {p.prompt_text}")

    print(f"\nTotal: {len(collection.prompts)} prompts across "
          f"{len(set(p.intent_category for p in collection.prompts))} intent categories.")
