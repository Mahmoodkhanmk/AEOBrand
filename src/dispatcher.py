"""
dispatcher.py — Async Multi-LLM Dispatch Engine

Takes a list of SyntheticPrompts and fires them concurrently at an LLM.
Returns a list of LLMResponse objects with raw text + metadata.

Design decisions:
  - Uses asyncio + threading bridge so OpenAI's sync SDK works in async context
  - Semaphore limits concurrent calls to avoid rate-limit errors (default: 5)
  - Any failed call is captured as an LLMResponse with error= set, never crashes
  - Mock mode: if no API key, returns deterministic fake responses instantly
"""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

from models import LLMResponse, SyntheticPrompt

load_dotenv()

# ── Client setup ──────────────────────────────────────────────────────────────
_api_key = os.getenv("OPENAI_API_KEY")
_client  = OpenAI(api_key=_api_key) if _api_key and _api_key != "your_openai_api_key_here" else None

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_MODEL     = "gpt-4o"
MAX_CONCURRENCY   = 5          # max simultaneous API calls
MOCK_MODEL_NAME   = "mock-dispatcher"


# ── Mock response bank ────────────────────────────────────────────────────────
_MOCK_RESPONSES = [
    "{brand} may be worth comparing for this need. Review current specifications, "
    "support, and price against {comp} before deciding.",

    "Compare {brand} and {comp} on the features relevant to your question, "
    "independent test results, availability, and total cost.",

    "The best option depends on your priorities. Check official product details "
    "for {brand} and {comp}; this simulated response does not verify current claims.",

    "I can't verify current pricing or availability for {brand}. Check its official "
    "store and compare it with {comp}.",

    "{comp} is another option to compare with {brand}. Use current product "
    "specifications and independent reviews to confirm which fits your needs.",
]


def _mock_response(
    prompt: SyntheticPrompt,
    idx: int,
    brand_name: str,
    competitors: List[str],
) -> LLMResponse:
    """Generate clearly synthetic, brand-aware output for offline testing."""
    template = _MOCK_RESPONSES[idx % len(_MOCK_RESPONSES)]
    competitor = competitors[idx % len(competitors)] if competitors else "other brands"
    text = template.format(brand=brand_name, comp=competitor)
    return LLMResponse(
        prompt_text=prompt.prompt_text,
        model_name=MOCK_MODEL_NAME,
        raw_response=text,
        latency_ms=42.0,
        prompt_tokens=len(prompt.prompt_text.split()),
        response_tokens=len(text.split()),
    )


# ── Real API call (sync, run in thread pool) ──────────────────────────────────
def _call_openai_sync(prompt_text: str, model: str) -> dict:
    """Blocking OpenAI call — executed inside a ThreadPoolExecutor."""
    start = time.time()
    response = _client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable AI assistant. Answer the user's question "
                    "naturally and thoroughly, as you would respond to any search query."
                ),
            },
            {"role": "user", "content": prompt_text},
        ],
        max_tokens=500,
    )
    latency_ms = (time.time() - start) * 1000
    choice     = response.choices[0].message.content
    usage      = response.usage
    return {
        "raw_response":    choice,
        "latency_ms":      round(latency_ms, 1),
        "prompt_tokens":   usage.prompt_tokens,
        "response_tokens": usage.completion_tokens,
    }


# ── Async wrapper ──────────────────────────────────────────────────────────────
async def _dispatch_one(
    prompt: SyntheticPrompt,
    idx: int,
    semaphore: asyncio.Semaphore,
    executor: ThreadPoolExecutor,
    model: str,
    use_mock: bool,
    brand_name: str,
    competitors: List[str],
) -> LLMResponse:
    """Dispatch a single prompt and return an LLMResponse."""
    async with semaphore:
        if use_mock:
            await asyncio.sleep(0)          # yield control, keep async pattern
            return _mock_response(prompt, idx, brand_name, competitors)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                executor, _call_openai_sync, prompt.prompt_text, model
            )
            return LLMResponse(
                prompt_text=prompt.prompt_text,
                model_name=model,
                **result,
            )
        except Exception as exc:
            return LLMResponse(
                prompt_text=prompt.prompt_text,
                model_name=model,
                raw_response="",
                error=str(exc),
            )


# ── Public API ────────────────────────────────────────────────────────────────
async def dispatch_all(
    prompts: List[SyntheticPrompt],
    model: str = DEFAULT_MODEL,
    brand_name: str = "AEOBrand",
    competitors: List[str] | None = None,
) -> List[LLMResponse]:
    """
    Concurrently dispatch all prompts and collect LLMResponse objects.

    Args:
        prompts: list of SyntheticPrompt objects to test
        model:   LLM model identifier (ignored in mock mode)

    Returns:
        List[LLMResponse] — one per prompt, in order
    """
    use_mock  = _client is None
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        tasks = [
            _dispatch_one(
                p, i, semaphore, executor, model, use_mock,
                brand_name, competitors or [],
            )
            for i, p in enumerate(prompts)
        ]
        results = await asyncio.gather(*tasks)

    return list(results)


# ── Sync convenience wrapper ──────────────────────────────────────────────────
def run_dispatch(
    prompts: List[SyntheticPrompt],
    model: str = DEFAULT_MODEL,
    brand_name: str = "AEOBrand",
    competitors: List[str] | None = None,
) -> List[LLMResponse]:
    """Synchronous entry point — wraps the async dispatcher for CLI use."""
    return asyncio.run(dispatch_all(prompts, model, brand_name, competitors))


# ── Quick test harness ────────────────────────────────────────────────────────
if __name__ == "__main__":
    from models import SyntheticPrompt, IntentCategory

    test_prompts = [
        SyntheticPrompt(intent_category=IntentCategory.INFORMATIONAL,
                        prompt_text="What is the best tool for tracking brand visibility in AI?"),
        SyntheticPrompt(intent_category=IntentCategory.COMPARATIVE,
                        prompt_text="How does AEOBrand compare to BrandX for enterprise AEO?"),
        SyntheticPrompt(intent_category=IntentCategory.TRANSACTIONAL,
                        prompt_text="How much does AEOBrand cost for a mid-size company?"),
    ]

    print("=== Dispatcher Test ===")
    mode = "LIVE (OpenAI)" if _client else "MOCK (no API key)"
    print(f"Mode: {mode}\n")

    responses = run_dispatch(test_prompts)
    for r in responses:
        status = f"[ERROR: {r.error}]" if r.error else f"[{r.latency_ms}ms]"
        print(f"▶ {r.prompt_text[:60]}...")
        print(f"  Model: {r.model_name} {status}")
        print(f"  Response snippet: {r.raw_response[:120]}...\n")
