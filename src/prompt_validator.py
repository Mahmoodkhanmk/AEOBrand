"""
prompt_validator.py — Prompt Quality Validation & Diversity Scoring

Runs after prompt generation, before dispatch. Ensures the prompt batch
is good enough to produce meaningful analytics.

What it checks:
  1. Deduplication       — removes exact and near-duplicate prompts
  2. Negative keyword filter — removes prompts containing blocked topics
  3. Intent distribution  — verifies all 6 intent categories are represented
  4. Diversity score      — quantifies how varied the prompt set is (0.0–1.0)
  5. Pass/fail threshold  — raises a warning (not an error) if score is low

Diversity score formula:
  intent_variety    = unique_intents / 6                              × 0.40
  lexical_variety   = unique_first_bigrams / total_prompts            × 0.35
    length_variety    = min(1, std_dev_prompt_lengths / mean_length)   × 0.25
                                            (higher length variation increases diversity)
  diversity_score   = intent_variety + lexical_variety + length_variety

Target: ≥ 0.75 for production runs. Below 0.60 is a hard warning.
"""

import re
import statistics
from collections import Counter
from typing import List

from models import (
    BaselineConfig,
    IntentCategory,
    PromptDiversityReport,
    SyntheticPrompt,
    SyntheticPromptCollection,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def validate_collection(
    collection: SyntheticPromptCollection,
    config: BaselineConfig,
) -> tuple[SyntheticPromptCollection, PromptDiversityReport]:
    """
    Validate, clean, and score a SyntheticPromptCollection.

    Steps:
      1. Remove negative-keyword matches
      2. Deduplicate (exact + near-duplicate via normalised text)
      3. Compute diversity score
      4. Build PromptDiversityReport with warnings and suggestions
      5. Attach score and intent_counts to the collection

    Args:
        collection: The raw collection from prompt_generator.
        config:     The BaselineConfig used in this run.

    Returns:
        (cleaned_collection, diversity_report)
        The cleaned collection is safe to pass to the dispatcher.
    """
    original_count = len(collection.prompts)
    warnings: list[str] = []
    suggestions: list[str] = []

    # ── Step 1: Negative keyword filter ──────────────────────────────────────
    filtered = _filter_negative_keywords(collection.prompts, config.negative_keywords)
    removed_neg = original_count - len(filtered)
    if removed_neg:
        warnings.append(
            f"{removed_neg} prompt(s) removed — contained blocked keywords: "
            f"{config.negative_keywords}"
        )

    # ── Step 2: Deduplication ─────────────────────────────────────────────────
    deduped, duplicates_removed = _deduplicate(filtered)
    if duplicates_removed:
        warnings.append(
            f"{duplicates_removed} near-duplicate prompt(s) removed."
        )

    # ── Step 3: Diversity scoring ─────────────────────────────────────────────
    diversity_score = _compute_diversity_score(deduped)

    # ── Step 4: Intent distribution ───────────────────────────────────────────
    intent_counts = _count_intents(deduped)
    missing_intents = [
        cat.value for cat in IntentCategory if intent_counts.get(cat.value, 0) == 0
    ]
    if missing_intents:
        warnings.append(
            f"Missing intent categories: {missing_intents}. "
            "Add more prompts or widen the intent_mix percentages."
        )
        suggestions.append(
            "Run with --prompts N (higher N) to ensure all 6 categories are covered."
        )

    # ── Step 5: Threshold check ───────────────────────────────────────────────
    passes = diversity_score >= config.min_diversity_score
    if not passes:
        warnings.append(
            f"Diversity score {diversity_score:.2f} is below threshold "
            f"{config.min_diversity_score:.2f}. Results may lack coverage."
        )
        suggestions.append(
            "Consider increasing num_prompts or adjusting intent_mix to spread "
            "prompt types more evenly."
        )

    # Empty input is unusable; a low diversity score remains a reported warning.
    if not deduped:
        raise ValueError("Prompt validation removed every prompt; no run can be evaluated.")

    # ── Build cleaned collection ──────────────────────────────────────────────
    cleaned = SyntheticPromptCollection(
        prompts=deduped,
        diversity_score=round(diversity_score, 4),
        intent_counts=intent_counts,
    )

    report = PromptDiversityReport(
        total_prompts=len(deduped),
        unique_prompts=len(deduped),
        duplicates_removed=duplicates_removed,
        intent_distribution=intent_counts,
        diversity_score=round(diversity_score, 4),
        passes_threshold=passes,
        warnings=warnings,
        suggestions=suggestions,
    )

    return cleaned, report


# ── Deduplication ──────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """
    Normalise a prompt string for similarity comparison.
    Lowercases, strips punctuation, collapses whitespace.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _deduplicate(prompts: list[SyntheticPrompt]) -> tuple[list[SyntheticPrompt], int]:
    """
    Remove exact duplicates and near-duplicates (same normalised form).

    Returns (unique_prompts, number_removed).
    """
    seen: set[str] = set()
    unique: list[SyntheticPrompt] = []
    removed = 0

    for prompt in prompts:
        key = _normalise(prompt.prompt_text)
        if key not in seen:
            seen.add(key)
            unique.append(prompt)
        else:
            removed += 1

    return unique, removed


# ── Negative keyword filtering ─────────────────────────────────────────────────

def _filter_negative_keywords(
    prompts: list[SyntheticPrompt],
    negative_keywords: list[str],
) -> list[SyntheticPrompt]:
    """Remove any prompt containing a negative/blocked keyword."""
    if not negative_keywords:
        return prompts

    blocked_lower = [kw.lower() for kw in negative_keywords]
    return [
        p for p in prompts
        if not any(kw in p.prompt_text.lower() for kw in blocked_lower)
    ]


# ── Diversity scoring ──────────────────────────────────────────────────────────

def _compute_diversity_score(prompts: list[SyntheticPrompt]) -> float:
    """
    Compute a 0.0–1.0 diversity score for a prompt collection.

    Three components (weighted):
      intent_variety   (40%) — how many of the 6 intent types are represented
      lexical_variety  (35%) — unique opening 2-word pairs (bigrams)
      length_variety   (25%) — variation in prompt word count
    """
    if not prompts:
        return 0.0

    total = len(prompts)

    # Component 1: Intent variety
    unique_intents = len(set(p.intent_category for p in prompts))
    intent_variety = unique_intents / len(IntentCategory)          # 0–1

    # Component 2: Lexical variety via first-bigram uniqueness
    def first_bigram(text: str) -> str:
        words = text.lower().split()
        return " ".join(words[:2]) if len(words) >= 2 else words[0] if words else ""

    bigrams = [first_bigram(p.prompt_text) for p in prompts]
    unique_bigrams = len(set(bigrams))
    lexical_variety = unique_bigrams / total                       # 0–1

    # Component 3: Length variety (coefficient of variation, inverted)
    lengths = [len(p.prompt_text.split()) for p in prompts]
    if len(lengths) > 1 and statistics.mean(lengths) > 0:
        cv = statistics.stdev(lengths) / statistics.mean(lengths)  # coefficient of variation
        length_variety = min(1.0, cv)                              # cap at 1.0
    else:
        length_variety = 0.0

    score = (
        intent_variety  * 0.40 +
        lexical_variety * 0.35 +
        length_variety  * 0.25
    )
    return min(1.0, max(0.0, score))


# ── Intent distribution ────────────────────────────────────────────────────────

def _count_intents(prompts: list[SyntheticPrompt]) -> dict[str, int]:
    """Return a count of prompts per intent category."""
    counter: Counter = Counter(p.intent_category.value for p in prompts)
    # Fill in zeros for any missing categories
    for cat in IntentCategory:
        counter.setdefault(cat.value, 0)
    return dict(sorted(counter.items()))


# ── Standalone CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from config_loader import load_default_config
    from prompt_generator import build_prompt_collection

    cfg = load_default_config()
    collection = build_prompt_collection(cfg)
    cleaned, report = validate_collection(collection, cfg)

    SEP = "=" * 55
    print(SEP)
    print("  PROMPT VALIDATION REPORT")
    print(SEP)
    print(f"  Total prompts     : {report.total_prompts}")
    print(f"  Duplicates removed: {report.duplicates_removed}")
    status = "PASS" if report.passes_threshold else "WARN"
    print(f"  Diversity score   : {report.diversity_score:.4f}  ({status})")
    print()
    print("  Intent distribution:")
    for intent, count in report.intent_distribution.items():
        bar = "#" * count + "." * max(0, 6 - count)
        print(f"    {intent:<22} {bar} ({count})")
    if report.warnings:
        print("\n  Warnings:")
        for w in report.warnings:
            print(f"    [!] {w}")
    if report.suggestions:
        print("\n  Suggestions:")
        for s in report.suggestions:
            print(f"    [>] {s}")
    print()
    print("  Validated prompts:")
    for i, p in enumerate(cleaned.prompts, 1):
        print(f"    {i:2}. [{p.intent_category.value[:4]}] {p.prompt_text}")
    print(SEP)
