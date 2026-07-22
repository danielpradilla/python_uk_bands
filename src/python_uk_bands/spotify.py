"""Spotify fetch and normalization logic."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

from .config import INTERIM_DATA_DIR, PROJECT_ROOT, SPOTIFY_RAW_DIR
from .io import read_json, write_csv, write_json
from .matching import pick_best_candidate


@dataclass
class SpotifyResolveConfig:
    """Parameters for resolving MusicBrainz artists to Spotify artists."""

    search_limit: int = 5


def get_spotify_client() -> spotipy.Spotify:
    """Create an authenticated Spotify client from local environment variables."""
    load_dotenv(PROJECT_ROOT / ".env")
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET in environment/.env")
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth)


def load_musicbrainz_snapshot(path: Path) -> tuple[pd.DataFrame, dict]:
    """Load a MusicBrainz snapshot JSON written by the new fetch script."""
    payload = read_json(path)
    return pd.DataFrame(payload["records"]), payload["metadata"]


def _spotify_snapshot_slug(snapshot_path: Path, search_limit: int) -> str:
    value = f"{snapshot_path.name}||{search_limit}"
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def build_spotify_output_paths(snapshot_path: Path, search_limit: int) -> tuple[Path, Path, Path]:
    """Return timestamped raw snapshot path, stable latest path, and interim CSV path."""
    slug = _spotify_snapshot_slug(snapshot_path, search_limit)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_snapshot = SPOTIFY_RAW_DIR / f"artist_matches_{slug}_{timestamp}.json"
    raw_latest = SPOTIFY_RAW_DIR / f"artist_matches_{slug}_latest.json"
    interim_csv = INTERIM_DATA_DIR / "spotify_matches.csv"
    return raw_snapshot, raw_latest, interim_csv


def resolve_spotify_artists(
    musicbrainz_artists: pd.DataFrame,
    spotify_client: spotipy.Spotify,
    config: SpotifyResolveConfig,
) -> tuple[pd.DataFrame, dict]:
    """Resolve MusicBrainz artists to Spotify artist candidates."""
    rows: list[dict] = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for row in musicbrainz_artists.itertuples(index=False):
        try:
            result = spotify_client.search(q=f'artist:"{row.name}"', type="artist", limit=config.search_limit)
        except SpotifyException as exc:
            raise RuntimeError(
                "Spotify artist resolution failed. The current app credentials do not have access to "
                "artist search. Keep using the existing cached Spotify data until the app/account access "
                "is fixed, then rerun scripts/resolve_spotify_artists.py."
            ) from exc
        items = result.get("artists", {}).get("items", [])
        best, match_confidence = pick_best_candidate(row.name, items)
        candidate_names = " | ".join(item.get("name", "") for item in items[: config.search_limit])
        rows.append(
            {
                "musicbrainz_id": row.musicbrainz_id,
                "band_name": row.name,
                "musicbrainz_type": row.type,
                "origin_raw": row.city,
                "country": row.country,
                "musicbrainz_score": row.score,
                "spotify_id": best.get("id") if best else None,
                "spotify_name": best.get("name") if best else None,
                "spotify_followers": ((best.get("followers") or {}).get("total") if best else None),
                "spotify_popularity": best.get("popularity") if best else None,
                "spotify_match_confidence": match_confidence,
                "candidate_names": candidate_names,
                "review_required": match_confidence != "exact",
                "fetched_at_utc": fetched_at,
            }
        )

    metadata = {
        "fetched_at_utc": fetched_at,
        "search_limit": config.search_limit,
        "returned_count": len(rows),
    }
    return pd.DataFrame(rows), metadata


def save_spotify_resolution(
    resolved_artists: pd.DataFrame,
    metadata: dict,
    *,
    source_snapshot: Path,
    search_limit: int,
) -> tuple[Path, Path, Path]:
    """Write raw snapshot JSON and a reviewable CSV for Spotify matches."""
    raw_snapshot, raw_latest, interim_csv = build_spotify_output_paths(source_snapshot, search_limit)
    payload = {
        "metadata": {**metadata, "source_snapshot": str(source_snapshot)},
        "records": resolved_artists.to_dict(orient="records"),
    }
    write_json(payload, raw_snapshot)
    write_json(payload, raw_latest)
    write_csv(resolved_artists, interim_csv)
    return raw_snapshot, raw_latest, interim_csv
