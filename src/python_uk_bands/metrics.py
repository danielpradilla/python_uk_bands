"""Fetch and validate dated Spotify artist metrics from SpotScraper."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import time
from typing import Callable

import requests


SPOTSCRAPER_ARTIST_ENDPOINT = "https://api.spotscraper.com/v1/artists/{spotify_id}"


def _first_value(mapping: dict, *keys: str):
    """Return the first present, non-null value without treating zero as missing."""
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def extract_spotscraper_artist(payload: dict) -> dict:
    """Normalize the known SpotScraper artist response variants."""
    if not isinstance(payload, dict):
        raise ValueError("SpotScraper response must be a JSON object")
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ValueError("SpotScraper response has no artist object")
    stats = data.get("statistics") or data.get("stats") or {}
    if not isinstance(stats, dict):
        stats = {}

    monthly_listeners = _first_value(stats, "monthlyListeners", "monthly_listeners")
    if monthly_listeners is None:
        monthly_listeners = _first_value(data, "monthlyListeners", "monthly_listeners")
    followers = _first_value(stats, "followers")
    if followers is None:
        followers = _first_value(data, "followers", "followers_total", "followersTotal")
    world_rank = _first_value(stats, "worldRank", "world_rank")
    if world_rank is None:
        world_rank = _first_value(data, "worldRank", "world_rank")

    return {
        "spotify_name": _first_value(data, "name", "artistName", "artist_name"),
        "monthly_listeners": monthly_listeners,
        "followers": followers,
        "world_rank": world_rank,
    }


def _as_int(value, *, field: str) -> int:
    if isinstance(value, dict):
        value = _first_value(value, "total", "value")
    try:
        number = int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Missing or invalid {field}: {value!r}") from exc
    if number < 0:
        raise ValueError(f"{field} cannot be negative")
    return number


def fetch_spotscraper_metrics(
    records: list[dict],
    *,
    api_key: str,
    request_get: Callable = requests.get,
    timeout: float = 20,
    attempts: int = 3,
    backoff_seconds: float = 1,
) -> tuple[list[dict], list[dict]]:
    """Fetch every requested artist, returning successful rows and audit failures."""
    if not api_key:
        raise ValueError("SPOTSCRAPER_API_KEY is required")

    fetched_at = datetime.now(timezone.utc).date().isoformat()
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    rows: list[dict] = []
    failures: list[dict] = []

    for record in records:
        spotify_id = record.get("spotify_id")
        if not spotify_id:
            failures.append({"band": record.get("band"), "error": "missing_spotify_id"})
            continue

        response = None
        for attempt in range(1, attempts + 1):
            try:
                response = request_get(
                    SPOTSCRAPER_ARTIST_ENDPOINT.format(spotify_id=spotify_id),
                    headers=headers,
                    timeout=timeout,
                )
                response.raise_for_status()
                normalized = extract_spotscraper_artist(response.json())
                monthly_listeners = _as_int(
                    normalized["monthly_listeners"], field="monthly_listeners"
                )
                followers = _as_int(normalized["followers"], field="followers")
                rows.append(
                    {
                        "band": record["band"],
                        "city": record["city"],
                        "spotify_id": spotify_id,
                        "spotify_name": normalized["spotify_name"]
                        or record.get("spotify_name"),
                        "match_quality": record.get("match_quality"),
                        "monthly_listeners": monthly_listeners,
                        "monthly_listeners_m": round(monthly_listeners / 1_000_000, 2),
                        "followers": followers,
                        "world_rank": normalized["world_rank"],
                        "stats_extracted_at": fetched_at,
                    }
                )
                break
            except (requests.RequestException, ValueError) as exc:
                status = (
                    response.status_code
                    if response is not None and hasattr(response, "status_code")
                    else None
                )
                retryable = status is None or status == 429 or status >= 500
                if retryable and attempt < attempts:
                    retry_after = response.headers.get("Retry-After") if response is not None else None
                    try:
                        delay = min(float(retry_after), 30) if retry_after else backoff_seconds * attempt
                    except ValueError:
                        delay = backoff_seconds * attempt
                    time.sleep(delay)
                    continue
                failures.append(
                    {
                        "band": record.get("band"),
                        "spotify_id": spotify_id,
                        "status": status,
                        "error": str(exc),
                    }
                )
                break

        # Authentication and quota failures apply to the account, not one artist.
        if failures and failures[-1].get("status") in {401, 403, 429}:
            break

    rows.sort(key=lambda item: (item["city"], item["band"]))
    return rows, failures


def validate_metric_candidate(
    candidate: list[dict],
    identifiers: list[dict],
    previous: list[dict],
) -> dict:
    """Build a promotion report for a candidate metrics snapshot."""
    expected_by_band = {row["band"]: row for row in identifiers}
    candidate_by_band = {row.get("band"): row for row in candidate}
    previous_by_band = {row["band"]: row for row in previous}

    missing_bands = sorted(set(expected_by_band) - set(candidate_by_band))
    unexpected_bands = sorted(set(candidate_by_band) - set(expected_by_band))
    duplicate_bands = sorted(
        value for value, count in Counter(row.get("band") for row in candidate).items()
        if count > 1
    )
    duplicate_ids = sorted(
        value
        for value, count in Counter(row.get("spotify_id") for row in candidate).items()
        if count > 1
    )
    id_changes = sorted(
        band
        for band, row in candidate_by_band.items()
        if band in expected_by_band
        and row.get("spotify_id") != expected_by_band[band].get("spotify_id")
    )
    missing_metrics = sorted(
        row.get("band")
        for row in candidate
        if row.get("followers") is None or row.get("monthly_listeners") is None
    )
    dates = sorted({row.get("stats_extracted_at") for row in candidate})

    large_changes = []
    for band, row in candidate_by_band.items():
        old = previous_by_band.get(band)
        if not old:
            continue
        for metric in ("followers", "monthly_listeners"):
            before, after = old.get(metric), row.get(metric)
            if before and after is not None:
                change = (after - before) / before
                if abs(change) >= 0.75:
                    large_changes.append(
                        {
                            "band": band,
                            "metric": metric,
                            "before": before,
                            "after": after,
                            "change_pct": round(change * 100, 1),
                        }
                    )

    identity_warnings = sorted(
        row["band"]
        for row in candidate
        if row.get("match_quality") != "exact" or row.get("followers", 0) < 100
    )
    blocking_checks = {
        "row_count_matches": len(candidate) == len(identifiers),
        "all_expected_bands_present": not missing_bands,
        "no_unexpected_bands": not unexpected_bands,
        "band_names_are_unique": not duplicate_bands,
        "spotify_ids_are_unique": not duplicate_ids,
        "spotify_ids_are_unchanged": not id_changes,
        "all_metrics_present": not missing_metrics,
        "one_valid_snapshot_date": len(dates) == 1 and bool(dates[0]),
    }
    return {
        "promotion_ready": all(blocking_checks.values()),
        "blocking_checks": blocking_checks,
        "row_count": len(candidate),
        "expected_row_count": len(identifiers),
        "snapshot_dates": dates,
        "missing_bands": missing_bands,
        "unexpected_bands": unexpected_bands,
        "duplicate_bands": duplicate_bands,
        "duplicate_spotify_ids": duplicate_ids,
        "spotify_id_changes": id_changes,
        "missing_metrics": missing_metrics,
        "identity_warnings": identity_warnings,
        "large_changes": large_changes,
    }
