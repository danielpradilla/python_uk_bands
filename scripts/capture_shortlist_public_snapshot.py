#!/usr/bin/env python3
"""Capture a timestamped 50-band Spotify candidate without promoting it.

The published cache at ``data/processed/shortlist_spotify_metrics.json`` is
never written by this script. Artist IDs and the reviewed catalogue remain
fixed so that a later comparison measures popularity changes rather than
selection changes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (
    PROCESSED_DATA_DIR,
    SHORTLIST_METRICS_PATH,
    SPOTIFY_IDENTIFIERS_PATH,
    SPOTIFY_RAW_DIR,
)
from python_uk_bands.dataset import load_shortlist_dataset, validate_shortlist_shape
from python_uk_bands.io import write_json
from python_uk_bands.matching import infer_match_confidence
from python_uk_bands.spotify_public import fetch_public_spotify_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spotify-throttle",
        type=float,
        default=0.2,
        help="Seconds between public Spotify artist-page requests",
    )
    return parser


def _load_identifiers() -> list[dict]:
    identifiers = json.loads(SPOTIFY_IDENTIFIERS_PATH.read_text())
    if len(identifiers) != 50:
        raise ValueError(f"Expected 50 reviewed Spotify IDs, found {len(identifiers)}")
    if len({row["spotify_id"] for row in identifiers}) != len(identifiers):
        raise ValueError("Reviewed shortlist Spotify IDs must be unique")
    return identifiers


def _identity_review(
    identifiers: list[dict],
    metrics: list[dict],
) -> list[dict]:
    reviewed_by_band = {row["band"]: row for row in identifiers}
    review: list[dict] = []
    for metric in metrics:
        reviewed = reviewed_by_band[metric["band"]]
        confidence = infer_match_confidence(
            reviewed.get("spotify_name") or reviewed["band"],
            metric.get("spotify_name") or "",
            is_first_result=False,
        )
        if confidence != "exact":
            review.append(
                {
                    "band": metric["band"],
                    "spotify_id": metric["spotify_id"],
                    "reviewed_spotify_name": reviewed.get("spotify_name"),
                    "current_spotify_name": metric.get("spotify_name"),
                    "identity_match": confidence,
                }
            )
        metric["match_quality"] = reviewed["match_quality"]
        metric["monthly_listeners_m"] = round(
            metric["monthly_listeners"] / 1_000_000,
            2,
        )
        metric["world_rank"] = None
    return review


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    identifiers = _load_identifiers()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    raw_path = SPOTIFY_RAW_DIR / f"shortlist_public_metrics_{timestamp}.json"
    report_path = (
        SPOTIFY_RAW_DIR / f"shortlist_public_metrics_{timestamp}_report.json"
    )
    candidate_path = (
        PROCESSED_DATA_DIR / f"shortlist_spotify_metrics_{timestamp}.json"
    )

    metrics, failures = fetch_public_spotify_metrics(
        identifiers,
        throttle_seconds=max(args.spotify_throttle, 0),
    )
    identity_review = _identity_review(identifiers, metrics)
    write_json(metrics, raw_path)

    missing_followers = [
        row["band"] for row in metrics if row.get("followers") is None
    ]
    report = {
        "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_rows": len(identifiers),
        "metric_rows": len(metrics),
        "metric_failures": failures,
        "missing_followers": missing_followers,
        "identity_review": identity_review,
        "candidate_ready": False,
        "published_metrics_path": str(SHORTLIST_METRICS_PATH.relative_to(PROJECT_ROOT)),
        "published_metrics_modified": False,
    }

    if (
        len(metrics) != len(identifiers)
        or failures
        or missing_followers
        or identity_review
    ):
        write_json(report, report_path)
        print(
            "Candidate not built: resolve every metric, follower value, and "
            "identity review first.",
            flush=True,
        )
        print(f"Report: {report_path}", flush=True)
        return 2

    write_json(metrics, candidate_path)
    candidate = load_shortlist_dataset(metrics_path=candidate_path)
    validate_shortlist_shape(candidate)
    if candidate[["monthly_listeners", "followers"]].isna().any().any():
        raise ValueError("Candidate snapshot contains missing popularity metrics")

    report["candidate_ready"] = True
    report["candidate_path"] = str(candidate_path.relative_to(PROJECT_ROOT))
    report["stats_extracted_at"] = (
        pd.to_datetime(candidate["stats_extracted_at"]).max().date().isoformat()
    )
    write_json(report, report_path)

    print(f"Shortlist candidate: {candidate_path}", flush=True)
    print(f"Report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
