#!/usr/bin/env python3
"""Build dated band-level data and rankings for the top-20 city-first study."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_csv, write_json
from python_uk_bands.scene_depth import build_scene_depth_rankings
from python_uk_bands.top20 import validate_top20_catalog


def _snapshot_id(path: Path) -> str:
    match = re.search(r"_(\d{8}T\d{6}Z)\.csv$", path.name)
    if not match:
        raise ValueError(f"Metrics path has no UTC snapshot ID: {path}")
    return match.group(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--spotify-metrics", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = pd.read_csv(args.catalog, keep_default_na=False)
    metrics = pd.read_csv(args.spotify_metrics, keep_default_na=False)
    validate_top20_catalog(catalog)
    snapshot_id = _snapshot_id(args.spotify_metrics)

    if len(metrics) != 200 or metrics["band"].duplicated().any():
        raise ValueError("Spotify snapshot must contain 200 unique bands")
    if metrics["monthly_listeners"].isna().any():
        raise ValueError("Spotify monthly-listener values must be complete")

    analysis = catalog.merge(
        metrics,
        left_on=["band_name", "study_city_label", "spotify_id"],
        right_on=["band", "city", "spotify_id"],
        validate="one_to_one",
        suffixes=("", "_captured"),
    )
    if len(analysis) != 200:
        raise ValueError("Catalogue and Spotify snapshot did not fully match")
    analysis["band"] = analysis["band_name"]
    analysis["city"] = analysis["study_city_label"]

    rankings = build_scene_depth_rankings(
        analysis,
        metric="monthly_listeners",
        trim_each_tail=1,
        expected_cities=20,
        bands_per_city=10,
    )
    rankings["untrimmed_listeners_per_million_residents"] = (
        rankings["untrimmed_ratio"] * 1_000_000
    )
    rankings["trimmed_total_per_million_residents"] = (
        rankings["scene_depth_ratio"] * 1_000_000
    )
    rankings["population_normalized_trimmed_mean_per_million"] = (
        rankings["population_normalized_trimmed_mean"] * 1_000_000
    )

    band_metrics_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"top20_city_band_metrics_{snapshot_id}.csv"
    )
    rankings_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"top20_city_rankings_{snapshot_id}.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"top20_city_analysis_{snapshot_id}_report.json"
    )
    write_csv(analysis, band_metrics_path)
    write_csv(rankings, rankings_path)

    correlation = rankings["untrimmed_rank"].corr(
        rankings["rank"],
        method="pearson",
    )
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "spotify_snapshot_id": snapshot_id,
        "catalog_path": str(args.catalog.resolve().relative_to(PROJECT_ROOT)),
        "spotify_metrics_path": str(
            args.spotify_metrics.resolve().relative_to(PROJECT_ROOT)
        ),
        "band_rows": len(analysis),
        "cities": analysis["city"].nunique(),
        "bands_per_city": sorted(
            analysis.groupby("city").size().unique().tolist()
        ),
        "origin_review_ready_rows": int(
            analysis["catalogue_review_ready"].sum()
        ),
        "spotify_capture_dates": sorted(
            analysis["stats_extracted_at_utc"].unique().tolist()
        ),
        "untrimmed_vs_trimmed_rank_spearman": float(correlation),
        "untrimmed_top10": rankings.nsmallest(10, "untrimmed_rank")[
            ["city", "untrimmed_rank"]
        ].to_dict("records"),
        "trimmed_top10": rankings.nsmallest(10, "rank")[
            ["city", "rank"]
        ].to_dict("records"),
        "band_metrics_path": str(band_metrics_path.relative_to(PROJECT_ROOT)),
        "rankings_path": str(rankings_path.relative_to(PROJECT_ROOT)),
        "analysis_status": "experimental_complete",
        "published_notebook_modified": False,
    }
    write_json(report, report_path)
    print(f"Band metrics: {band_metrics_path.relative_to(PROJECT_ROOT)}")
    print(f"Rankings: {rankings_path.relative_to(PROJECT_ROOT)}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
