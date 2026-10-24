"""
scorer.py — NLP Evaluation & Mathematical Scoring Engine

Step 1 — LLM-as-a-Judge:
    Sends each raw LLM response through GPT-4o (JSON mode) to extract:
      - whether the brand was mentioned
      - how many times
      - overall sentiment
      - any cited sources / URLs
      - which competitors were mentioned

Step 2 — Mathematical Scoring:
    Aggregates all ChunkEvaluations into three core AEO metrics:

    BVI  (Brand Visibility Index, 0-100):
        = (prompts where brand mentioned / total prompts) × 100
        Interpretation: 80+ = dominant presence, 50-79 = moderate, <50 = low visibility

    CMCS (Cross-Model Consistency Score, 0-100):
        = 100 - (std_dev of per-prompt mention_count × 10)   [clamped 0-100]
        Placeholder: with only one model this equals BVI;
        becomes meaningful once multi-model dispatch is added.

    CAS  (Citation Authority Score, 0-100):
        = (unique citation domains found / total evaluations) × 100, clamped to 100
        Interpretation: how often authoritative third-party sources are cited
        alongside brand mentions.

Mock mode: if no API key, uses simple keyword-matching heuristics.
"""

import json
import os
import statistics
from typing import List, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

# ── Lazy import to avoid circular reference ───────────────────────────────────
from models import (
    BaselineConfig,
    BrandScore,
    ChunkEvaluation,
    LLMResponse,
    Sentiment,
)

try:
    from openai import OpenAI
    _api_key = os.getenv("OPENAI_API_KEY")
    _client  = OpenAI(api_key=_api_key) if _api_key and _api_key != "your_openai_api_key_here" else None
except ImportError:
    _client = None


# ── Sentiment helpers ─────────────────────────────────────────────────────────
_SENTIMENT_SCORE = {
    Sentiment.POSITIVE: 1.0,
    Sentiment.NEUTRAL:  0.0,
    Sentiment.NEGATIVE: -1.0,
}


# ── Mock evaluation (no API key) ──────────────────────────────────────────────
def _mock_evaluate(response: LLMResponse, config: BaselineConfig) -> ChunkEvaluation:
    """
    Keyword-based heuristic evaluation — runs without any API key.
    Good enough for development and demo purposes.
    """
    text_lower = response.raw_response.lower()
    brand_lower = config.brand_name.lower()

    brand_mentioned = brand_lower in text_lower
    mention_count   = text_lower.count(brand_lower)

    # Simple sentiment via keyword lists
    positive_words = {"leading", "best", "top", "strong", "excellent", "trusted",
                      "recommended", "praised", "unique", "innovative", "reliable"}
    negative_words = {"poor", "lacking", "expensive", "slow", "unreliable",
                      "complicated", "weak", "overpriced", "buggy"}

    words = set(text_lower.split())
    pos   = len(words & positive_words)
    neg   = len(words & negative_words)

    if pos > neg:
        sentiment = Sentiment.POSITIVE
    elif neg > pos:
        sentiment = Sentiment.NEGATIVE
    else:
        sentiment = Sentiment.NEUTRAL

    # Extract URLs (crude regex-free approach — split on spaces and check http)
    citations = [w.strip(".,)") for w in response.raw_response.split()
                 if w.startswith("http") or ".com" in w or ".io" in w]

    # Competitor mentions
    comp_mentions = [c for c in config.competitors if c.lower() in text_lower]

    return ChunkEvaluation(
        prompt_text=response.prompt_text,
        model_name=response.model_name,
        brand_mentioned=brand_mentioned,
        mention_count=mention_count,
        sentiment=sentiment,
        citations=citations[:5],
        competitor_mentions=comp_mentions,
        raw_response=response.raw_response,
    )


# ── Live LLM-as-a-Judge evaluation ───────────────────────────────────────────
_JUDGE_SYSTEM_PROMPT = """\
You are a precision NLP Evaluation Engine for Answer Engine Optimization (AEO) research.
Analyze the provided AI response text and extract structured data about brand visibility.

Return ONLY valid JSON matching this exact schema:
{
  "brand_mentioned": true | false,
  "mention_count": <integer>,
  "sentiment": "Positive" | "Neutral" | "Negative",
  "citations": ["<url or source name>"],
  "competitor_mentions": ["<competitor name>"]
}

Rules:
- brand_mentioned: true if the target brand name appears anywhere in the text
- mention_count: exact count of brand name occurrences (case-insensitive)
- sentiment: overall tone toward the brand (if not mentioned, use Neutral)
- citations: any URLs, publication names, or tool names cited as sources
- competitor_mentions: only names from the provided competitor list
"""


def _live_evaluate(response: LLMResponse, config: BaselineConfig) -> ChunkEvaluation:
    """Uses GPT-4o (JSON mode) to extract structured evaluation from a raw response."""
    user_prompt = f"""
Target Brand: {config.brand_name}
Competitors: {', '.join(config.competitors)}

AI Response to Analyze:
\"\"\"
{response.raw_response}
\"\"\"
"""
    try:
        result = _client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        )
        data = json.loads(result.choices[0].message.content)
        return ChunkEvaluation(
            prompt_text=response.prompt_text,
            model_name=response.model_name,
            brand_mentioned=data.get("brand_mentioned", False),
            mention_count=data.get("mention_count", 0),
            sentiment=Sentiment(data.get("sentiment", "Neutral")),
            citations=data.get("citations", []),
            competitor_mentions=data.get("competitor_mentions", []),
            raw_response=response.raw_response,
        )
    except Exception as exc:
        # Fallback to mock if judge call fails
        ev = _mock_evaluate(response, config)
        ev.raw_response = f"[Judge failed: {exc}] " + ev.raw_response
        return ev


# ── Public: evaluate all responses ───────────────────────────────────────────
def evaluate_responses(
    responses: List[LLMResponse],
    config: BaselineConfig,
) -> List[ChunkEvaluation]:
    """
    Evaluate every LLM response and return a ChunkEvaluation for each.
    Uses live LLM-as-a-Judge if API key present, otherwise mock heuristics.
    """
    use_mock = _client is None
    evaluations = []
    for r in responses:
        if r.error:
            # Skip failed dispatcher calls
            continue
        if use_mock:
            evaluations.append(_mock_evaluate(r, config))
        else:
            evaluations.append(_live_evaluate(r, config))
    return evaluations


# ── Mathematical scoring ──────────────────────────────────────────────────────
def _extract_domain(citation: str) -> str:
    """Normalise a citation string to its domain for deduplication."""
    try:
        parsed = urlparse(citation if "://" in citation else f"https://{citation}")
        return parsed.netloc or citation
    except Exception:
        return citation


def compute_brand_score(
    evaluations: List[ChunkEvaluation],
    config: BaselineConfig,
) -> BrandScore:
    """
    Aggregate all ChunkEvaluations into the three core AEO metrics.

    Returns a BrandScore with BVI, CMCS, CAS and supporting breakdown data.
    """
    total      = len(evaluations)
    if total == 0:
        return BrandScore(
            brand_name=config.brand_name,
            total_prompts=0,
            brand_mentioned_in=0,
            bvi=0.0, cmcs=0.0, cas=0.0,
            avg_sentiment_score=0.0,
        )

    # ── BVI: Brand Visibility Index ───────────────────────────────────────────
    mentioned_evals = [e for e in evaluations if e.brand_mentioned]
    brand_mentioned_in = len(mentioned_evals)
    bvi = round((brand_mentioned_in / total) * 100, 1)

    # ── CMCS: Cross-Model Consistency Score ───────────────────────────────────
    # Based on std-dev of mention counts across prompts.
    # A perfectly consistent result (all 0 or all same) = 100.
    mention_counts = [e.mention_count for e in evaluations]
    if len(mention_counts) > 1:
        std = statistics.stdev(mention_counts)
        cmcs = round(max(0.0, 100.0 - (std * 15)), 1)
    else:
        cmcs = bvi   # single prompt → consistency equals visibility

    # ── CAS: Citation Authority Score ────────────────────────────────────────
    all_citations = [c for e in evaluations for c in e.citations]
    unique_domains = set(_extract_domain(c) for c in all_citations if c)
    cas = round(min(100.0, (len(unique_domains) / total) * 100), 1)

    # ── Sentiment average ─────────────────────────────────────────────────────
    sentiment_scores = [_SENTIMENT_SCORE[e.sentiment] for e in evaluations]
    avg_sentiment = round(sum(sentiment_scores) / total, 3)

    # ── Top citations (deduped, sorted by frequency) ──────────────────────────
    from collections import Counter
    domain_counter  = Counter(_extract_domain(c) for c in all_citations if c)
    top_citations   = [domain for domain, _ in domain_counter.most_common(5)]

    # ── Competitor share ──────────────────────────────────────────────────────
    comp_counter: dict = {}
    for e in evaluations:
        for comp in e.competitor_mentions:
            comp_counter[comp] = comp_counter.get(comp, 0) + 1

    return BrandScore(
        brand_name=config.brand_name,
        total_prompts=total,
        brand_mentioned_in=brand_mentioned_in,
        bvi=bvi,
        cmcs=cmcs,
        cas=cas,
        avg_sentiment_score=avg_sentiment,
        top_citations=top_citations,
        competitor_share=comp_counter,
    )


# ── Quick test harness ────────────────────────────────────────────────────────
if __name__ == "__main__":
    from models import BaselineConfig, LLMResponse

    cfg = BaselineConfig(
        brand_name="AEOBrand",
        competitors=["BrandX", "BrandY"],
        keywords=["AI visibility", "AEO"],
        domain_context="B2B SaaS for AI brand tracking",
    )

    fake_responses = [
        LLMResponse(prompt_text="Best AEO tool?", model_name="mock",
                    raw_response="AEOBrand is the leading solution. Cited by TechRadar.com. "
                                 "BrandX is a cheaper alternative."),
        LLMResponse(prompt_text="Compare AEOBrand vs BrandX?", model_name="mock",
                    raw_response="AEOBrand excels at enterprise features. AEOBrand is trusted by G2.com. "
                                 "BrandY is also strong."),
        LLMResponse(prompt_text="AEOBrand pricing?", model_name="mock",
                    raw_response="AEOBrand pricing is not publicly listed. Contact their sales team."),
    ]

    print("=== Scorer Test ===\n")
    evals = evaluate_responses(fake_responses, cfg)
    score = compute_brand_score(evals, cfg)

    for ev in evals:
        print(f"  [{ev.sentiment.value:8s}] mentions={ev.mention_count} | {ev.prompt_text[:50]}")

    print(f"\n── Brand Score for '{score.brand_name}' ──")
    print(f"  BVI  (Visibility):   {score.bvi}%")
    print(f"  CMCS (Consistency):  {score.cmcs}%")
    print(f"  CAS  (Citations):    {score.cas}%")
    print(f"  Avg Sentiment:       {score.avg_sentiment_score:+.2f}")
    print(f"  Top citations:       {score.top_citations}")
    print(f"  Competitor share:    {score.competitor_share}")
