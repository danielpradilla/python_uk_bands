#!/usr/bin/env python3
"""Resolve MusicBrainz artist records to Spotify artist candidates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import MUSICBRAINZ_RAW_DIR
from python_uk_bands.spotify import (
    SpotifyResolveConfig,
    get_spotify_client,
    load_musicbrainz_snapshot,
    resolve_spotify_artists,
    save_spotify_resolution,
)


def default_musicbrainz_snapshot() -> Path:
    """Pick the most recent stable MusicBrainz snapshot if available."""
    candidates = sorted(MUSICBRAINZ_RAW_DIR.glob("artists_*_latest.json"))
    if candidates:
        return candidates[-1]
    return MUSICBRAINZ_RAW_DIR / "artists_latest.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=default_musicbrainz_snapshot(),
        help="Path to a MusicBrainz snapshot JSON",
    )
    parser.add_argument("--search-limit", type=int, default=5, help="Spotify search result limit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    musicbrainz_artists, source_metadata = load_musicbrainz_snapshot(args.source)
    spotify_client = get_spotify_client()
    config = SpotifyResolveConfig(search_limit=args.search_limit)
    resolved_artists, metadata = resolve_spotify_artists(musicbrainz_artists, spotify_client, config)
    metadata["source_musicbrainz_query"] = source_metadata.get("query")
    raw_snapshot, raw_latest, interim_csv = save_spotify_resolution(
        resolved_artists,
        metadata,
        source_snapshot=args.source,
        search_limit=args.search_limit,
    )
    print(f"Resolved {len(resolved_artists)} artists to Spotify candidates")
    print(f"Raw snapshot: {raw_snapshot}")
    print(f"Latest raw:   {raw_latest}")
    print(f"Review CSV:   {interim_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
