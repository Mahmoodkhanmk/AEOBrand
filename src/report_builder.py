"""
report_builder.py — Assembles a complete RunReport and saves it to disk.

Responsibilities:
  - Combines config + prompts + evaluations + score into a RunReport
  - Generates a unique run_id and ISO timestamp
  - Saves to reports/<run_id>.json
  - Returns the RunReport object for further use (e.g. dashboard rendering)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from models import (
    BaselineConfig,
    BrandScore,
    ChunkEvaluation,
    PromptDiversityReport,
    RunReport,
    SyntheticPrompt,
)
from typing import Optional

# Reports are saved relative to the project root (one level up from src/)
_REPORTS_DIR = Path(__file__).parent.parent / "reports"


def build_report(
    config: BaselineConfig,
    prompts: list[SyntheticPrompt],
    evaluations: list[ChunkEvaluation],
    score: BrandScore,
    diversity_report: Optional[PromptDiversityReport] = None,
) -> RunReport:
    """
    Assemble and persist a RunReport.

    Args:
        config:           The original BaselineConfig for this run
        prompts:          All synthetic prompts that were dispatched
        evaluations:      ChunkEvaluation for each successful response
        score:            Computed BrandScore metrics
        diversity_report: Optional prompt quality report from Phase 1

    Returns:
        RunReport — the saved report object
    """
    run_id    = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    report = RunReport(
        run_id=run_id,
        timestamp=timestamp,
        config=config,
        diversity_report=diversity_report,
        prompts_used=prompts,
        evaluations=evaluations,
        score=score,
    )

    _save_report(report)
    return report


def _save_report(report: RunReport) -> Path:
    """Serialise and write the report to reports/<run_id>.json."""
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _REPORTS_DIR / f"{report.run_id}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, default=str)

    return filepath


def load_latest_report() -> RunReport | None:
    """
    Load the most recently created report from the reports/ directory.
    Returns None if no reports exist.
    """
    if not _REPORTS_DIR.exists():
        return None

    report_files = sorted(
        _REPORTS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not report_files:
        return None

    with open(report_files[0], encoding="utf-8") as f:
        data = json.load(f)

    return RunReport(**data)


def list_reports() -> list[dict]:
    """Return a summary list of all saved reports (id, timestamp, brand, BVI)."""
    if not _REPORTS_DIR.exists():
        return []

    summaries = []
    for filepath in sorted(_REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            summaries.append({
                "run_id":    data["run_id"],
                "timestamp": data["timestamp"],
                "brand":     data["config"]["brand_name"],
                "bvi":       data["score"]["bvi"],
                "cmcs":      data["score"]["cmcs"],
                "cas":       data["score"]["cas"],
                "file":      str(filepath),
            })
        except Exception:
            continue

    return summaries
