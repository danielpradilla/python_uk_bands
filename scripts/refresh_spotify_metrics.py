#!/usr/bin/env python3
"""Fetch, validate and optionally promote a new shortlist metrics snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (
    SHORTLIST_METRICS_PATH,
    SPOTIFY_IDENTIFIERS_PATH,
    SPOTIFY_RAW_DIR,
)
from python_uk_bands.io import write_json
from python_uk_bands.metrics import fetch_spotscraper_metrics, validate_metric_candidate

def _read_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Replace the canonical metrics only after every blocking check passes.",
    )
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per API request")
    args = parser.parse_args(argv)

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("SPOTSCRAPER_API_KEY")
    if not api_key:
        raise RuntimeError("SPOTSCRAPER_API_KEY is missing")

    identifiers = _read_rows(SPOTIFY_IDENTIFIERS_PATH)
    previous = _read_rows(SHORTLIST_METRICS_PATH)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    SPOTIFY_RAW_DIR.mkdir(parents=True, exist_ok=True)
    candidate_path = SPOTIFY_RAW_DIR / f"shortlist_metrics_{timestamp}.json"
    report_path = SPOTIFY_RAW_DIR / f"shortlist_metrics_{timestamp}_report.json"

    candidate, failures = fetch_spotscraper_metrics(
        identifiers,
        api_key=api_key,
        attempts=max(args.attempts, 1),
    )
    report = validate_metric_candidate(candidate, identifiers, previous)
    report.update(
        {
            "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "SpotScraper artist endpoint",
            "failures": failures,
            "candidate_path": str(candidate_path.relative_to(PROJECT_ROOT)),
            "promoted": False,
        }
    )
    write_json(candidate, candidate_path)

    if args.promote and report["promotion_ready"]:
        shutil.copy2(candidate_path, SHORTLIST_METRICS_PATH)
        report["promoted"] = True

    write_json(report, report_path)
    print(f"Candidate rows: {len(candidate)}/{len(identifiers)}")
    print(f"Promotion ready: {report['promotion_ready']}")
    print(f"Promoted: {report['promoted']}")
    print(f"Candidate: {candidate_path}")
    print(f"Report:    {report_path}")
    if failures:
        first = failures[0]
        print(f"First failure: HTTP {first.get('status')} for {first.get('band')}")
    return 0 if report["promotion_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
