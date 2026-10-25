"""
models.py — All Pydantic schema definitions for AEOBrand pipeline.

Data flows through the pipeline in this order:
  BaselineConfig → SyntheticPromptCollection → LLMResponse
  → ChunkEvaluation → BrandScore → RunReport

Phase 1 deep-dive additions:
  - BaselineConfig: 8 new fields (industry, geography, product_lines,
                    use_cases, target_audience, num_prompts, intent_mix,
                    negative_keywords)
  - IntentCategory: 3 new enum values (Problem-Aware, Feature-Aware, Alternative)
  - SyntheticPrompt: added 'template_used' and 'diversity_score' metadata
  - PromptDiversityReport: new schema for prompt quality validation
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class IntentCategory(str, Enum):
    """
    Six intent types covering the full spectrum of how users query AI assistants.

    Informational  — seeking knowledge      "What is / How does / Why..."
    Comparative    — evaluating options     "X vs Y / Compare X and Y"
    Transactional  — action-oriented        "How to buy / pricing / demo"
    Problem-Aware  — pain-point led         "How do I solve / fix / handle..."
    Feature-Aware  — capability check       "Does X support / can X do..."
    Alternative    — replacement seeking    "Alternative to X / other options"
    """
    INFORMATIONAL = "Informational"
    COMPARATIVE   = "Comparative"
    TRANSACTIONAL = "Transactional"
    PROBLEM_AWARE = "Problem-Aware"
    FEATURE_AWARE = "Feature-Aware"
    ALTERNATIVE   = "Alternative"


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEUTRAL  = "Neutral"
    NEGATIVE = "Negative"


# ── Phase 1: Input Configuration ──────────────────────────────────────────────

class IntentMix(BaseModel):
    """
    Controls the percentage split of generated prompts across intent categories.
    Values must be integers summing to 100.
    """
    informational: int = Field(default=25, ge=0, le=100)
    comparative:   int = Field(default=25, ge=0, le=100)
    transactional: int = Field(default=15, ge=0, le=100)
    problem_aware: int = Field(default=15, ge=0, le=100)
    feature_aware: int = Field(default=10, ge=0, le=100)
    alternative:   int = Field(default=10, ge=0, le=100)

    @model_validator(mode="after")
    def check_sum_to_100(self) -> "IntentMix":
        total = (
            self.informational + self.comparative + self.transactional
            + self.problem_aware + self.feature_aware + self.alternative
        )
        if total != 100:
            raise ValueError(
                f"intent_mix percentages must sum to 100, got {total}. "
                f"Adjust the values so they add up to 100."
            )
        return self

    def to_counts(self, total: int) -> Dict[IntentCategory, int]:
        """Convert percentage mix into actual prompt counts for a given total."""
        counts = {
            IntentCategory.INFORMATIONAL: round(total * self.informational / 100),
            IntentCategory.COMPARATIVE:   round(total * self.comparative   / 100),
            IntentCategory.TRANSACTIONAL: round(total * self.transactional / 100),
            IntentCategory.PROBLEM_AWARE: round(total * self.problem_aware / 100),
            IntentCategory.FEATURE_AWARE: round(total * self.feature_aware / 100),
            IntentCategory.ALTERNATIVE:   round(total * self.alternative   / 100),
        }
        # Fix rounding drift so counts always sum to `total`
        diff = total - sum(counts.values())
        if diff != 0:
            # Apply remainder to the largest bucket
            largest = max(counts, key=counts.get)
            counts[largest] += diff
        return counts


class BaselineConfig(BaseModel):
    """
    Complete brand configuration — the single source of truth for every pipeline run.

    Loaded from a YAML file (configs/*.yaml) or constructed programmatically.
    All fields are validated on construction via Pydantic.
    """

    # ── Core identity ─────────────────────────────────────────────────────────
    brand_name:     str = Field(..., min_length=1, description="The brand to track")
    competitors:    List[str] = Field(..., min_length=1, description="At least one competitor")
    keywords:       List[str] = Field(..., min_length=2, description="At least two target keywords")
    domain_context: str = Field(..., min_length=10, description="Brief description of what the brand does")

    # ── Industry & geography ──────────────────────────────────────────────────
    industry: str = Field(
        default="B2B SaaS",
        description="Primary industry vertical (e.g. 'B2B SaaS', 'FinTech', 'E-Commerce')"
    )
    geography: List[str] = Field(
        default_factory=lambda: ["Global"],
        description="Target markets (e.g. ['US', 'EU', 'India'])"
    )

    # ── Product & use-case detail ─────────────────────────────────────────────
    product_lines: List[str] = Field(
        default_factory=list,
        description="Named products/features (e.g. ['Brand Monitor', 'AEO Analytics'])"
    )
    use_cases: List[str] = Field(
        default_factory=list,
        description="Primary use cases users solve with this brand"
    )

    # ── Audience ──────────────────────────────────────────────────────────────
    target_audience: str = Field(
        default="enterprise marketing teams",
        description="Who uses this product (used to calibrate prompt tone)"
    )

    # ── Prompt generation controls ────────────────────────────────────────────
    num_prompts: int = Field(
        default=10, ge=3, le=100,
        description="Total synthetic prompts to generate per run (3–100)"
    )
    intent_mix: IntentMix = Field(
        default_factory=IntentMix,
        description="Percentage split across the 6 intent categories (must sum to 100)"
    )

    # ── Quality control ───────────────────────────────────────────────────────
    negative_keywords: List[str] = Field(
        default_factory=list,
        description="Topics to exclude from generated prompts (e.g. ['pricing', 'lawsuit'])"
    )
    min_diversity_score: float = Field(
        default=0.70, ge=0.0, le=1.0,
        description="Minimum acceptable diversity score for the prompt collection (0–1)"
    )

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("brand_name")
    @classmethod
    def brand_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("brand_name cannot be blank")
        return v

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty_strings(cls, v: List[str]) -> List[str]:
        cleaned = [k.strip() for k in v if k.strip()]
        if len(cleaned) < 2:
            raise ValueError("At least 2 non-empty keywords are required")
        return cleaned

    @field_validator("competitors")
    @classmethod
    def competitors_not_empty(cls, v: List[str]) -> List[str]:
        cleaned = [c.strip() for c in v if c.strip()]
        if not cleaned:
            raise ValueError("At least 1 competitor is required")
        return cleaned

    def summary(self) -> str:
        """Human-readable one-line summary of this config."""
        return (
            f"Brand='{self.brand_name}' | Industry={self.industry} | "
            f"Keywords={len(self.keywords)} | Competitors={len(self.competitors)} | "
            f"Prompts={self.num_prompts}"
        )


# ── Phase 1: Prompt Synthesis ────────────────────────────────────────────────

class SyntheticPrompt(BaseModel):
    """
    A single generated test query with metadata about how it was created.
    """
    intent_category:  IntentCategory
    prompt_text:      str
    template_used:    Optional[str] = None   # the template string this was derived from
    generated_by:     str = "mock"           # "llm" | "mock" | "template"

class SyntheticPromptCollection(BaseModel):
    """Container for all generated prompts in one batch, with quality metadata."""
    prompts:         List[SyntheticPrompt]
    diversity_score: Optional[float] = None   # 0.0–1.0, set by prompt_validator
    intent_counts:   Optional[Dict[str, int]] = None  # {"Informational": 4, ...}


# ── Phase 1: Prompt Quality Validation ───────────────────────────────────────

class PromptDiversityReport(BaseModel):
    """
    Quality report produced by prompt_validator.validate_collection().
    Gives a complete picture of prompt diversity and flags issues.
    """
    total_prompts:       int
    unique_prompts:      int
    duplicates_removed:  int
    intent_distribution: Dict[str, int]         # how many prompts per intent
    diversity_score:     float                  # 0.0–1.0
    passes_threshold:    bool                   # diversity >= config.min_diversity_score
    warnings:            List[str] = Field(default_factory=list)
    suggestions:         List[str] = Field(default_factory=list)


# ── Phase 2: LLM Dispatch ────────────────────────────────────────────────────

class LLMResponse(BaseModel):
    """Raw response captured from a single LLM call."""
    prompt_text:     str
    model_name:      str
    raw_response:    str
    latency_ms:      Optional[float] = None
    prompt_tokens:   Optional[int]   = None
    response_tokens: Optional[int]   = None
    error:           Optional[str]   = None


# ── Phase 3: NLP Evaluation ──────────────────────────────────────────────────

class ChunkEvaluation(BaseModel):
    """
    Structured output from the LLM-as-a-Judge analysis of one response.
    Captures brand presence, sentiment, and citation evidence.
    """
    prompt_text:         str
    model_name:          str
    brand_mentioned:     bool
    mention_count:       int       = 0
    sentiment:           Sentiment = Sentiment.NEUTRAL
    citations:           List[str] = Field(default_factory=list)
    competitor_mentions: List[str] = Field(default_factory=list)
    raw_response:        str       = ""

class BrandScore(BaseModel):
    """
    The three core AEO metrics computed from a full batch of evaluations.

    BVI  — Brand Visibility Index        (0-100)
    CMCS — Cross-Model Consistency Score (0-100)
    CAS  — Citation Authority Score      (0-100)
    """
    brand_name:          str
    total_prompts:       int
    brand_mentioned_in:  int
    bvi:                 float
    cmcs:                float
    cas:                 float
    avg_sentiment_score: float
    top_citations:       List[str] = Field(default_factory=list)
    competitor_share:    Dict[str, int] = Field(default_factory=dict)


# ── Phase 4: Final Report ────────────────────────────────────────────────────

class RunReport(BaseModel):
    """
    Complete output of one full pipeline run.
    Saved as a timestamped JSON file in reports/.
    """
    run_id:           str
    timestamp:        str
    config:           BaselineConfig
    diversity_report: Optional[PromptDiversityReport] = None
    prompts_used:     List[SyntheticPrompt]
    evaluations:      List[ChunkEvaluation]
    score:            BrandScore
