# -*- coding: utf-8 -*-
"""
main.py — AEOBrand End-to-End Pipeline Runner (Production)

Pipeline steps:
  1. Load config from YAML file (--config) or CLI flags or built-in demo
  2. Generate synthetic prompts — proportional across 6 intent categories
  3. Validate prompts — deduplicate, diversity-score, filter negatives
  4. Dispatch to LLM concurrently (async, with semaphore rate-limiting)
  5. Evaluate each response (LLM-as-a-Judge or keyword heuristics)
  6. Compute BVI / CMCS / CAS mathematical scores
  7. Build and save RunReport to reports/<run_id>.json
  8. Print rich console summary

Usage:
  python src/main.py                                  # demo config, template mode
  python src/main.py --config configs/aeobrand.yaml  # load from YAML
  python src/main.py --brand "MyBrand" --prompts 20  # quick CLI config
  python src/main.py --list-reports                   # show all past runs
  python src/main.py --list-configs                   # show all YAML configs
"""

import sys
import io

# Force UTF-8 on Windows (avoids cp1252 errors with box-drawing chars)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Ensure src/ on path when called from the project root
sys.path.insert(0, str(Path(__file__).parent))

from models import BaselineConfig
from config_loader import load_config, load_default_config, list_configs, _builtin_demo_config
from prompt_generator import build_prompt_collection
from prompt_validator import validate_collection
from dispatcher import run_dispatch
from scorer import evaluate_responses, compute_brand_score
from report_builder import build_report, list_reports

# ── ANSI colour helpers ───────────────────────────────────────────────────────
def _c(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return str(text)
    return f"\033[{code}m{text}\033[0m"

BOLD   = lambda t: _c(t, "1")
GREEN  = lambda t: _c(t, "92")
YELLOW = lambda t: _c(t, "93")
RED    = lambda t: _c(t, "91")
CYAN   = lambda t: _c(t, "96")
BLUE   = lambda t: _c(t, "94")
DIM    = lambda t: _c(t, "2")
MAGENTA= lambda t: _c(t, "95")

BANNER = """
+----------------------------------------------------------+
|   AEOBrand  --  Enterprise AI Visibility Observatory     |
|   Phase 1: Configuration & Prompt Synthesis              |
+----------------------------------------------------------+
"""

INTENT_COLOR = {
    "Info": CYAN,
    "Comp": BLUE,
    "Tran": GREEN,
    "Prob": YELLOW,
    "Feat": MAGENTA,
    "Alte": RED,
}

# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_sentiment(score: float) -> str:
    label = "POSITIVE" if score > 0.1 else ("NEGATIVE" if score < -0.1 else "NEUTRAL")
    fn    = GREEN if score > 0.1 else (RED if score < -0.1 else YELLOW)
    return fn(f"{label} ({score:+.2f})")


def _bvi_bar(value: float, width: int = 28) -> str:
    filled = int((value / 100) * width)
    bar    = "█" * filled + "░" * (width - filled)
    colour = GREEN if value >= 70 else (YELLOW if value >= 40 else RED)
    return colour(f"[{bar}] {value:.1f}%")


def _diversity_bar(score: float, width: int = 20) -> str:
    filled = int(score * width)
    bar    = "█" * filled + "░" * (width - filled)
    colour = GREEN if score >= 0.75 else (YELLOW if score >= 0.55 else RED)
    return colour(f"[{bar}] {score:.2f}")


def _intent_tag(category_value: str) -> str:
    tag = category_value[:4]
    fn  = INTENT_COLOR.get(tag, DIM)
    return fn(f"{tag:4}")


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(config: BaselineConfig) -> None:
    has_key = (
        bool(os.getenv("OPENAI_API_KEY"))
        and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here"
    )
    mode = GREEN("LIVE (OpenAI GPT-4o)") if has_key else YELLOW(
        "SIMULATED (no API key; not real model results)"
    )

    print(CYAN(BANNER))
    print(BOLD("=" * 60))
    print(f"  Brand       : {BOLD(config.brand_name)}")
    print(f"  Industry    : {config.industry}")
    print(f"  Mode        : {mode}")
    print(f"  Prompts     : {config.num_prompts}")
    print(f"  Competitors : {', '.join(config.competitors)}")
    print(f"  Geography   : {', '.join(config.geography)}")
    print(f"  Audience    : {config.target_audience}")
    print(BOLD("=" * 60) + "\n")

    # ── Step 1: Generate synthetic prompts ────────────────────────────────────
    print(BOLD("(1) Generating synthetic prompts..."))
    t0 = time.time()
    raw_collection = build_prompt_collection(config)
    if not raw_collection.prompts:
        raise RuntimeError("Prompt generation returned no prompts; stopping without a report.")
    elapsed = time.time() - t0
    print(f"    {GREEN('OK')} {len(raw_collection.prompts)} prompts generated  "
          f"{DIM(f'({elapsed:.1f}s)')}\n")

    # ── Step 2: Validate & score prompt diversity ─────────────────────────────
    print(BOLD("(2) Validating prompt quality..."))
    t0 = time.time()
    collection, div_report = validate_collection(raw_collection, config)
    elapsed = time.time() - t0

    status = GREEN("PASS") if div_report.passes_threshold else YELLOW("WARN")
    print(f"    {status} Diversity score: "
          f"{_diversity_bar(div_report.diversity_score)}  "
          f"{DIM(f'({elapsed:.2f}s)')}")

    if div_report.duplicates_removed:
        print(f"    {YELLOW('!')}  {div_report.duplicates_removed} duplicate(s) removed")

    if div_report.warnings:
        for w in div_report.warnings:
            print(f"    {YELLOW('!')}  {w}")

    print(f"\n    Intent distribution:")
    for intent, count in div_report.intent_distribution.items():
        bar = GREEN("█") * count + DIM("░") * max(0, 6 - count)
        print(f"      {intent:<20} {bar} {count}")
    print()

    # Print numbered prompt list
    print(f"    {len(collection.prompts)} prompts ready:")
    for i, p in enumerate(collection.prompts, 1):
        tag = _intent_tag(p.intent_category.value)
        src = DIM(f"[{p.generated_by[:4]}]")
        print(f"      {DIM(str(i)+'.')} [{tag}] {src} {p.prompt_text}")
    print()

    prompts = collection.prompts
    if not prompts:
        raise RuntimeError("Prompt validation removed every prompt; stopping without a report.")

    # ── Step 3: Dispatch to LLM ───────────────────────────────────────────────
    print(BOLD("(3) Dispatching prompts to LLM..."))
    t0 = time.time()
    responses = run_dispatch(
        prompts,
        brand_name=config.brand_name,
        competitors=config.competitors,
    )
    ok_count  = sum(1 for r in responses if not r.error)
    err_count = len(responses) - ok_count
    elapsed   = time.time() - t0
    err_str   = f"  {RED(str(err_count) + ' errors')}" if err_count else ""
    print(f"    {GREEN('OK')} {ok_count} responses received{err_str}  "
          f"{DIM(f'({elapsed:.1f}s)')}\n")
    if not ok_count:
        details = "; ".join(r.error or "unknown error" for r in responses[:3])
        raise RuntimeError(f"All model dispatches failed; no report was saved. {details}")

    # ── Step 4: NLP Evaluation ────────────────────────────────────────────────
    print(BOLD("(4) Running NLP evaluation (LLM-as-a-Judge)..."))
    t0 = time.time()
    evaluations = evaluate_responses(responses, config)
    score       = compute_brand_score(evaluations, config)
    elapsed     = time.time() - t0
    print(f"    {GREEN('OK')} {len(evaluations)} responses evaluated  "
          f"{DIM(f'({elapsed:.1f}s)')}\n")

    # ── Step 5: Build and save report ─────────────────────────────────────────
    print(BOLD("(5) Building and saving report..."))
    report = build_report(
        config, prompts, evaluations, score, div_report,
        execution_mode="live" if has_key else "simulated",
    )
    print(f"    {GREEN('OK')} Saved -> reports/{report.run_id}.json\n")

    # ── Step 6: Final summary ─────────────────────────────────────────────────
    _print_summary(config, score, div_report, evaluations, report)


def _print_summary(config, score, div_report, evaluations, report) -> None:
    print(BOLD("=" * 60))
    print(BOLD(f"  AEO SCORE REPORT  --  {config.brand_name}"))
    print(BOLD("=" * 60) + "\n")

    print(f"  Brand Visibility Index  (BVI) : {_bvi_bar(score.bvi)}")
    print(f"  Cross-Model Consistency (CMCS): {_bvi_bar(score.cmcs)}")
    print(f"  Citation Authority      (CAS) : {_bvi_bar(score.cas)}")
    print(f"  Prompt Diversity Score        : {_diversity_bar(div_report.diversity_score)}")
    print(f"  Average Sentiment             : {_fmt_sentiment(score.avg_sentiment_score)}")
    print()
    print(f"  Total prompts : {score.total_prompts}")
    print(f"  Brand found in: {score.brand_mentioned_in} / {score.total_prompts} prompts")

    if score.top_citations:
        print(f"\n  Top cited sources:")
        for src in score.top_citations:
            print(f"    - {src}")

    if score.competitor_share:
        print(f"\n  Competitor mentions:")
        for comp, count in sorted(score.competitor_share.items(), key=lambda x: -x[1]):
            print(f"    - {comp}: {count}x")

    print()
    print(BOLD("=" * 60))
    print(BOLD("\n  Per-Prompt Breakdown:\n"))

    for ev in evaluations:
        flag = GREEN("+ mentioned") if ev.brand_mentioned else RED("- not found")
        tag  = f"[{ev.sentiment.value[:3]}]"
        print(f"  {flag}  {tag}  {ev.prompt_text[:68]}")

    print()
    print(f"  Run ID    : {CYAN(report.run_id)}")
    print(f"  Timestamp : {DIM(report.timestamp)}")
    print()
    print(DIM("  Open dashboard/index.html to visualise this report."))
    print(BOLD("=" * 60) + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AEOBrand — Enterprise AI Visibility Observatory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py
  python src/main.py --config configs/aeobrand.yaml
  python src/main.py --brand "MyBrand" --prompts 15
  python src/main.py --list-reports
  python src/main.py --list-configs
        """,
    )

    # Config source (mutually exclusive group)
    cfg_group = parser.add_argument_group("Config source (pick one)")
    cfg_group.add_argument(
        "--config", metavar="FILE",
        help="Path to a YAML brand config file (e.g. configs/aeobrand.yaml)"
    )
    cfg_group.add_argument(
        "--brand", default=None,
        help="Brand name for a quick inline config (no YAML needed)"
    )

    # Inline config overrides (used with --brand)
    inline = parser.add_argument_group("Inline config options (used with --brand)")
    inline.add_argument("--competitors", nargs="+", default=["CompetitorA", "CompetitorB"],
                        help="Competitor names")
    inline.add_argument("--keywords", nargs="+",
                        default=["AI brand visibility", "Answer Engine Optimization"],
                        help="Target keywords")
    inline.add_argument("--context",
                        default="B2B SaaS platform for AI brand tracking.",
                        help="Domain context description")
    inline.add_argument("--industry", default="B2B SaaS",
                        help="Industry vertical")
    inline.add_argument("--audience", default="enterprise marketing teams",
                        help="Target audience")
    inline.add_argument("--prompts", type=int, default=10,
                        help="Number of prompts to generate (default: 10)")

    # Utility commands
    utils = parser.add_argument_group("Utilities")
    utils.add_argument("--list-reports", action="store_true",
                       help="List all saved reports and exit")
    utils.add_argument("--list-configs", action="store_true",
                       help="List all available YAML configs and exit")

    return parser.parse_args()


def _resolve_config(args: argparse.Namespace) -> BaselineConfig:
    """Determine which config to use based on CLI arguments."""

    # Priority 1: explicit YAML file
    if args.config:
        print(f"  Loading config: {args.config}")
        return load_config(args.config)

    # Priority 2: inline --brand flag
    if args.brand:
        return BaselineConfig(
            brand_name=args.brand,
            competitors=args.competitors,
            keywords=args.keywords,
            domain_context=args.context,
            industry=args.industry,
            target_audience=args.audience,
            num_prompts=args.prompts,
        )

    # Priority 3: auto-discover first YAML in configs/
    try:
        cfg = load_default_config()
        print(f"  Auto-loaded config: {cfg.brand_name}")
        return cfg
    except Exception:
        pass

    # Priority 4: built-in demo
    print("  Using built-in AEOBrand demo config.")
    return _builtin_demo_config()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = _parse_args()

    # ── Utility commands ──────────────────────────────────────────────────────
    if args.list_reports:
        reports = list_reports()
        if not reports:
            print("No reports found in reports/")
        else:
            print(f"\n{'Run ID':<10} {'Brand':<16} {'BVI':>6} {'CMCS':>6} "
                  f"{'CAS':>6}  Timestamp")
            print("-" * 66)
            for r in reports:
                print(f"{r['run_id']:<10} {r['brand']:<16} {r['bvi']:>5.1f}% "
                      f"{r['cmcs']:>5.1f}% {r['cas']:>5.1f}%  {r['timestamp'][:19]}")
        sys.exit(0)

    if args.list_configs:
        configs = list_configs()
        if not configs:
            print("No YAML configs found in configs/")
        else:
            print(f"\nAvailable configs ({len(configs)}):\n")
            for p in configs:
                try:
                    cfg = load_config(p)
                    print(f"  {p.name:<35}  {cfg.summary()}")
                except Exception as e:
                    print(f"  {p.name:<35}  [ERROR] {e}")
        sys.exit(0)

    # ── Main run ──────────────────────────────────────────────────────────────
    config = _resolve_config(args)
    run_pipeline(config)
