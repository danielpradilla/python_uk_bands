#!/usr/bin/env python3
"""Capture dated Spotify artist-overview metrics for an identifier table.

The collector reads Spotify's own web-player endpoint. It never promotes or
overwrites canonical data. Missing identifiers can be resolved only when the
search result contains exactly one exact-name match.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
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

from python_uk_bands.io import write_csv, write_json
from python_uk_bands.matching import normalize_name
from python_uk_bands.spotify_partner import (
    fetch_artist_overview,
    fetch_embed_access_token,
    search_artist_candidates,
)


def _project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def _write_gzip_json(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle)


def _exact_search_match(band_name: str, candidates: list[dict]) -> dict | None:
    exact = [
        candidate
        for candidate in candidates
        if normalize_name(candidate.get("spotify_name"))
        == normalize_name(band_name)
    ]
    unique = {
        candidate["spotify_id"]: candidate
        for candidate in exact
        if candidate.get("spotify_id")
    }
    return next(iter(unique.values())) if len(unique) == 1 else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--band-column", default="band_name")
    parser.add_argument("--city-column", default="study_city_label")
    parser.add_argument("--spotify-id-column", default="spotify_id")
    parser.add_argument(
        "--expected-name-column",
        default="spotify_expected_name",
        help="Optional reviewed Spotify display-name column",
    )
    parser.add_argument(
        "--search-missing",
        action="store_true",
        help="Resolve a missing ID only from one unique exact-name result",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--search-throttle", type=float, default=0.3)
    parser.add_argument("--timeout", type=float, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    frame = pd.read_csv(args.input, keep_default_na=False)
    required = {args.band_column, args.spotify_id_column}
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"Input is missing columns: {missing_columns}")
    if frame[args.band_column].duplicated().any():
        raise ValueError("Input band names must be unique")

    captured_at = datetime.now(timezone.utc)
    timestamp = captured_at.strftime("%Y%m%dT%H%M%SZ")
    raw_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "spotify"
        / f"{args.output_prefix}_{timestamp}.json.gz"
    )
    metrics_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"{args.output_prefix}_{timestamp}.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "spotify"
        / f"{args.output_prefix}_{timestamp}_report.json"
    )

    access_token, token_expiry = fetch_embed_access_token(timeout=args.timeout)
    records = frame.to_dict("records")
    search_payloads: dict[str, dict] = {}
    search_failures: list[dict] = []

    if args.search_missing:
        for position, record in enumerate(records, start=1):
            if record.get(args.spotify_id_column):
                continue
            band_name = record[args.band_column]
            try:
                candidates, raw = search_artist_candidates(
                    band_name,
                    access_token=access_token,
                    timeout=args.timeout,
                )
                search_payloads[band_name] = raw
                match = _exact_search_match(band_name, candidates)
                if match:
                    record[args.spotify_id_column] = match["spotify_id"]
                else:
                    search_failures.append(
                        {
                            "band": band_name,
                            "error": "no_unique_exact_name_result",
                            "exact_candidates": [
                                candidate
                                for candidate in candidates
                                if normalize_name(candidate.get("spotify_name"))
                                == normalize_name(band_name)
                            ],
                        }
                    )
            except (requests.RequestException, ValueError) as exc:
                search_failures.append(
                    {"band": band_name, "error": str(exc)}
                )
            time.sleep(max(args.search_throttle, 0))
            if position % 25 == 0:
                print(f"Searched through input row {position}", flush=True)

    raw_overviews: dict[str, dict] = {}
    rows: list[dict] = []
    metric_failures: list[dict] = []

    def fetch(record: dict) -> tuple[dict, dict]:
        spotify_id = record.get(args.spotify_id_column)
        if not spotify_id:
            raise ValueError("missing_spotify_id")
        compact, raw = fetch_artist_overview(
            spotify_id,
            access_token=access_token,
            timeout=args.timeout,
        )
        return (
            {
                "band": record[args.band_column],
                "city": (
                    record.get(args.city_column)
                    if args.city_column in frame.columns
                    else ""
                ),
                **compact,
                "stats_extracted_at_utc": captured_at.isoformat(),
                "source": "Spotify web-player queryArtistOverview",
                "source_access": "undocumented read-only web-client endpoint",
            },
            raw,
        )

    with ThreadPoolExecutor(max_workers=max(args.workers, 1)) as executor:
        future_records = {
            executor.submit(fetch, record): record
            for record in records
            if record.get(args.spotify_id_column)
        }
        completed = 0
        for future in as_completed(future_records):
            record = future_records[future]
            band_name = record[args.band_column]
            try:
                row, raw = future.result()
                rows.append(row)
                raw_overviews[band_name] = raw
            except (requests.RequestException, ValueError) as exc:
                metric_failures.append(
                    {
                        "band": band_name,
                        "spotify_id": record.get(args.spotify_id_column),
                        "error": str(exc),
                    }
                )
            completed += 1
            if completed % 25 == 0 or completed == len(future_records):
                print(
                    f"Fetched {completed}/{len(future_records)} artist overviews",
                    flush=True,
                )

    rows.sort(key=lambda row: (row["city"], row["band"]))
    metrics = pd.DataFrame(rows)
    write_csv(metrics, metrics_path)
    _write_gzip_json(
        {
            "captured_at_utc": captured_at.isoformat(),
            "input_path": _project_relative(args.input),
            "token_expiration_timestamp_ms": token_expiry,
            "search_responses": search_payloads,
            "artist_overviews": raw_overviews,
        },
        raw_path,
    )
    name_review = []
    if not metrics.empty:
        expected = frame.set_index(args.band_column)
        for row in metrics.to_dict("records"):
            expected_name = row["band"]
            if args.expected_name_column in frame.columns:
                expected_name = expected.at[
                    row["band"],
                    args.expected_name_column,
                ] or row["band"]
            if normalize_name(expected_name) != normalize_name(
                row["spotify_name"]
            ):
                name_review.append(
                    {
                        "band": row["band"],
                        "expected_spotify_name": expected_name,
                        "spotify_name": row["spotify_name"],
                        "spotify_id": row["spotify_id"],
                    }
                )
    report = {
        "captured_at_utc": captured_at.isoformat(),
        "input_path": _project_relative(args.input),
        "input_rows": len(frame),
        "resolved_identifier_rows": sum(
            bool(record.get(args.spotify_id_column)) for record in records
        ),
        "metrics_rows": len(metrics),
        "search_failures": search_failures,
        "metric_failures": metric_failures,
        "name_review": name_review,
        "complete": (
            len(metrics) == len(frame)
            and not search_failures
            and not metric_failures
            and not name_review
        ),
        "raw_path": str(raw_path.relative_to(PROJECT_ROOT)),
        "metrics_path": str(metrics_path.relative_to(PROJECT_ROOT)),
        "canonical_files_modified": False,
    }
    write_json(report, report_path)
    print(f"Metrics: {metrics_path.relative_to(PROJECT_ROOT)}")
    print(f"Raw responses: {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
