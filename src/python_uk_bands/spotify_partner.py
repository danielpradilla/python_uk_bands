"""Read-only access to Spotify's web-player artist overview.

This is an undocumented endpoint used by Spotify's own web client. It is kept
separate from the supported Web API and public-page parser so snapshots can
state their exact collection method and the endpoint can fail without changing
canonical data.
"""

from __future__ import annotations

import json
import re
from typing import Callable

import requests


EMBED_ARTIST_URL = "https://open.spotify.com/embed/artist/{spotify_id}"
PATHFINDER_URL = "https://api-partner.spotify.com/pathfinder/v1/query"
ARTIST_OVERVIEW_HASH = (
    "433e28d1e949372d3ca3aa6c47975cff428b5dc37b12f5325d9213accadf770a"
)
ARTIST_SEARCH_HASH = (
    "0dff51c99e552b992377a2a6f40d213dc42b62db86ca0bcf16cf3934aec1aae6"
)
TOKEN_PROBE_ARTIST_ID = "4Z8W4fKeB5YxbusRsdQVPb"


def parse_embed_access_token(page_html: str) -> tuple[str, int | None]:
    """Extract the anonymous session token embedded in Spotify's player HTML."""
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        page_html,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("Spotify embed page is missing __NEXT_DATA__")
    payload = json.loads(match.group(1))
    session = payload["props"]["pageProps"]["state"]["settings"]["session"]
    token = session.get("accessToken")
    if not token:
        raise ValueError("Spotify embed page is missing an access token")
    return token, session.get("accessTokenExpirationTimestampMs")


def fetch_embed_access_token(
    *,
    request_get: Callable = requests.get,
    timeout: float = 30,
    probe_artist_id: str = TOKEN_PROBE_ARTIST_ID,
) -> tuple[str, int | None]:
    """Fetch a short-lived anonymous token from Spotify's embed player."""
    response = request_get(
        EMBED_ARTIST_URL.format(spotify_id=probe_artist_id),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_embed_access_token(response.text)


def _pathfinder_query(
    *,
    operation_name: str,
    variables: dict,
    sha256_hash: str,
    access_token: str,
    request_get: Callable = requests.get,
    timeout: float = 30,
) -> dict:
    response = request_get(
        PATHFINDER_URL,
        params={
            "operationName": operation_name,
            "variables": json.dumps(variables, separators=(",", ":")),
            "extensions": json.dumps(
                {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": sha256_hash,
                    }
                },
                separators=(",", ":"),
            ),
        },
        headers={
            "Accept": "application/json",
            "Accept-Language": "en",
            "Authorization": f"Bearer {access_token}",
            "app-platform": "WebPlayer",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ValueError(f"Spotify web-player query failed: {payload['errors']}")
    return payload


def search_artist_candidates(
    band_name: str,
    *,
    access_token: str,
    request_get: Callable = requests.get,
    timeout: float = 30,
    limit: int = 10,
) -> tuple[list[dict], dict]:
    """Search Spotify's web-player index and return compact artist candidates."""
    payload = _pathfinder_query(
        operation_name="searchDesktop",
        variables={
            "searchTerm": band_name,
            "offset": 0,
            "limit": limit,
            "numberOfTopResults": limit,
        },
        sha256_hash=ARTIST_SEARCH_HASH,
        access_token=access_token,
        request_get=request_get,
        timeout=timeout,
    )
    items = (
        payload.get("data", {})
        .get("searchV2", {})
        .get("artists", {})
        .get("items", [])
    )
    candidates = []
    for item in items:
        data = item.get("data") or {}
        uri = data.get("uri") or ""
        candidates.append(
            {
                "spotify_id": uri.rsplit(":", 1)[-1] if uri else "",
                "spotify_name": (data.get("profile") or {}).get("name"),
                "spotify_uri": uri,
            }
        )
    return candidates, payload


def fetch_artist_overview(
    spotify_id: str,
    *,
    access_token: str,
    request_get: Callable = requests.get,
    timeout: float = 30,
) -> tuple[dict, dict]:
    """Fetch and compact one current Spotify web-player artist overview."""
    payload = _pathfinder_query(
        operation_name="queryArtistOverview",
        variables={"uri": f"spotify:artist:{spotify_id}"},
        sha256_hash=ARTIST_OVERVIEW_HASH,
        access_token=access_token,
        request_get=request_get,
        timeout=timeout,
    )
    artist = payload.get("data", {}).get("artist")
    if not artist:
        raise ValueError("Spotify web-player response has no artist")
    stats = artist.get("stats") or {}
    monthly_listeners = stats.get("monthlyListeners")
    if monthly_listeners is None:
        raise ValueError("Spotify web-player response has no monthly listeners")
    compact = {
        "spotify_id": artist.get("id") or spotify_id,
        "spotify_name": (artist.get("profile") or {}).get("name"),
        "monthly_listeners": int(monthly_listeners),
        "followers": (
            int(stats["followers"]) if stats.get("followers") is not None else None
        ),
        "world_rank": (
            int(stats["worldRank"]) if stats.get("worldRank") is not None else None
        ),
    }
    return compact, payload
