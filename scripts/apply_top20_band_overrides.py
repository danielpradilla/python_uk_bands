#!/usr/bin/env python3
"""Apply a dated review layer without overwriting the original candidate list."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument(
        "--overrides",
        type=Path,
        default=(
            PROJECT_ROOT
            / "reference"
            / "top20_city_band_overrides_20260718.csv"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    review = pd.read_csv(args.review, keep_default_na=False)
    overrides = pd.read_csv(args.overrides, keep_default_na=False)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = (
        PROJECT_ROOT
        / "data"
        / "interim"
        / f"top20_city_band_review_{timestamp}_curated.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "interim"
        / f"top20_city_band_review_{timestamp}_curated_report.json"
    )

    # Promote exact source-aligned rows, but retain every manual override below.
    exact = review["origin_alignment"].eq("exact") & review["spotify_id"].ne("")
    review.loc[exact, "origin_review_status"] = "reviewed"

    applied = []
    for override in overrides.to_dict("records"):
        mask = review["band_name"].eq(override["existing_band_name"])
        if mask.sum() != 1:
            raise ValueError(
                "Every override must match exactly one band: "
                f"{override['existing_band_name']} matched {mask.sum()}"
            )
        index = review.index[mask][0]
        if override["action"] not in {"update", "replace"}:
            raise ValueError(f"Unknown override action: {override['action']}")
        if override["action"] == "replace":
            review.at[index, "band_name"] = override["replacement_band_name"]
            review.at[index, "wikidata_id"] = ""
            review.at[index, "wikidata_name"] = ""
            review.at[index, "wikidata_formation_places"] = ""
            review.at[index, "musicbrainz_id"] = ""
            review.at[index, "musicbrainz_name"] = ""
            review.at[index, "musicbrainz_begin_area"] = ""
            review.at[index, "musicbrainz_area"] = ""
            review.at[index, "musicbrainz_disambiguation"] = ""
        for target in (
            "claimed_formation_place",
            "spotify_id",
            "origin_review_status",
            "origin_alignment",
        ):
            if override[target]:
                review.at[index, target] = override[target]
        review.at[index, "evidence_url"] = override["evidence_url"]
        review.at[index, "selection_source"] = override["selection_source"]
        review.at[index, "notes"] = override["notes"]
        review.at[index, "identity_resolution"] = "manual_reviewed_spotify_id"
        applied.append(
            {
                "action": override["action"],
                "from": override["existing_band_name"],
                "to": review.at[index, "band_name"],
            }
        )

    review["review_ready"] = (
        review["origin_review_status"].eq("reviewed")
        & review["spotify_id"].ne("")
    )
    if len(review) != 110:
        raise ValueError(f"Expected 110 additions, found {len(review)}")
    if review["band_name"].duplicated().any():
        raise ValueError("Curated addition names must be unique")
    city_counts = review.groupby("study_city_label").size()
    if len(city_counts) != 11 or not city_counts.eq(10).all():
        raise ValueError("Curated additions must contain 11 cities by ten bands")

    write_csv(review, output_path)
    not_ready = review.loc[
        ~review["review_ready"],
        ["band_name", "study_city_label", "origin_review_status", "spotify_id"],
    ]
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_review": str(args.review.resolve().relative_to(PROJECT_ROOT)),
        "overrides": str(args.overrides.resolve().relative_to(PROJECT_ROOT)),
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
        "rows": len(review),
        "review_ready_rows": int(review["review_ready"].sum()),
        "not_ready_rows": len(not_ready),
        "not_ready_bands": not_ready.to_dict("records"),
        "applied_overrides": applied,
        "original_candidate_file_modified": False,
    }
    write_json(report, report_path)
    print(f"Curated review: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0 if not_ready.empty else 2


if __name__ == "__main__":
    raise SystemExit(main())
