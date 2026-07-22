#!/usr/bin/env python3
"""Resolve identifiers and origin evidence for top-20 city candidates.

The input catalogue remains unchanged. Every run writes timestamped raw
MusicBrainz responses, a reviewable interim CSV and a validation report.
Wikidata candidates are read from an already frozen raw snapshot.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (
    DEFAULT_MUSICBRAINZ_USER_AGENT,
    INTERIM_DATA_DIR,
    MUSICBRAINZ_ARTIST_ENDPOINT,
    MUSICBRAINZ_RAW_DIR,
    REFERENCE_DIR,
)
from python_uk_bands.io import write_csv, write_json
from python_uk_bands.matching import normalize_name
from python_uk_bands.spotify_public import spotify_artist_id_from_url


DEFAULT_ADDITIONS = REFERENCE_DIR / "top20_city_band_additions.csv"
DEFAULT_WIKIDATA = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "wikidata"
    / "uk_group_candidates_with_spotify_20260718T201100Z.json"
)


def _entity_id(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1]


def _wikidata_index(path: Path) -> dict[str, list[dict]]:
    payload = json.loads(path.read_text())
    index: dict[str, list[dict]] = {}
    for binding in payload["results"]["bindings"]:
        name = binding["itemLabel"]["value"]
        index.setdefault(normalize_name(name), []).append(binding)
    return index


def _collapse_wikidata_matches(matches: list[dict]) -> dict | None:
    identities: dict[tuple[str, str], dict] = {}
    for match in matches:
        key = (_entity_id(match["item"]["value"]), match["spotifyId"]["value"])
        row = identities.setdefault(
            key,
            {
                "wikidata_id": key[0],
                "wikidata_name": match["itemLabel"]["value"],
                "wikidata_spotify_id": key[1],
                "wikidata_formation_places": set(),
            },
        )
        formation = match.get("formationLabel", {}).get("value")
        if formation:
            row["wikidata_formation_places"].add(formation)
    if len(identities) != 1:
        return None
    result = next(iter(identities.values()))
    result["wikidata_formation_places"] = " | ".join(
        sorted(result["wikidata_formation_places"])
    )
    return result


def _musicbrainz_search(
    band_name: str,
    *,
    session: requests.Session,
    timeout: float,
) -> dict:
    response = session.get(
        MUSICBRAINZ_ARTIST_ENDPOINT,
        params={
            "query": f'artist:"{band_name}" AND type:group AND country:GB',
            "fmt": "json",
            "limit": 25,
        },
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_MUSICBRAINZ_USER_AGENT,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _pick_musicbrainz_artist(payload: dict, band_name: str) -> tuple[dict | None, str]:
    exact = [
        artist
        for artist in payload.get("artists", [])
        if normalize_name(artist.get("name")) == normalize_name(band_name)
    ]
    if not exact:
        return None, "no_exact_name"
    exact.sort(key=lambda artist: int(artist.get("score", 0)), reverse=True)
    top_score = int(exact[0].get("score", 0))
    top = [artist for artist in exact if int(artist.get("score", 0)) == top_score]
    if len(top) != 1:
        return None, f"ambiguous_exact_name_{len(top)}"
    return top[0], "exact_name"


def _musicbrainz_artist_details(
    musicbrainz_id: str,
    *,
    session: requests.Session,
    timeout: float,
) -> dict:
    response = session.get(
        f"{MUSICBRAINZ_ARTIST_ENDPOINT}/{musicbrainz_id}",
        params={"inc": "url-rels", "fmt": "json"},
        headers={
            "Accept": "application/json",
            "User-Agent": DEFAULT_MUSICBRAINZ_USER_AGENT,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _spotify_id_from_musicbrainz(details: dict) -> str | None:
    for relation in details.get("relations", []):
        url = (relation.get("url") or {}).get("resource")
        spotify_id = spotify_artist_id_from_url(url)
        if spotify_id:
            return spotify_id
    return None


def _area_name(artist: dict, key: str) -> str:
    return (artist.get(key) or {}).get("name") or ""


def _origin_alignment(claimed_place: str, *evidence_places: str) -> str:
    claimed = normalize_name(claimed_place)
    evidence = {
        normalize_name(place)
        for value in evidence_places
        for place in str(value).split(" | ")
        if place
    }
    if claimed and claimed in evidence:
        return "exact"
    return "review_required"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--additions", type=Path, default=DEFAULT_ADDITIONS)
    parser.add_argument("--wikidata-snapshot", type=Path, default=DEFAULT_WIKIDATA)
    parser.add_argument(
        "--throttle",
        type=float,
        default=1.05,
        help="Seconds between MusicBrainz requests",
    )
    parser.add_argument("--timeout", type=float, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    additions = pd.read_csv(args.additions, keep_default_na=False)
    wikidata = _wikidata_index(args.wikidata_snapshot)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = MUSICBRAINZ_RAW_DIR / f"top20_band_resolution_{timestamp}.json"
    review_path = INTERIM_DATA_DIR / f"top20_city_band_review_{timestamp}.csv"
    report_path = INTERIM_DATA_DIR / f"top20_city_band_review_{timestamp}_report.json"

    raw_payload: dict = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(args.additions.relative_to(PROJECT_ROOT)),
        "wikidata_snapshot": str(args.wikidata_snapshot.relative_to(PROJECT_ROOT)),
        "musicbrainz": {},
    }
    rows: list[dict] = []
    session = requests.Session()

    for position, candidate in enumerate(additions.to_dict("records"), start=1):
        band_name = candidate["band_name"]
        wd = _collapse_wikidata_matches(
            wikidata.get(normalize_name(band_name), [])
        )
        resolution = {
            **candidate,
            "wikidata_id": wd["wikidata_id"] if wd else "",
            "wikidata_name": wd["wikidata_name"] if wd else "",
            "wikidata_formation_places": (
                wd["wikidata_formation_places"] if wd else ""
            ),
            "musicbrainz_id": "",
            "musicbrainz_name": "",
            "musicbrainz_begin_area": "",
            "musicbrainz_area": "",
            "musicbrainz_disambiguation": "",
            "spotify_id": wd["wikidata_spotify_id"] if wd else "",
            "identity_resolution": "wikidata_exact_name" if wd else "unresolved",
            "origin_alignment": "review_required",
            "evidence_url": (
                f"https://www.wikidata.org/wiki/{wd['wikidata_id']}" if wd else ""
            ),
        }

        if not wd:
            search_payload = _musicbrainz_search(
                band_name,
                session=session,
                timeout=args.timeout,
            )
            raw_payload["musicbrainz"][band_name] = {"search": search_payload}
            artist, match_status = _pick_musicbrainz_artist(
                search_payload,
                band_name,
            )
            resolution["identity_resolution"] = f"musicbrainz_{match_status}"
            time.sleep(max(args.throttle, 0))

            if artist:
                details = _musicbrainz_artist_details(
                    artist["id"],
                    session=session,
                    timeout=args.timeout,
                )
                raw_payload["musicbrainz"][band_name]["details"] = details
                spotify_id = _spotify_id_from_musicbrainz(details)
                resolution.update(
                    {
                        "musicbrainz_id": artist["id"],
                        "musicbrainz_name": artist.get("name", ""),
                        "musicbrainz_begin_area": _area_name(
                            artist,
                            "begin-area",
                        ),
                        "musicbrainz_area": _area_name(artist, "area"),
                        "musicbrainz_disambiguation": artist.get(
                            "disambiguation",
                            "",
                        ),
                        "spotify_id": spotify_id or "",
                        "identity_resolution": (
                            "musicbrainz_exact_name_with_spotify"
                            if spotify_id
                            else "musicbrainz_exact_name_missing_spotify"
                        ),
                        "evidence_url": (
                            f"https://musicbrainz.org/artist/{artist['id']}"
                        ),
                    }
                )
                time.sleep(max(args.throttle, 0))

        resolution["origin_alignment"] = _origin_alignment(
            candidate["claimed_formation_place"],
            resolution["wikidata_formation_places"],
            resolution["musicbrainz_begin_area"],
        )
        resolution["review_ready"] = (
            bool(resolution["spotify_id"])
            and resolution["identity_resolution"]
            in {
                "wikidata_exact_name",
                "musicbrainz_exact_name_with_spotify",
            }
            and resolution["origin_alignment"] == "exact"
        )
        rows.append(resolution)

        if position % 10 == 0 or position == len(additions):
            write_json(raw_payload, raw_path)
            print(
                f"Resolved {position}/{len(additions)} candidates",
                flush=True,
            )

    review = pd.DataFrame(rows)
    write_csv(review, review_path)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_rows": len(review),
        "cities": review["study_city_label"].nunique(),
        "spotify_ids_resolved": int(review["spotify_id"].ne("").sum()),
        "origin_exact": int(review["origin_alignment"].eq("exact").sum()),
        "review_ready": int(review["review_ready"].sum()),
        "needs_identity_review": review.loc[
            ~review["review_ready"],
            "band_name",
        ].tolist(),
        "raw_path": str(raw_path.relative_to(PROJECT_ROOT)),
        "review_path": str(review_path.relative_to(PROJECT_ROOT)),
        "canonical_inputs_modified": False,
    }
    write_json(report, report_path)

    print(f"Raw responses: {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Review table: {review_path.relative_to(PROJECT_ROOT)}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
