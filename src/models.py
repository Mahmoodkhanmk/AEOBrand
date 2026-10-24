"""
models.py — All Pydantic schema definitions for AEOBrand pipeline.

Schemas flow through the pipeline in this order:
  BaselineConfig → SyntheticPromptCollection → LLMResponse
  → ChunkEvaluation → BrandScore → RunReport
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class IntentCategory(str, Enum):
    INFORMATIONAL = "Informational"
    COMPARATIVE   = "Comparative"
    TRANSACTIONAL = "Transactional"

class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL  = "Neutral"
    NEGATIVE = "Negative"


# ── Phase 1: Input Configuration ─────────────────────────────────────────────

class BaselineConfig(BaseModel):
    """User-supplied brand configuration — the starting point for every run."""
    brand_name:     str
    competitors:    List[str]
    keywords:       List[str]
    domain_context: str

class SyntheticPrompt(BaseModel):
    """A single generated test query."""
    intent_category: IntentCategory
    prompt_text:     str

class SyntheticPromptCollection(BaseModel):
    """Container for all generated prompts in one batch."""
    prompts: List[SyntheticPrompt]


# ── Phase 2: LLM Dispatch ─────────────────────────────────────────────────────

class LLMResponse(BaseModel):
    """Raw response captured from a single LLM call."""
    prompt_text:    str
    model_name:     str                  # e.g. "gpt-4o", "claude-3", "mock"
    raw_response:   str
    latency_ms:     Optional[float] = None
    prompt_tokens:  Optional[int]   = None
    response_tokens: Optional[int]  = None
    error:          Optional[str]   = None   # set if the call failed


# ── Phase 3: NLP Evaluation ───────────────────────────────────────────────────

class ChunkEvaluation(BaseModel):
    """
    Structured output from the LLM-as-a-Judge analysis of one response.
    Captures brand presence, sentiment, and citation evidence.
    """
    prompt_text:      str
    model_name:       str
    brand_mentioned:  bool
    mention_count:    int                    = 0
    sentiment:        Sentiment              = Sentiment.NEUTRAL
    citations:        List[str]              = Field(default_factory=list)
    competitor_mentions: List[str]           = Field(default_factory=list)
    raw_response:     str                    = ""

class BrandScore(BaseModel):
    """
    The three core AEO metrics computed from a full batch of evaluations.

    BVI  — Brand Visibility Index      (0-100): share of voice across all prompts
    CMCS — Cross-Model Consistency Score (0-100): uniformity across LLMs (placeholder for multi-model)
    CAS  — Citation Authority Score    (0-100): weighted citation quality
    """
    brand_name:          str
    total_prompts:       int
    brand_mentioned_in:  int
    bvi:                 float   # Brand Visibility Index
    cmcs:                float   # Cross-Model Consistency Score
    cas:                 float   # Citation Authority Score
    avg_sentiment_score: float   # -1 (all negative) → +1 (all positive)
    top_citations:       List[str] = Field(default_factory=list)
    competitor_share:    dict     = Field(default_factory=dict)  # {competitor: mention_count}


# ── Phase 4: Final Report ─────────────────────────────────────────────────────

class RunReport(BaseModel):
    """
    Complete output of one full pipeline run.
    Saved as a timestamped JSON file in reports/.
    """
    run_id:       str
    timestamp:    str
    config:       BaselineConfig
    prompts_used: List[SyntheticPrompt]
    evaluations:  List[ChunkEvaluation]
    score:        BrandScore
