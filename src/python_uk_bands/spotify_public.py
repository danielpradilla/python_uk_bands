"""Read-only helpers for the isolated scene-depth Spotify snapshot.

These helpers use public artist pages and MusicBrainz URL relationships. They
do not modify or promote the canonical 50-band Spotify caches.
"""

from __future__ import annotations

from datetime import datetime, timezone
import html
import re
import time
from typing import Callable, Iterable
from urllib.parse import urlparse

import requests

from .config import DEFAULT_MUSICBRAINZ_USER_AGENT


SPOTIFY_ARTIST_URL = "https://open.spotify.com/artist/{spotify_id}"
MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist/{musicbrainz_id}"
PUBLIC_PAGE_USER_AGENT = "Mozilla/5.0"


def spotify_artist_id_from_url(url: str | None) -> str | None:
    """Extract a Spotify artist ID from a canonical artist URL."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc not in {"open.spotify.com", "play.spotify.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "artist":
        return None
    spotify_id = parts[1]
    return spotify_id if re.fullmatch(r"[A-Za-z0-9]+", spotify_id) else None


def spotify_artist_url_from_musicbrainz_payload(payload: dict) -> str | None:
    """Return the first Spotify artist relationship from MusicBrainz."""
    for relation in payload.get("relations", []):
        resource = ((relation.get("url") or {}).get("resource") or "").strip()
        if spotify_artist_id_from_url(resource):
            return resource
    return None


def fetch_musicbrainz_spotify_url(
    musicbrainz_id: str,
    *,
    request_get: Callable = requests.get,
    timeout: float = 20,
) -> str | None:
    """Resolve a reviewed MusicBrainz artist to its related Spotify URL."""
    response = request_get(
        MUSICBRAINZ_ARTIST_URL.format(musicbrainz_id=musicbrainz_id),
        params={"inc": "url-rels", "fmt": "json"},
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_MUSICBRAINZ_USER_AGENT,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return spotify_artist_url_from_musicbrainz_payload(response.json())


def parse_public_spotify_artist_page(page_html: str) -> dict:
    """Extract public artist metrics from Spotify page HTML."""
    title_match = re.search(
        r'<meta\s+property="og:title"\s+content="([^"]*)"',
        page_html,
        flags=re.IGNORECASE,
    )
    listeners_match = re.search(
        r'data-testid="monthly-listeners-label"[^>]*>'
        r"\s*([\d,.]+)\s+monthly listeners",
        page_html,
        flags=re.IGNORECASE,
    )
    if not listeners_match:
        listeners_match = re.search(
            r'<meta\s+property="og:description"\s+content="[^"]*'
            r"[\s·]([\d,.]+)\s+monthly listeners",
            page_html,
            flags=re.IGNORECASE,
        )
    if not listeners_match:
        raise ValueError("Public Spotify page has no exact monthly-listener count")

    followers_match = re.search(
        r">\s*([\d,.]+)\s*</p>\s*<p[^>]*>\s*Followers\s*</p>",
        page_html,
        flags=re.IGNORECASE,
    )
    normalized = listeners_match.group(1).replace(",", "").replace(".", "")
    return {
        "spotify_name": html.unescape(title_match.group(1)) if title_match else None,
        "monthly_listeners": int(normalized),
        "followers": (
            int(followers_match.group(1).replace(",", "").replace(".", ""))
            if followers_match
            else None
        ),
    }


def fetch_public_spotify_metrics(
    records: Iterable[dict],
    *,
    request_get: Callable = requests.get,
    timeout: float = 20,
    throttle_seconds: float = 0.2,
) -> tuple[list[dict], list[dict]]:
    """Fetch public monthly-listener values for reviewed Spotify artist IDs."""
    rows: list[dict] = []
    failures: list[dict] = []
    fetched_at = datetime.now(timezone.utc).date().isoformat()

    for index, record in enumerate(records):
        spotify_id = record.get("spotify_id")
        if not spotify_id:
            failures.append(
                {
                    "band": record.get("band"),
                    "error": "missing_spotify_id",
                }
            )
            continue
        try:
            response = request_get(
                SPOTIFY_ARTIST_URL.format(spotify_id=spotify_id),
                headers={
                    "User-Agent": PUBLIC_PAGE_USER_AGENT,
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            parsed = parse_public_spotify_artist_page(response.text)
            rows.append(
                {
                    "band": record["band"],
                    "city": record["city"],
                    "spotify_id": spotify_id,
                    "spotify_name": parsed["spotify_name"],
                    "monthly_listeners": parsed["monthly_listeners"],
                    "followers": parsed["followers"],
                    "stats_extracted_at": fetched_at,
                    "source": "Spotify public artist page",
                }
            )
        except (requests.RequestException, ValueError) as exc:
            failures.append(
                {
                    "band": record.get("band"),
                    "spotify_id": spotify_id,
                    "error": str(exc),
                }
            )

        if throttle_seconds and index:
            time.sleep(throttle_seconds)

    return rows, failures
