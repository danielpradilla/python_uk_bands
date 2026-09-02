#!/usr/bin/env python3
"""Freeze public data used by review follow-up experiments 19–23."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import quote
import sys

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (  # noqa: E402
    FUA_POPULATION_PATH,
    FUA_POPULATION_YEAR,
)
from python_uk_bands.io import write_json  # noqa: E402


CAPTURE_DATE = "20260725"
PAGEVIEW_START = "2025070100"
PAGEVIEW_END = "2026063000"
USER_AGENT = (
    "uk-music-cities/1.0 (research project; info@danielpradilla.info)"
)

TOP1000_PATH = (
    PROJECT_ROOT
    / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv"
)
TOP1000_MAPPING_PATH = (
    PROJECT_ROOT
    / "data/interim/popularity_first_top1000_20260718T204522Z_fua_mapping_audit.csv"
)
BALANCED_PATH = (
    PROJECT_ROOT / "data/processed/fua_top20_band_metrics_20260718T204000Z.csv"
)
LEGACY_SPOTIFY_PATH = (
    PROJECT_ROOT
    / "data/snapshots/20260711T205005Z_pre-refresh-2026-07-11/files/data/raw/legacy/spotify_artists_f5c3e7b7ff.json"
)
COORDINATES_PATH = (
    PROJECT_ROOT / "reference/top1000_fua_map_coordinates_20260723.csv"
)

WIKIDATA_OUTPUT = (
    PROJECT_ROOT
    / f"data/raw/wikidata/review_extension_entities_{CAPTURE_DATE}.json"
)
MUSICBRAINZ_OUTPUT = (
    PROJECT_ROOT
    / f"data/raw/musicbrainz/review_extension_artists_{CAPTURE_DATE}.json"
)
OSM_OUTPUT = (
    PROJECT_ROOT
    / f"data/raw/openstreetmap/music_infrastructure_{CAPTURE_DATE}.json"
)
PAGEVIEWS_OUTPUT = (
    PROJECT_ROOT
    / (
        "data/raw/wikimedia/top1000_enwiki_pageviews_"
        f"{PAGEVIEW_START[:8]}_{PAGEVIEW_END[:8]}_{CAPTURE_DATE}.json"
    )
)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MUSICBRAINZ_API = "https://musicbrainz.org/ws/2/artist"
OVERPASS_API = "https://overpass-api.de/api/interpreter"
NOMINATIM_API = "https://nominatim.openstreetmap.org/search"
PAGEVIEWS_API = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Reuse completed records and retry only failed or missing requests.",
    )
    parser.add_argument(
        "--only",
        choices=("wikidata", "musicbrainz", "osm", "pageviews"),
        action="append",
        help="Capture only the named source; may be repeated.",
    )
    return parser


def _session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def _get_json(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    timeout: int = 90,
    attempts: int = 5,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to retrieve {url}: {last_error}") from last_error


def _post_json(
    session: requests.Session,
    url: str,
    *,
    data: dict,
    timeout: int = 180,
    attempts: int = 5,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.post(url, data=data, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Unable to retrieve {url}") from last_error


def _qid_values(entity: dict, property_id: str) -> list[str]:
    values: list[str] = []
    for claim in entity.get("claims", {}).get(property_id, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("entity-type") == "item":
            qid = value.get("id")
            if qid:
                values.append(str(qid))
    return sorted(set(values))


def _string_values(entity: dict, property_id: str) -> list[str]:
    values: list[str] = []
    for claim in entity.get("claims", {}).get(property_id, []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str) and value:
            values.append(value)
    return sorted(set(values))


def _trim_wikidata_entity(entity: dict) -> dict:
    """Keep only fields required by experiments 19, 21 and 23."""

    properties = ("P136", "P264", "P434", "P527", "P571")
    trimmed = {
        "id": entity.get("id", ""),
        "type": entity.get("type", "item"),
        "labels": {},
        "claims": {
            property_id: entity.get("claims", {}).get(property_id, [])
            for property_id in properties
            if entity.get("claims", {}).get(property_id)
        },
        "sitelinks": {},
    }
    english_label = entity.get("labels", {}).get("en")
    if english_label:
        trimmed["labels"]["en"] = english_label
    english_wikipedia = entity.get("sitelinks", {}).get("enwiki")
    if english_wikipedia:
        trimmed["sitelinks"]["enwiki"] = english_wikipedia
    return trimmed


def capture_wikidata(*, force: bool) -> Path:
    if WIKIDATA_OUTPUT.exists() and not force:
        print(f"reuse {WIKIDATA_OUTPUT.relative_to(PROJECT_ROOT)}", flush=True)
        return WIKIDATA_OUTPUT

    top1000 = pd.read_csv(TOP1000_PATH, keep_default_na=False)
    balanced = pd.read_csv(BALANCED_PATH, keep_default_na=False)
    candidates = pd.read_csv(
        PROJECT_ROOT / "data/interim/uk_group_spotify_candidates_20260718T201100Z.csv",
        keep_default_na=False,
    )
    balanced_qids = balanced[["spotify_id"]].merge(
        candidates[["spotify_id", "wikidata_qid"]],
        on="spotify_id",
        how="left",
        validate="one_to_one",
    )["wikidata_qid"]
    qids = sorted(
        set(top1000["wikidata_qid"]).union(
            value
            for value in balanced_qids
            if isinstance(value, str) and value.startswith("Q")
        )
    )
    session = _session()
    entities: dict[str, dict] = {}
    for start in range(0, len(qids), 50):
        batch = qids[start : start + 50]
        response = _get_json(
            session,
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "format": "json",
                "props": "claims|labels|sitelinks",
                "languages": "en",
                "sitefilter": "enwiki",
                "ids": "|".join(batch),
            },
        )
        entities.update(response["entities"])
        print(f"wikidata seed {min(start + 50, len(qids))}/{len(qids)}", flush=True)

    referenced_qids = sorted(
        {
            qid
            for entity in entities.values()
            for property_id in ("P136", "P264", "P527")
            for qid in _qid_values(entity, property_id)
        }.difference(entities)
    )
    labels: dict[str, str] = {}
    for start in range(0, len(referenced_qids), 50):
        batch = referenced_qids[start : start + 50]
        response = _get_json(
            session,
            WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "format": "json",
                "props": "labels",
                "languages": "en",
                "ids": "|".join(batch),
            },
        )
        for qid, entity in response["entities"].items():
            labels[qid] = entity.get("labels", {}).get("en", {}).get("value", "")

    entities = {
        qid: _trim_wikidata_entity(entity) for qid, entity in entities.items()
    }

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": WIKIDATA_API,
        "license": "CC0",
        "input_path": str(TOP1000_PATH.relative_to(PROJECT_ROOT)),
        "balanced_input_path": str(BALANCED_PATH.relative_to(PROJECT_ROOT)),
        "seed_counts": {
            "top1000_qids": int(top1000["wikidata_qid"].nunique()),
            "balanced_qids": int(
                balanced_qids[
                    balanced_qids.map(
                        lambda value: isinstance(value, str) and value.startswith("Q")
                    )
                ].nunique()
            ),
            "union_qids": len(qids),
        },
        "properties": {
            "P136": "genre",
            "P264": "record label",
            "P434": "MusicBrainz artist ID",
            "P527": "has part or member",
            "P571": "inception",
        },
        "entities": entities,
        "referenced_labels": labels,
    }
    write_json(payload, WIKIDATA_OUTPUT)
    print(
        f"wrote {WIKIDATA_OUTPUT.relative_to(PROJECT_ROOT)} "
        f"entities={len(entities)} labels={len(labels)}",
        flush=True,
    )
    return WIKIDATA_OUTPUT


def _musicbrainz_catalogue() -> pd.DataFrame:
    top1000 = pd.read_csv(TOP1000_PATH, keep_default_na=False)
    mapping = pd.read_csv(TOP1000_MAPPING_PATH, keep_default_na=False)
    wikidata = json.loads(WIKIDATA_OUTPUT.read_text())
    wikidata_musicbrainz = pd.DataFrame(
        [
            {
                "wikidata_qid": qid,
                "wikidata_musicbrainz_ids": "|".join(_string_values(entity, "P434")),
            }
            for qid, entity in wikidata.get("entities", {}).items()
        ]
    )
    legacy = pd.DataFrame(json.loads(LEGACY_SPOTIFY_PATH.read_text()))
    legacy = legacy[["spotify_id", "musicbrainz_id"]].drop_duplicates("spotify_id")
    catalogue = top1000[
        ["spotify_name", "returned_spotify_id", "wikidata_qid"]
    ].rename(
        columns={"spotify_name": "band_name", "returned_spotify_id": "spotify_id"}
    ).merge(
        mapping[["returned_spotify_id", "mapping_tier", "study_city_label"]].rename(
            columns={"returned_spotify_id": "spotify_id"}
        ),
        on="spotify_id",
        how="left",
        validate="one_to_one",
    )
    catalogue = catalogue.loc[
        catalogue["mapping_tier"].isin({"strict", "reviewed_extended"})
    ].copy()
    catalogue = catalogue.merge(
        wikidata_musicbrainz,
        on="wikidata_qid",
        how="left",
        validate="one_to_one",
    ).merge(
        legacy.rename(columns={"musicbrainz_id": "legacy_musicbrainz_id"}),
        on="spotify_id",
        how="left",
    )
    catalogue[["wikidata_musicbrainz_ids", "legacy_musicbrainz_id"]] = catalogue[
        ["wikidata_musicbrainz_ids", "legacy_musicbrainz_id"]
    ].fillna("")
    catalogue["resolved_musicbrainz_ids"] = catalogue[
        "wikidata_musicbrainz_ids"
    ].mask(
        catalogue["wikidata_musicbrainz_ids"].eq(""),
        catalogue["legacy_musicbrainz_id"],
    )
    catalogue["resolved_musicbrainz_id"] = catalogue[
        "resolved_musicbrainz_ids"
    ].str.split("|")
    catalogue = catalogue.explode("resolved_musicbrainz_id")
    return (
        catalogue.loc[catalogue["resolved_musicbrainz_id"].ne("")]
        .drop_duplicates(["spotify_id", "resolved_musicbrainz_id"])
        .reset_index(drop=True)
    )


def capture_musicbrainz(*, force: bool) -> Path:
    if MUSICBRAINZ_OUTPUT.exists() and not force:
        print(f"reuse {MUSICBRAINZ_OUTPUT.relative_to(PROJECT_ROOT)}", flush=True)
        return MUSICBRAINZ_OUTPUT

    if not WIKIDATA_OUTPUT.exists():
        capture_wikidata(force=force)
    catalogue = _musicbrainz_catalogue()
    def capture_record(row: object) -> dict:
        session = _session()
        mbid = row.resolved_musicbrainz_id
        source_url = f"https://musicbrainz.org/artist/{mbid}"
        try:
            response = _get_json(
                session,
                f"{MUSICBRAINZ_API}/{mbid}",
                params={"inc": "genres+tags+artist-rels", "fmt": "json"},
                timeout=90,
            )
        except RuntimeError as error:
            return {
                "band_name": row.band_name,
                "study_city_label": row.study_city_label,
                "spotify_id": row.spotify_id,
                "wikidata_qid": row.wikidata_qid,
                "musicbrainz_id": mbid,
                "status": "request_failed",
                "error": str(error),
                "musicbrainz_name": "",
                "genres": [],
                "tags": [],
                "member_relations": [],
                "source_url": source_url,
            }
        relations = []
        for relation in response.get("relations", []):
            if relation.get("type") != "member of band" or "artist" not in relation:
                continue
            target = relation["artist"]
            relations.append(
                {
                    "artist_id": target.get("id", ""),
                    "artist_name": target.get("name", ""),
                    "artist_type": target.get("type", ""),
                    "direction": relation.get("direction", ""),
                    "begin": relation.get("begin"),
                    "end": relation.get("end"),
                    "ended": relation.get("ended"),
                }
            )
        return {
            "band_name": row.band_name,
            "study_city_label": row.study_city_label,
            "spotify_id": row.spotify_id,
            "wikidata_qid": row.wikidata_qid,
            "musicbrainz_id": mbid,
            "status": "ok",
            "musicbrainz_name": response.get("name", ""),
            "genres": response.get("genres", []),
            "tags": response.get("tags", []),
            "member_relations": relations,
            "source_url": source_url,
        }

    records: list[dict] = []
    last_request = 0.0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for submitted, row in enumerate(catalogue.itertuples(), start=1):
            wait = 1.05 - (time.monotonic() - last_request)
            if wait > 0:
                time.sleep(wait)
            futures.append(executor.submit(capture_record, row))
            last_request = time.monotonic()
            if submitted % 25 == 0 or submitted == len(catalogue):
                print(
                    f"musicbrainz scheduled {submitted}/{len(catalogue)}",
                    flush=True,
                )
        for index, future in enumerate(as_completed(futures), start=1):
            records.append(future.result())
            if index % 25 == 0 or index == len(futures):
                print(f"musicbrainz {index}/{len(futures)}", flush=True)
    records.sort(key=lambda row: (row["band_name"], row["musicbrainz_id"]))

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": MUSICBRAINZ_API,
        "license_note": (
            "Core MusicBrainz data are CC0; tags/genres are supplementary data "
            "under CC BY-NC-SA 3.0."
        ),
        "input_path": str(TOP1000_PATH.relative_to(PROJECT_ROOT)),
        "mapping_path": str(TOP1000_MAPPING_PATH.relative_to(PROJECT_ROOT)),
        "wikidata_input_path": str(WIKIDATA_OUTPUT.relative_to(PROJECT_ROOT)),
        "legacy_identifier_path": str(LEGACY_SPOTIFY_PATH.relative_to(PROJECT_ROOT)),
        "successful_records": sum(record["status"] == "ok" for record in records),
        "failed_records": sum(record["status"] != "ok" for record in records),
        "records": records,
    }
    write_json(payload, MUSICBRAINZ_OUTPUT)
    print(
        f"wrote {MUSICBRAINZ_OUTPUT.relative_to(PROJECT_ROOT)} records={len(records)}",
        flush=True,
    )
    return MUSICBRAINZ_OUTPUT


def _overpass_query(latitude: float, longitude: float, radius: int) -> str:
    selectors = (
        '["amenity"="music_venue"]',
        '["amenity"="nightclub"]',
        '["amenity"="arts_centre"]',
        '["shop"="music"]',
        '["studio"="audio"]',
        '["amenity"="university"]',
    )
    clauses = "\n".join(
        f"nw(around:{radius},{latitude},{longitude}){selector};"
        for selector in selectors
    )
    return f"[out:json][timeout:180];\n(\n{clauses}\n);\nout center tags;"


def capture_osm(*, force: bool) -> Path:
    cities = pd.read_csv(BALANCED_PATH)[
        ["fua_code", "official_fua_name", "study_city_label"]
    ].drop_duplicates()
    current_population = pd.read_csv(FUA_POPULATION_PATH)[
        ["fua_code", "population_year", "population", "captured_at_utc"]
    ]
    cities = cities.merge(
        current_population,
        on="fua_code",
        how="left",
        validate="one_to_one",
    )
    if cities["population"].isna().any():
        missing = cities.loc[cities["population"].isna(), "fua_code"].tolist()
        raise ValueError(f"Missing current FUA population for: {missing}")
    if set(cities["population_year"]) != {FUA_POPULATION_YEAR}:
        raise ValueError(
            "OpenStreetMap capture context must use the configured FUA "
            f"population year {FUA_POPULATION_YEAR}"
        )
    population_captured_at = current_population[
        "captured_at_utc"
    ].unique().item()
    population_by_code = (
        cities.set_index("fua_code")[["population_year", "population"]]
        .to_dict("index")
    )

    existing_records: list[dict] = []
    if OSM_OUTPUT.exists() and not force:
        existing = json.loads(OSM_OUTPUT.read_text())
        for record in existing.get("records", []):
            population = population_by_code.get(record.get("fua_code"))
            if population is None:
                raise ValueError(
                    "OpenStreetMap record has no current FUA population: "
                    f"{record.get('fua_code')}"
                )
            record["population_year"] = int(population["population_year"])
            record["population"] = int(population["population"])
        existing["population_path"] = str(
            FUA_POPULATION_PATH.relative_to(PROJECT_ROOT)
        )
        existing["population_year"] = FUA_POPULATION_YEAR
        existing["population_captured_at_utc"] = population_captured_at
        if existing.get("complete"):
            write_json(existing, OSM_OUTPUT)
            print(f"reuse {OSM_OUTPUT.relative_to(PROJECT_ROOT)}", flush=True)
            return OSM_OUTPUT
        existing_records = existing.get("records", [])

    coordinates = pd.read_csv(COORDINATES_PATH)
    cities = cities.merge(
        coordinates[["fua_code", "latitude", "longitude", "coordinate_source_url"]],
        on="fua_code",
        how="left",
        validate="one_to_one",
    ).sort_values("study_city_label")
    session = _session()
    missing_coordinates = cities["latitude"].isna() | cities["longitude"].isna()
    for index in cities.index[missing_coordinates]:
        query_label = cities.at[index, "official_fua_name"]
        matches = _get_json(
            session,
            NOMINATIM_API,
            params={
                "q": f"{query_label}, United Kingdom",
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "gb",
            },
        )
        if not matches:
            raise ValueError(f"No coordinate match for {query_label}")
        match = matches[0]
        cities.at[index, "latitude"] = float(match["lat"])
        cities.at[index, "longitude"] = float(match["lon"])
        cities.at[index, "coordinate_source_url"] = (
            f"https://www.openstreetmap.org/{match['osm_type']}/{match['osm_id']}"
        )
        print(f"nominatim {query_label}: {match['display_name']}", flush=True)
        time.sleep(1.05)

    radius = 15_000
    records_by_city = {
        record["study_city_label"]: record for record in existing_records
    }
    checkpoint = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": OVERPASS_API,
        "data_copyright": "OpenStreetMap contributors",
        "license": "ODbL",
        "input_path": str(BALANCED_PATH.relative_to(PROJECT_ROOT)),
        "population_path": str(FUA_POPULATION_PATH.relative_to(PROJECT_ROOT)),
        "population_year": FUA_POPULATION_YEAR,
        "population_captured_at_utc": population_captured_at,
        "coordinate_path": str(COORDINATES_PATH.relative_to(PROJECT_ROOT)),
        "definition": (
            "OpenStreetMap nodes and ways within 15 km of the study-city "
            "centre; these are not OECD FUA boundaries."
        ),
        "complete": False,
        "records": sorted(
            records_by_city.values(), key=lambda item: item["study_city_label"]
        ),
    }
    for index, row in enumerate(cities.itertuples(), start=1):
        if row.study_city_label in records_by_city:
            print(
                f"openstreetmap {index}/{len(cities)} {row.study_city_label} reused",
                flush=True,
            )
            continue
        query = _overpass_query(row.latitude, row.longitude, radius)
        response = _post_json(
            session,
            OVERPASS_API,
            data={"data": query},
            timeout=240,
            attempts=8,
        )
        records_by_city[row.study_city_label] = {
            "fua_code": row.fua_code,
            "study_city_label": row.study_city_label,
            "population_year": int(row.population_year),
            "population": int(row.population),
            "latitude": row.latitude,
            "longitude": row.longitude,
            "radius_metres": radius,
            "coordinate_source_url": row.coordinate_source_url,
            "elements": response.get("elements", []),
        }
        print(
            f"openstreetmap {index}/{len(cities)} {row.study_city_label} "
            f"elements={len(response.get('elements', []))}",
            flush=True,
        )
        checkpoint["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
        checkpoint["records"] = sorted(
            records_by_city.values(), key=lambda item: item["study_city_label"]
        )
        write_json(checkpoint, OSM_OUTPUT)
        time.sleep(2.0)

    payload = checkpoint | {"complete": True}
    write_json(payload, OSM_OUTPUT)
    print(f"wrote {OSM_OUTPUT.relative_to(PROJECT_ROOT)}", flush=True)
    return OSM_OUTPUT


def _pageview_record(qid: str, entity: dict) -> dict:
    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title", "")
    base = {
        "wikidata_qid": qid,
        "article_title": title,
        "status": "no_enwiki_article" if not title else "pending",
        "items": [],
    }
    if not title:
        return base
    encoded_title = quote(title.replace(" ", "_"), safe="")
    url = f"{PAGEVIEWS_API}/{encoded_title}/monthly/{PAGEVIEW_START}/{PAGEVIEW_END}"
    try:
        payload = _get_json(_session(), url, timeout=90)
    except RuntimeError as error:
        if "404 Client Error" in str(error):
            base["status"] = "no_pageview_data"
            base["source_url"] = url
            return base
        base["status"] = "request_failed"
        base["error"] = str(error)
        base["source_url"] = url
        return base
    base["status"] = "ok"
    base["source_url"] = url
    base["items"] = payload.get("items", [])
    return base


def capture_pageviews(*, force: bool, retry_failed: bool = False) -> Path:
    if PAGEVIEWS_OUTPUT.exists() and not force and not retry_failed:
        print(f"reuse {PAGEVIEWS_OUTPUT.relative_to(PROJECT_ROOT)}", flush=True)
        return PAGEVIEWS_OUTPUT
    if not WIKIDATA_OUTPUT.exists():
        capture_wikidata(force=force)

    wikidata = json.loads(WIKIDATA_OUTPUT.read_text())
    entities = wikidata["entities"]
    records: list[dict] = []
    target_entities = entities
    if retry_failed and PAGEVIEWS_OUTPUT.exists():
        previous = json.loads(PAGEVIEWS_OUTPUT.read_text())
        records = [
            record
            for record in previous.get("records", [])
            if record.get("status") != "request_failed"
        ]
        completed_qids = {record["wikidata_qid"] for record in records}
        target_entities = {
            qid: entity for qid, entity in entities.items() if qid not in completed_qids
        }
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_pageview_record, qid, entity): qid
            for qid, entity in target_entities.items()
        }
        for index, future in enumerate(as_completed(futures), start=1):
            records.append(future.result())
            if index % 20 == 0 or index == len(futures):
                print(f"wikimedia pageviews {index}/{len(futures)}", flush=True)
    records.sort(key=lambda row: row["wikidata_qid"])

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": PAGEVIEWS_API,
        "license_note": (
            "Wikimedia pageview aggregates are provided under Wikimedia API "
            "terms; article content is not reproduced."
        ),
        "wikidata_input": str(WIKIDATA_OUTPUT.relative_to(PROJECT_ROOT)),
        "project": "en.wikipedia",
        "access": "all-access",
        "agent": "user",
        "granularity": "monthly",
        "start": PAGEVIEW_START,
        "end": PAGEVIEW_END,
        "records": records,
    }
    write_json(payload, PAGEVIEWS_OUTPUT)
    print(
        f"wrote {PAGEVIEWS_OUTPUT.relative_to(PROJECT_ROOT)} records={len(records)}",
        flush=True,
    )
    return PAGEVIEWS_OUTPUT


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = set(args.only or ("wikidata", "musicbrainz", "osm", "pageviews"))
    if "wikidata" in selected:
        capture_wikidata(force=args.force)
    if "musicbrainz" in selected:
        capture_musicbrainz(force=args.force)
    if "osm" in selected:
        capture_osm(force=args.force)
    if "pageviews" in selected:
        capture_pageviews(force=args.force, retry_failed=args.retry_failed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
