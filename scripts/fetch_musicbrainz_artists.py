#!/usr/bin/env python3
"""Fetch UK band candidates from MusicBrainz and write raw snapshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.musicbrainz import MBFetchConfig, fetch_musicbrainz_artists, save_musicbrainz_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="country:GB", help='MusicBrainz Lucene query, default: "country:GB"')
    parser.add_argument(
        "--include-type",
        dest="include_types",
        action="append",
        default=["Group"],
        help='Artist type to include, repeatable. Default: "Group"',
    )
    parser.add_argument("--min-relevance", type=int, default=65, help="Minimum MusicBrainz relevance score")
    parser.add_argument("--batch-size", type=int, default=100, help="Page size per MusicBrainz request")
    parser.add_argument("--max-artists", type=int, default=2000, help="Maximum artists to collect")
    parser.add_argument("--max-offset-pages", type=int, default=50, help="Maximum MusicBrainz pages to request")
    parser.add_argument("--throttle-seconds", type=float, default=0.5, help="Delay multiplier between requests")
    parser.add_argument("--request-attempts", type=int, default=3, help="Retry attempts per request")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    include_types = tuple(dict.fromkeys(args.include_types))
    config = MBFetchConfig(
        query=args.query,
        include_types=include_types,
        min_relevance=args.min_relevance,
        batch_size=args.batch_size,
        max_artists=args.max_artists,
        throttle_seconds=args.throttle_seconds,
        request_attempts=args.request_attempts,
        max_offset_pages=args.max_offset_pages,
    )
    records, metadata = fetch_musicbrainz_artists(config)
    snapshot_path, latest_path = save_musicbrainz_snapshot(records, metadata, config)
    print(f"Fetched {len(records)} artists from MusicBrainz")
    print(f"Snapshot: {snapshot_path}")
    print(f"Latest:   {latest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
