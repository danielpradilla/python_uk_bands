#!/usr/bin/env python3
"""Build a separate ten-band scene-depth snapshot and ranking.

This script is intentionally isolated from the canonical 50-band analysis. It
does not read or write ``data/processed/shortlist_spotify_metrics.json``. It
only reuses already reviewed Spotify IDs, and it never changes the final
notebook or existing charts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (
    FUA_POPULATION_PATH,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    REFERENCE_DIR,
    SPOTIFY_IDENTIFIERS_PATH,
    SPOTIFY_RAW_DIR,
)
from python_uk_bands.io import write_csv, write_json
from python_uk_bands.matching import infer_match_confidence
from python_uk_bands.scene_depth import build_scene_depth_rankings
from python_uk_bands.spotify_public import (
    fetch_musicbrainz_spotify_url,
    fetch_public_spotify_metrics,
    spotify_artist_id_from_url,
)


DEFAULT_CATALOG = REFERENCE_DIR / "scene_depth_bands.csv"
POPULATIONS_PATH = FUA_POPULATION_PATH
EXISTING_IDENTIFIERS_PATH = SPOTIFY_IDENTIFIERS_PATH
RAW_SPOTIFY_DIR = SPOTIFY_RAW_DIR
INTERIM_DIR = INTERIM_DATA_DIR
PROCESSED_DIR = PROCESSED_DATA_DIR

REQUIRED_CATALOG_COLUMNS = {
    "band_name",
    "original_city_label",
    "musicbrainz_id",
    "origin_confidence",
    "origin_evidence_url",
    "editorial_review_flag",
    "notes",
}


def _load_catalog(path: Path) -> pd.DataFrame:
    catalog = pd.read_csv(path, keep_default_na=False)
    missing = sorted(REQUIRED_CATALOG_COLUMNS.difference(catalog.columns))
    if missing:
        raise ValueError(f"Scene-depth catalogue is missing columns: {missing}")
    if len(catalog) != 100:
        raise ValueError(f"Expected 100 scene-depth bands, found {len(catalog)}")
    if catalog["band_name"].duplicated().any():
        duplicates = catalog.loc[
            catalog["band_name"].duplicated(keep=False),
            "band_name",
        ].tolist()
        raise ValueError(f"Scene-depth band names must be unique: {duplicates}")
    city_counts = catalog.groupby("original_city_label").size()
    if len(city_counts) != 10 or not (city_counts == 10).all():
        observed = ", ".join(
            f"{city}={count}" for city, count in city_counts.items()
        )
        raise ValueError(f"Expected ten bands in each of ten cities; {observed}")
    invalid_confidence = sorted(
        set(catalog["origin_confidence"]) - {"high", "medium", "low"}
    )
    if invalid_confidence:
        raise ValueError(f"Unknown origin confidence values: {invalid_confidence}")
    return catalog


def _load_existing_identifiers(
    reuse_identifiers_path: Path | None = None,
) -> dict[str, dict]:
    rows = json.loads(EXISTING_IDENTIFIERS_PATH.read_text())
    existing = {row["band"]: row for row in rows}
    if reuse_identifiers_path:
        prior = pd.read_csv(reuse_identifiers_path, keep_default_na=False)
        existing.update(
            {
                row["band"]: {
                    **row.to_dict(),
                    "id_source": "prior scene-depth identifier snapshot",
                }
                for _, row in prior.iterrows()
            }
        )
    return existing


def _resolve_identifiers(
    catalog: pd.DataFrame,
    *,
    musicbrainz_throttle: float,
    reuse_identifiers_path: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    existing = _load_existing_identifiers(reuse_identifiers_path)
    resolved: list[dict] = []
    failures: list[dict] = []
    total = len(catalog)

    for position, row in enumerate(catalog.itertuples(index=False), start=1):
        supplied_url = getattr(row, "spotify_url", "") or ""
        expected_spotify_name = (
            getattr(row, "spotify_match_name", "") or row.band_name
        )
        prior = existing.get(row.band_name)
        if prior and not supplied_url:
            resolved.append(
                {
                    "band": row.band_name,
                    "city": row.original_city_label,
                    "musicbrainz_id": row.musicbrainz_id or None,
                    "spotify_id": prior["spotify_id"],
                    "spotify_name": prior.get("spotify_name"),
                    "expected_spotify_name": expected_spotify_name,
                    "match_quality": prior.get("match_quality", "reviewed_existing"),
                    "id_source": prior.get(
                        "id_source",
                        "existing reviewed 50-band cache",
                    ),
                }
            )
            continue

        spotify_url = supplied_url or None
        if not spotify_url and row.musicbrainz_id:
            try:
                spotify_url = fetch_musicbrainz_spotify_url(row.musicbrainz_id)
            except requests.RequestException as exc:
                failures.append(
                    {
                        "band": row.band_name,
                        "city": row.original_city_label,
                        "stage": "musicbrainz_relationship",
                        "error": str(exc),
                    }
                )
            time.sleep(max(musicbrainz_throttle, 0))

        spotify_id = spotify_artist_id_from_url(spotify_url)
        if not spotify_id:
            failures.append(
                {
                    "band": row.band_name,
                    "city": row.original_city_label,
                    "stage": "spotify_id",
                    "error": "No reviewed Spotify artist relationship",
                }
            )
        else:
            resolved.append(
                {
                    "band": row.band_name,
                    "city": row.original_city_label,
                    "musicbrainz_id": row.musicbrainz_id or None,
                    "spotify_id": spotify_id,
                    "spotify_name": None,
                    "expected_spotify_name": expected_spotify_name,
                    "match_quality": "musicbrainz_relationship",
                    "id_source": (
                        "catalogue override"
                        if supplied_url
                        else "MusicBrainz Spotify relationship"
                    ),
                }
            )

        if position % 10 == 0 or position == total:
            print(
                f"Resolved Spotify IDs for {position}/{total} catalogue rows",
                flush=True,
            )

    return resolved, failures


def _validate_public_matches(
    identifiers: list[dict],
    metrics: list[dict],
) -> list[dict]:
    identifiers_by_band = {row["band"]: row for row in identifiers}
    review: list[dict] = []
    for row in metrics:
        identifier = identifiers_by_band[row["band"]]
        confidence = infer_match_confidence(
            identifier.get("expected_spotify_name") or row["band"],
            row.get("spotify_name") or "",
            is_first_result=False,
        )
        row["match_quality"] = confidence
        row["id_source"] = identifier["id_source"]
        if confidence != "exact":
            review.append(
                {
                    "band": row["band"],
                    "spotify_name": row.get("spotify_name"),
                    "spotify_id": row["spotify_id"],
                    "match_quality": confidence,
                }
            )
    return review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--musicbrainz-throttle",
        type=float,
        default=1.0,
        help="Seconds between MusicBrainz relationship requests",
    )
    parser.add_argument(
        "--spotify-throttle",
        type=float,
        default=0.2,
        help="Seconds between public Spotify artist-page requests",
    )
    parser.add_argument(
        "--reuse-identifiers",
        type=Path,
        help=(
            "Optional prior scene-depth identifier CSV. Catalogue Spotify URL "
            "overrides still take precedence."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = _load_catalog(args.catalog)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    RAW_SPOTIFY_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    identifiers_path = INTERIM_DIR / f"scene_depth_spotify_ids_{timestamp}.csv"
    metrics_path = RAW_SPOTIFY_DIR / f"scene_depth_metrics_{timestamp}.json"
    report_path = RAW_SPOTIFY_DIR / f"scene_depth_metrics_{timestamp}_report.json"
    band_metrics_path = PROCESSED_DIR / f"scene_depth_band_metrics_{timestamp}.csv"
    rankings_path = PROCESSED_DIR / f"scene_depth_rankings_{timestamp}.csv"

    identifiers, identifier_failures = _resolve_identifiers(
        catalog,
        musicbrainz_throttle=args.musicbrainz_throttle,
        reuse_identifiers_path=args.reuse_identifiers,
    )
    write_csv(pd.DataFrame(identifiers), identifiers_path)

    metrics, metric_failures = fetch_public_spotify_metrics(
        identifiers,
        throttle_seconds=max(args.spotify_throttle, 0),
    )
    match_review = _validate_public_matches(identifiers, metrics)
    write_json(metrics, metrics_path)

    report = {
        "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_path": str(args.catalog.relative_to(PROJECT_ROOT)),
        "expected_rows": len(catalog),
        "identifier_rows": len(identifiers),
        "metric_rows": len(metrics),
        "identifier_failures": identifier_failures,
        "metric_failures": metric_failures,
        "match_review": match_review,
        "ranking_ready": False,
        "canonical_50_band_files_modified": False,
    }

    if (
        len(identifiers) != len(catalog)
        or len(metrics) != len(catalog)
        or identifier_failures
        or metric_failures
        or match_review
    ):
        write_json(report, report_path)
        print(
            "Scene-depth ranking not built: resolve every ID, metric, and "
            "name-match review first.",
            flush=True,
        )
        print(f"Report: {report_path}", flush=True)
        return 2

    metrics_frame = pd.DataFrame(metrics)
    populations = pd.read_csv(POPULATIONS_PATH)
    population_labels = catalog["original_city_label"].replace(
        {"Bradford": "Leeds"}
    )
    catalog = catalog.assign(population_geography=population_labels)
    analysis = (
        catalog.rename(
            columns={
                "band_name": "band",
                "original_city_label": "city",
            }
        )
        .merge(metrics_frame, on=["band", "city"], validate="one_to_one")
        .merge(
            populations[["study_city_label", "population"]],
            left_on="population_geography",
            right_on="study_city_label",
            validate="many_to_one",
        )
        .drop(columns=["study_city_label"])
    )
    write_csv(analysis, band_metrics_path)

    rankings = build_scene_depth_rankings(
        analysis,
        metric="monthly_listeners",
        trim_each_tail=1,
        expected_cities=10,
        bands_per_city=10,
    )
    write_csv(rankings, rankings_path)
    report["ranking_ready"] = True
    report["band_metrics_path"] = str(band_metrics_path.relative_to(PROJECT_ROOT))
    report["rankings_path"] = str(rankings_path.relative_to(PROJECT_ROOT))
    write_json(report, report_path)

    print(f"Scene-depth metrics: {band_metrics_path}", flush=True)
    print(f"Scene-depth rankings: {rankings_path}", flush=True)
    print(f"Report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
