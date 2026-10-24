# -*- coding: utf-8 -*-
"""
main.py — AEOBrand End-to-End Pipeline Runner

Runs the complete pipeline in sequence:
  1. Load config (brand, keywords, competitors)
  2. Generate synthetic prompts (LLM or mock)
  3. Dispatch prompts to LLM concurrently (async)
  4. Evaluate each response (NLP Judge or mock)
  5. Compute BVI / CMCS / CAS scores
  6. Build and save RunReport to reports/
  7. Print a human-readable summary to console

Usage:
  python src/main.py                     # uses built-in demo config
  python src/main.py --brand "MyBrand"   # custom brand (see --help)
"""

import sys
import io

# Force UTF-8 output on Windows to avoid cp1252 errors with Unicode characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import os
import time

from dotenv import load_dotenv

load_dotenv()

# ── Ensure src/ is on the path when run from project root ─────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from models import BaselineConfig
from prompt_generator import generate_synthetic_prompts, mock_generate_prompts
from dispatcher import run_dispatch
from scorer import evaluate_responses, compute_brand_score
from report_builder import build_report, list_reports

# ── ANSI colour helpers ───────────────────────────────────────────────────────
def _c(text: str, code: str) -> str:
    """Wrap text in an ANSI escape code (no-op on non-TTY)."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

BOLD   = lambda t: _c(t, "1")
GREEN  = lambda t: _c(t, "92")
YELLOW = lambda t: _c(t, "93")
RED    = lambda t: _c(t, "91")
CYAN   = lambda t: _c(t, "96")
DIM    = lambda t: _c(t, "2")


# ── Banner ────────────────────────────────────────────────────────────────────
BANNER = """
+----------------------------------------------------------+
|   AEOBrand  --  Enterprise AI Visibility Observatory     |
+----------------------------------------------------------+
"""


# ── Sentiment display ─────────────────────────────────────────────────────────
def _fmt_sentiment(score: float) -> str:
    label = "POSITIVE" if score > 0.1 else ("NEGATIVE" if score < -0.1 else "NEUTRAL")
    fn    = GREEN if score > 0.1 else (RED if score < -0.1 else YELLOW)
    return fn(f"{label} ({score:+.2f})")


def _bvi_bar(value: float, width: int = 30) -> str:
    """ASCII progress bar for a 0-100 metric."""
    filled = int((value / 100) * width)
    bar    = "█" * filled + "░" * (width - filled)
    colour = GREEN if value >= 70 else (YELLOW if value >= 40 else RED)
    return colour(f"[{bar}] {value:.1f}%")


# ── Main pipeline ──────────────────────────────────────────────────────────────
def run_pipeline(config: BaselineConfig, num_prompts: int = 10) -> None:
    has_key = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here"
    mode    = GREEN("LIVE (OpenAI GPT-4o)") if has_key else YELLOW("MOCK (no API key)")

    print(CYAN(BANNER))
    print(BOLD("═" * 60))
    print(f"  Brand:     {BOLD(config.brand_name)}")
    print(f"  Mode:      {mode}")
    print(f"  Prompts:   {num_prompts}")
    print(f"  Competitors: {', '.join(config.competitors)}")
    print(BOLD("═" * 60) + "\n")

    # ── Step 1: Generate synthetic prompts ────────────────────────────────────
    print(BOLD("① Generating synthetic prompts..."))
    t0 = time.time()
    if has_key:
        collection = generate_synthetic_prompts(config, num_prompts=num_prompts)
    else:
        collection = mock_generate_prompts(config)
    prompts = collection.prompts
    print(f"   {GREEN('✓')} {len(prompts)} prompts generated  {DIM(f'({time.time()-t0:.1f}s)')}\n")

    for i, p in enumerate(prompts, 1):
        print(f"   {DIM(str(i)+'.')} [{CYAN(p.intent_category.value[:4])}] {p.prompt_text}")
    print()

    # ── Step 2: Dispatch to LLM ───────────────────────────────────────────────
    print(BOLD("② Dispatching prompts to LLM..."))
    t0 = time.time()
    responses = run_dispatch(prompts)
    ok_count  = sum(1 for r in responses if not r.error)
    err_count = len(responses) - ok_count
    elapsed   = time.time() - t0
    print(f"   {GREEN('✓')} {ok_count} responses received  "
          f"{RED(f'{err_count} errors') if err_count else ''}  "
          f"{DIM(f'({elapsed:.1f}s)')}\n")

    # ── Step 3: Evaluate / score ──────────────────────────────────────────────
    print(BOLD("③ Running NLP evaluation (LLM-as-a-Judge)..."))
    t0 = time.time()
    evaluations = evaluate_responses(responses, config)
    score       = compute_brand_score(evaluations, config)
    print(f"   {GREEN('✓')} {len(evaluations)} responses evaluated  {DIM(f'({time.time()-t0:.1f}s)')}\n")

    # ── Step 4: Build report ──────────────────────────────────────────────────
    print(BOLD("④ Building report..."))
    report = build_report(config, prompts, evaluations, score)
    print(f"   {GREEN('✓')} Saved → reports/{report.run_id}.json\n")

    # ── Step 5: Print summary ─────────────────────────────────────────────────
    print(BOLD("═" * 60))
    print(BOLD(f"  📊 AEO SCORE REPORT — {config.brand_name}"))
    print(BOLD("═" * 60))
    print()

    print(f"  Brand Visibility Index  (BVI) : {_bvi_bar(score.bvi)}")
    print(f"  Cross-Model Consistency (CMCS): {_bvi_bar(score.cmcs)}")
    print(f"  Citation Authority Score (CAS): {_bvi_bar(score.cas)}")
    print(f"  Average Sentiment             : {_fmt_sentiment(score.avg_sentiment_score)}")
    print()
    print(f"  Prompts fired     : {score.total_prompts}")
    print(f"  Brand mentioned in: {score.brand_mentioned_in} / {score.total_prompts} prompts")

    if score.top_citations:
        print(f"\n  📎 Top cited sources:")
        for src in score.top_citations:
            print(f"     • {src}")

    if score.competitor_share:
        print(f"\n  🏆 Competitor mentions:")
        for comp, count in sorted(score.competitor_share.items(), key=lambda x: -x[1]):
            print(f"     • {comp}: {count}x")

    print()
    print(BOLD("═" * 60))

    # ── Evaluation detail table ───────────────────────────────────────────────
    print(BOLD("\n  📋 Per-Prompt Breakdown:\n"))
    for ev in evaluations:
        mention_flag = GREEN("✓ mentioned") if ev.brand_mentioned else RED("✗ not found")
        print(f"  {mention_flag}  [{ev.sentiment.value[:3]}]  {ev.prompt_text[:65]}")

    print()
    print(f"  Run ID   : {CYAN(report.run_id)}")
    print(f"  Timestamp: {DIM(report.timestamp)}")
    print()
    print(DIM("  Open dashboard/index.html in a browser to view the visual report."))
    print(BOLD("═" * 60) + "\n")


# ── CLI argument parser ───────────────────────────────────────────────────────
def _parse_args():
    parser = argparse.ArgumentParser(
        description="AEOBrand — Enterprise AI Visibility Observatory"
    )
    parser.add_argument("--brand",    default="AEOBrand",
                        help="Target brand name (default: AEOBrand)")
    parser.add_argument("--competitors", nargs="+", default=["BrandX", "BrandY"],
                        help="Competitor brand names")
    parser.add_argument("--keywords",    nargs="+",
                        default=["Enterprise AI Visibility", "Answer Engine Optimization", "LLM Analytics"],
                        help="Target keywords")
    parser.add_argument("--context", default="B2B SaaS platform for tracking brand representation across generative AI search engines.",
                        help="Domain context description")
    parser.add_argument("--prompts", type=int, default=5,
                        help="Number of synthetic prompts to generate (default: 5)")
    parser.add_argument("--list-reports", action="store_true",
                        help="List all saved reports and exit")
    return parser.parse_args()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = _parse_args()

    if args.list_reports:
        reports = list_reports()
        if not reports:
            print("No reports found in reports/ directory.")
        else:
            print(f"\n{'Run ID':<10} {'Brand':<15} {'BVI':>6} {'CMCS':>6} {'CAS':>6}  Timestamp")
            print("─" * 65)
            for r in reports:
                print(f"{r['run_id']:<10} {r['brand']:<15} {r['bvi']:>5.1f}% {r['cmcs']:>5.1f}% {r['cas']:>5.1f}%  {r['timestamp'][:19]}")
        sys.exit(0)

    config = BaselineConfig(
        brand_name=args.brand,
        competitors=args.competitors,
        keywords=args.keywords,
        domain_context=args.context,
    )

    run_pipeline(config, num_prompts=args.prompts)
