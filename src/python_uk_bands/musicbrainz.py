"""MusicBrainz fetch and normalization logic."""

from __future__ import annotations

import functools
import hashlib
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import pycountry
import requests

from .config import (
    DEFAULT_MUSICBRAINZ_USER_AGENT,
    MUSICBRAINZ_API_LIMIT,
    MUSICBRAINZ_AREA_ENDPOINT,
    MUSICBRAINZ_ARTIST_ENDPOINT,
    MUSICBRAINZ_RAW_DIR,
)
from .io import write_json

MUSICBRAINZ_HEADERS = {"User-Agent": DEFAULT_MUSICBRAINZ_USER_AGENT}

ALLOWED_CITY_AREA_TYPES = {
    "borough",
    "city",
    "city district",
    "civil parish",
    "commune",
    "district borough",
    "locality",
    "london borough",
    "metropolitan area",
    "metropolitan borough",
    "municipality",
    "region/city",
    "suburb",
    "town",
    "urban district",
    "village",
}

DISALLOWED_AREA_TYPES = {
    "country",
    "county",
    "district",
    "province",
    "region",
    "state",
    "subdivision",
    "unitary authority",
}


@dataclass
class MBFetchConfig:
    """Parameters for fetching candidate artists from MusicBrainz."""

    query: str = "country:GB"
    include_types: tuple[str, ...] = ("Group",)
    min_relevance: int | None = 65
    batch_size: int = 100
    max_artists: int = 2000
    throttle_seconds: float = 0.5
    request_attempts: int = 3
    max_offset_pages: int | None = 50

    def query_string(self) -> str:
        """Compose the Lucene query for MusicBrainz."""
        type_clause = " OR ".join(f'type:"{value}"' for value in self.include_types)
        if not type_clause:
            return self.query
        return f"{self.query} AND ({type_clause})"


def _cache_slug(parts: Iterable[str]) -> str:
    joined = "||".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:10]


def build_snapshot_paths(config: MBFetchConfig) -> tuple[Path, Path]:
    """Return a timestamped snapshot path and a stable latest path."""
    slug = _cache_slug(
        [
            config.query_string(),
            ",".join(config.include_types),
            str(config.min_relevance),
            str(config.max_artists),
            str(config.batch_size),
        ]
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = MUSICBRAINZ_RAW_DIR / f"artists_{slug}_{timestamp}.json"
    latest = MUSICBRAINZ_RAW_DIR / f"artists_{slug}_latest.json"
    return snapshot, latest


def _resolve_country_name(artist: dict) -> str | None:
    area = artist.get("area") or {}
    area_type = (area.get("type") or "").lower()
    area_name = (area.get("name") or "").strip()
    if area_name and area_type == "country":
        return area_name

    country_code = (artist.get("country") or "").strip()
    if country_code:
        try:
            return pycountry.countries.lookup(country_code).name
        except LookupError:
            return area_name or None
    return area_name or None


def _is_country_match(name: str, country_name: str | None) -> bool:
    return bool(name and country_name and name.lower() == country_name.strip().lower())


@functools.lru_cache(maxsize=2048)
def _fetch_area_details(area_id: str, attempts: int = 3, backoff_base: float = 1.0) -> dict:
    for attempt in range(attempts):
        try:
            response = requests.get(
                f"{MUSICBRAINZ_AREA_ENDPOINT}/{area_id}",
                params={"fmt": "json", "inc": "area-rels"},
                headers=MUSICBRAINZ_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status and status >= 500 and attempt < attempts - 1:
                time.sleep(backoff_base * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"Unable to fetch area details for {area_id} after {attempts} attempts")


def _resolve_city_from_area(area_dict: dict | None, country_name: str | None, depth: int = 0) -> str | None:
    if not isinstance(area_dict, dict):
        return None

    area_id = area_dict.get("id")
    area_name = (area_dict.get("name") or "").strip()
    area_type = (area_dict.get("type") or "").lower()

    if area_name and not _is_country_match(area_name, country_name):
        if area_type in ALLOWED_CITY_AREA_TYPES or (not area_type and country_name):
            return area_name
        if not area_type and not country_name:
            return area_name
    if area_type and area_type in DISALLOWED_AREA_TYPES:
        pass
    elif area_name and not area_type and not _is_country_match(area_name, country_name):
        return area_name

    if not area_id or depth > 6:
        return None

    try:
        details = _fetch_area_details(area_id)
    except requests.RequestException as exc:
        warnings.warn(
            f"MusicBrainz area lookup failed for {area_id}; leaving city unresolved ({exc})",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    candidate_name = (details.get("name") or area_name).strip()
    candidate_type = (details.get("type") or area_type).lower()

    if candidate_name and not _is_country_match(candidate_name, country_name):
        if candidate_type in ALLOWED_CITY_AREA_TYPES or (not candidate_type and country_name):
            return candidate_name
        if not candidate_type and not country_name:
            return candidate_name

    for relation in details.get("relations", []):
        if relation.get("type") != "part of":
            continue
        direction = relation.get("direction")
        if direction and direction.lower() == "forward":
            continue
        resolved = _resolve_city_from_area(relation.get("area"), country_name, depth + 1)
        if resolved:
            return resolved
    return None


def _extract_musicbrainz_city(artist: dict, country_name: str | None) -> tuple[str | None, dict | None]:
    city_from_area = _resolve_city_from_area(artist.get("area"), country_name)
    if city_from_area:
        return city_from_area, None

    city_from_begin = _resolve_city_from_area(artist.get("begin-area"), country_name)
    if city_from_begin:
        return city_from_begin, None

    begin_area = artist.get("begin-area") or {}
    begin_area_name = (begin_area.get("name") or "").strip()
    begin_area_type = (begin_area.get("type") or "").lower()
    if begin_area_name and (
        begin_area_type in ALLOWED_CITY_AREA_TYPES or not begin_area_type
    ):
        if _is_country_match(begin_area_name, country_name):
            return None, {"reason": "begin_area_matches_country", "label": begin_area_name}
        return begin_area_name, None
    return None, None


def _filter_by_relevance(artists: list[dict], min_relevance: int | None) -> list[dict]:
    if min_relevance is None:
        return artists
    return [artist for artist in artists if (artist.get("score") or 0) >= min_relevance]


def _musicbrainz_request(params: dict, *, attempts: int, throttle: float, offset: int, collected: int) -> dict:
    for attempt in range(attempts):
        if throttle and (offset > 0 or collected > 0 or attempt > 0):
            time.sleep(throttle * (attempt + 1))
        try:
            response = requests.get(
                MUSICBRAINZ_ARTIST_ENDPOINT,
                params=params,
                headers=MUSICBRAINZ_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status and status >= 500 and attempt < attempts - 1:
                time.sleep(max(throttle, 0.5) * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"MusicBrainz request failed after {attempts} attempts (offset={offset})")


def fetch_musicbrainz_artists(config: MBFetchConfig) -> tuple[pd.DataFrame, dict]:
    """Fetch candidate artists from MusicBrainz and return both rows and metadata."""
    batch_size = min(config.batch_size, MUSICBRAINZ_API_LIMIT)
    collected: list[dict] = []
    offset = 0
    total_available = None
    pages_fetched = 0

    while len(collected) < config.max_artists:
        if config.max_offset_pages is not None and pages_fetched >= config.max_offset_pages:
            break

        remaining = config.max_artists - len(collected)
        params = {
            "query": config.query_string(),
            "fmt": "json",
            "limit": min(batch_size, remaining),
            "offset": offset,
        }
        payload = _musicbrainz_request(
            params,
            attempts=config.request_attempts,
            throttle=config.throttle_seconds,
            offset=offset,
            collected=len(collected),
        )
        pages_fetched += 1

        if total_available is None:
            total_available = payload.get("count")

        artists = _filter_by_relevance(payload.get("artists", []), config.min_relevance)
        if not artists:
            break

        for artist in artists:
            country_name = _resolve_country_name(artist)
            city_name, skip_info = _extract_musicbrainz_city(artist, country_name)
            if skip_info:
                continue
            collected.append(
                {
                    "musicbrainz_id": artist.get("id"),
                    "name": artist.get("name"),
                    "type": artist.get("type"),
                    "disambiguation": artist.get("disambiguation"),
                    "city": city_name,
                    "country": country_name,
                    "life_span_begin": (artist.get("life-span") or {}).get("begin"),
                    "life_span_end": bool((artist.get("life-span") or {}).get("ended")),
                    "score": artist.get("score"),
                    "source_query": config.query_string(),
                }
            )
            if len(collected) >= config.max_artists:
                break

        offset += params["limit"]
        if len(payload.get("artists", [])) < params["limit"]:
            break

    deduped = pd.DataFrame(collected).drop_duplicates(subset=["musicbrainz_id"]).reset_index(drop=True)
    metadata = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": config.query_string(),
        "include_types": list(config.include_types),
        "min_relevance": config.min_relevance,
        "batch_size": batch_size,
        "max_artists": config.max_artists,
        "pages_fetched": pages_fetched,
        "total_available": total_available,
        "returned_count": len(deduped),
    }
    return deduped, metadata


def save_musicbrainz_snapshot(records: pd.DataFrame, metadata: dict, config: MBFetchConfig) -> tuple[Path, Path]:
    """Persist a fetch snapshot and overwrite the stable latest file."""
    snapshot_path, latest_path = build_snapshot_paths(config)
    payload = {
        "metadata": metadata,
        "records": records.to_dict(orient="records"),
    }
    write_json(payload, snapshot_path)
    write_json(payload, latest_path)
    return snapshot_path, latest_path
