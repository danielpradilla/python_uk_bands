#!/usr/bin/env python3
"""Build the source-backed browser package for the band origins explorer."""

from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (  # noqa: E402
    FUA_POPULATION_PATH,
    FUA_POPULATION_YEAR,
    POPULARITY_FIRST_SNAPSHOT_ID,
    POPULARITY_FIRST_TOP1000_BANDS_PATH,
)


GENRE_AUDIT_PATH = (
    PROJECT_ROOT
    / "artifacts/experiments/genre_city_histories/20260725/band_genre_year_audit.csv"
)
GENRE_CAPTURE_PATH = (
    PROJECT_ROOT
    / "data/raw/wikidata/review_extension_entities_20260725.json"
)
ORIGIN_COORDINATES_PATH = (
    PROJECT_ROOT
    / "interactive/data/origin_coordinates_20260902.csv"
)
FUA_MAPPING_PATH = (
    PROJECT_ROOT
    / "reference/popularity_first_top1000_origin_fua_mapping_20260718.csv"
)
UK_OUTLINE_PATH = (
    PROJECT_ROOT
    / "data/raw/geography/natural_earth_50m_united_kingdom_20260723.geojson"
)

DASHBOARD_PATH = PROJECT_ROOT / "interactive/public/data/dashboard.json"
VALIDATION_PATH = (
    PROJECT_ROOT / "interactive/public/data/dashboard.validation.json"
)
OUTLINE_BROWSER_PATH = (
    PROJECT_ROOT / "interactive/public/data/uk-outline.geojson"
)

BASELINE_RESOLVED_BANDS = 748
BASELINE_GENRE_BANDS = 928
BASELINE_WIKIPEDIA_BANDS = 956
UK_BOUNDS = (-9.0, 49.0, 2.5, 61.5)

CATALOG_REQUIRED_COLUMNS = {
    "popularity_rank",
    "returned_spotify_id",
    "spotify_name",
    "band_name",
    "monthly_listeners",
    "followers",
    "stats_extracted_at_utc",
    "origin_cluster",
    "origin_resolution",
}
GENRE_REQUIRED_COLUMNS = {
    "returned_spotify_id",
    "genre_labels",
    "genre_families",
    "enwiki_title",
}
COORDINATE_REQUIRED_COLUMNS = {
    "origin_cluster",
    "place_type",
    "location_status",
    "wikidata_qid",
    "latitude",
    "longitude",
    "coordinate_source_url",
    "captured_at_utc",
    "review_notes",
}
FUA_MAPPING_REQUIRED_COLUMNS = {
    "origin_cluster",
    "fua_code",
    "mapping_tier",
    "mapping_method",
}
FUA_POPULATION_REQUIRED_COLUMNS = {
    "fua_code",
    "official_fua_name",
    "study_city_label",
    "population_year",
    "population",
    "source_dataset_url",
    "captured_at_utc",
}


def _read_csv(
    path: Path, required_columns: set[str]
) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = required_columns.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing required columns {sorted(missing)}")
        return list(reader)


def _integer(row: dict[str, str], field: str) -> int:
    try:
        return int(row[field])
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid {field} for {row.get('spotify_name', 'unknown band')}"
        ) from error


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid timestamp: {value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Timestamp is not timezone-aware: {value}")
    return parsed.astimezone(timezone.utc).isoformat()


def _capture_date_from_filename(path: Path) -> str:
    match = re.search(r"_(\d{8})(?:\D|$)", path.stem)
    if not match:
        raise ValueError(f"No capture date in filename: {path}")
    parsed = datetime.strptime(match.group(1), "%Y%m%d").replace(
        tzinfo=timezone.utc
    )
    return parsed.isoformat()


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _split_values(value: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in value.split("|") if item.strip()))


def _wikipedia_url(title: str) -> str | None:
    if not title:
        return None
    encoded = quote(title.replace(" ", "_"), safe="()_-'~")
    return f"https://en.wikipedia.org/wiki/{encoded}"


def _rank_bands(
    bands: list[dict[str, object]],
    metric: str,
    group_field: str,
    rank_field: str,
) -> None:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for band in bands:
        if band[group_field]:
            grouped[str(band[group_field])].append(band)
    for group_bands in grouped.values():
        ordered = sorted(
            group_bands,
            key=lambda band: (
                -int(band[metric]),
                int(band["catalogRank"]),
                str(band["name"]).casefold(),
            ),
        )
        for rank, band in enumerate(ordered, start=1):
            band[rank_field] = rank


def _validate_package(
    payload: dict[str, object],
    coordinate_rows: list[dict[str, str]],
) -> dict[str, object]:
    bands = payload["bands"]
    places = payload["places"]
    fuas = payload["fuas"]
    meta = payload["meta"]
    if len(bands) != 1000:
        raise ValueError(f"Expected 1,000 bands, found {len(bands)}")
    ids = [band["id"] for band in bands]
    if len(set(ids)) != 1000 or any(not band_id for band_id in ids):
        raise ValueError("Catalog must contain 1,000 unique Spotify IDs")
    ranks = [band["catalogRank"] for band in bands]
    if sorted(ranks) != list(range(1, 1001)):
        raise ValueError("Catalog popularity ranks must cover 1 through 1,000")

    location_records = [row["origin_cluster"] for row in coordinate_rows]
    if len(location_records) != len(set(location_records)):
        raise ValueError("Origin coordinate records must be unique")
    resolved_origins = {
        band["originCluster"] for band in bands if band["originCluster"]
    }
    if resolved_origins != set(location_records):
        missing = resolved_origins.difference(location_records)
        extra = set(location_records).difference(resolved_origins)
        raise ValueError(
            f"Origin location review mismatch; missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )

    for band in bands:
        if band["monthlyListeners"] < 0 or band["followers"] < 0:
            raise ValueError(f"Negative Spotify metric for {band['name']}")
        if not band["spotifyUrl"].endswith(f"/{band['id']}"):
            raise ValueError(f"Invalid Spotify URL for {band['name']}")
        expected_wikipedia_url = _wikipedia_url(band["wikipediaTitle"] or "")
        if band["wikipediaUrl"] != expected_wikipedia_url:
            raise ValueError(f"Invalid Wikipedia URL for {band['name']}")
        if len(band["genres"]) != len(set(band["genres"])):
            raise ValueError(f"Duplicate genres for {band['name']}")
        if len(band["genreFamilies"]) != len(set(band["genreFamilies"])):
            raise ValueError(f"Duplicate genre families for {band['name']}")
        if band["locationStatus"] == "uk":
            latitude = float(band["latitude"])
            longitude = float(band["longitude"])
            if not (isfinite(latitude) and isfinite(longitude)):
                raise ValueError(f"Non-finite coordinate for {band['name']}")
            west, south, east, north = UK_BOUNDS
            if not (west <= longitude <= east and south <= latitude <= north):
                raise ValueError(f"Coordinate outside UK bounds for {band['name']}")
        if band["locationStatus"] == "outside_uk" and (
            band["latitude"] is not None or band["longitude"] is not None
        ):
            raise ValueError(f"Outside-UK band has map coordinates: {band['name']}")

    fua_ids = [fua["id"] for fua in fuas]
    if len(fua_ids) != len(set(fua_ids)) or not fua_ids:
        raise ValueError("FUA records must have unique nonblank IDs")
    fua_by_id = {fua["id"]: fua for fua in fuas}
    for fua in fuas:
        if fua["population"] <= 0 or fua["populationYear"] != FUA_POPULATION_YEAR:
            raise ValueError(f"Invalid population denominator for {fua['label']}")
        if fua["bandCount"] <= 0:
            raise ValueError(f"FUA without mapped catalog bands: {fua['label']}")
        for field in ("monthlyListenersPerResident", "followersPerResident"):
            if not isfinite(float(fua[field])) or float(fua[field]) < 0:
                raise ValueError(f"Invalid {field} for {fua['label']}")
        expected_monthly = fua["monthlyListenersTotal"] / fua["population"]
        expected_followers = fua["followersTotal"] / fua["population"]
        if fua["monthlyListenersPerResident"] != expected_monthly:
            raise ValueError(f"Monthly-listener index mismatch for {fua['label']}")
        if fua["followersPerResident"] != expected_followers:
            raise ValueError(f"Follower index mismatch for {fua['label']}")
    for band in bands:
        if band["fuaCode"] is not None and band["fuaCode"] not in fua_by_id:
            raise ValueError(f"Unknown FUA code for {band['name']}")
        if band["fuaCode"] is not None and band["fuaMappingTier"] != "strict":
            raise ValueError(f"Non-strict FUA assignment for {band['name']}")
        if band["fuaCode"] is None and (
            band["fuaRankMonthlyListeners"] is not None
            or band["fuaRankFollowers"] is not None
        ):
            raise ValueError(f"Unmapped band has an FUA rank: {band['name']}")

    by_origin: dict[str, list[dict[str, object]]] = defaultdict(list)
    for band in bands:
        if band["originCluster"]:
            by_origin[band["originCluster"]].append(band)
    for origin, origin_bands in by_origin.items():
        for rank_field in (
            "placeRankMonthlyListeners",
            "placeRankFollowers",
        ):
            values = sorted(band[rank_field] for band in origin_bands)
            if values != list(range(1, len(origin_bands) + 1)):
                raise ValueError(f"Non-contiguous {rank_field} for {origin}")

    by_fua: dict[str, list[dict[str, object]]] = defaultdict(list)
    for band in bands:
        if band["fuaCode"]:
            by_fua[str(band["fuaCode"])].append(band)
    for fua_code, fua_bands in by_fua.items():
        for rank_field in ("fuaRankMonthlyListeners", "fuaRankFollowers"):
            values = sorted(band[rank_field] for band in fua_bands)
            if values != list(range(1, len(fua_bands) + 1)):
                raise ValueError(f"Non-contiguous {rank_field} for {fua_code}")
        if fua_by_id[fua_code]["bandCount"] != len(fua_bands):
            raise ValueError(f"FUA band-count mismatch for {fua_code}")

    for value in meta["freshness"].values():
        _utc(value)
    _utc(meta["builtAtUtc"])
    if meta["snapshotId"] != POPULARITY_FIRST_SNAPSHOT_ID:
        raise ValueError("Dashboard snapshot ID does not match project config")
    if meta["sourceFilename"] != POPULARITY_FIRST_TOP1000_BANDS_PATH.name:
        raise ValueError("Dashboard source filename does not match project config")

    counts = {
        "catalogBands": len(bands),
        "resolvedOriginBands": sum(
            band["originCluster"] is not None for band in bands
        ),
        "ukLocatedBands": sum(
            band["locationStatus"] == "uk" for band in bands
        ),
        "outsideUkBands": sum(
            band["locationStatus"] == "outside_uk" for band in bands
        ),
        "unresolvedOriginBands": sum(
            band["locationStatus"] == "unresolved" for band in bands
        ),
        "resolvedOriginPlaces": len(places),
        "ukOriginPlaces": sum(
            place["locationStatus"] == "uk" for place in places
        ),
        "outsideUkPlaces": sum(
            place["locationStatus"] == "outside_uk" for place in places
        ),
        "bandsWithGenre": sum(bool(band["genres"]) for band in bands),
        "bandsWithWikipedia": sum(
            band["wikipediaUrl"] is not None for band in bands
        ),
        "strictFuaMappedBands": sum(band["fuaCode"] is not None for band in bands),
        "strictFuaCount": len(fuas),
    }
    for key, value in counts.items():
        if meta[key] != value:
            raise ValueError(f"Metadata count mismatch for {key}")
    if counts["resolvedOriginBands"] < BASELINE_RESOLVED_BANDS:
        raise ValueError("Resolved-origin coverage regressed below reviewed baseline")
    if counts["bandsWithGenre"] < BASELINE_GENRE_BANDS:
        raise ValueError("Genre coverage regressed below reviewed baseline")
    if counts["bandsWithWikipedia"] < BASELINE_WIKIPEDIA_BANDS:
        raise ValueError("Wikipedia coverage regressed below reviewed baseline")

    return {
        "status": "passed",
        "schemaVersion": payload["schemaVersion"],
        "snapshotId": meta["snapshotId"],
        "sourceFilename": meta["sourceFilename"],
        "counts": counts,
        "checks": [
            "1,000 unique Spotify artists and complete catalog ranks",
            "deterministic Spotify and captured-title Wikipedia URLs",
            "complete reviewed location status for every resolved origin",
            "valid UK coordinates and null outside-UK map coordinates",
            "deduplicated genres and contiguous place ranks",
            "strict reviewed FUA assignments, positive 2024 denominators, and contiguous FUA ranks",
            "UTC-aware freshness and config-matched provenance",
            "coverage at or above reviewed baselines",
        ],
    }


def build_dashboard() -> tuple[dict[str, object], dict[str, object]]:
    catalog_rows = _read_csv(
        POPULARITY_FIRST_TOP1000_BANDS_PATH, CATALOG_REQUIRED_COLUMNS
    )
    genre_rows = _read_csv(GENRE_AUDIT_PATH, GENRE_REQUIRED_COLUMNS)
    coordinate_rows = _read_csv(
        ORIGIN_COORDINATES_PATH, COORDINATE_REQUIRED_COLUMNS
    )
    fua_mapping_rows = _read_csv(
        FUA_MAPPING_PATH, FUA_MAPPING_REQUIRED_COLUMNS
    )
    fua_population_rows = _read_csv(
        FUA_POPULATION_PATH, FUA_POPULATION_REQUIRED_COLUMNS
    )
    if not UK_OUTLINE_PATH.is_file():
        raise FileNotFoundError(UK_OUTLINE_PATH)
    if not GENRE_CAPTURE_PATH.is_file():
        raise FileNotFoundError(GENRE_CAPTURE_PATH)

    if len(catalog_rows) != 1000:
        raise ValueError(f"Expected 1,000 catalog rows, found {len(catalog_rows)}")
    catalog_ids = [row["returned_spotify_id"] for row in catalog_rows]
    if len(set(catalog_ids)) != 1000 or any(not value for value in catalog_ids):
        raise ValueError("Canonical catalog must contain 1,000 unique Spotify IDs")

    genre_by_id = {row["returned_spotify_id"]: row for row in genre_rows}
    if len(genre_by_id) != len(genre_rows):
        raise ValueError("Genre audit contains duplicate Spotify IDs")
    missing_genre_rows = set(catalog_ids).difference(genre_by_id)
    if missing_genre_rows:
        raise ValueError(
            f"Genre audit is missing {len(missing_genre_rows)} catalog bands"
        )

    coordinates_by_origin = {
        row["origin_cluster"]: row for row in coordinate_rows
    }
    if len(coordinates_by_origin) != len(coordinate_rows):
        raise ValueError("Coordinate input contains duplicate origin clusters")

    fua_mapping_by_origin = {
        row["origin_cluster"]: row for row in fua_mapping_rows
    }
    if len(fua_mapping_by_origin) != len(fua_mapping_rows):
        raise ValueError("FUA mapping input contains duplicate origin clusters")
    population_by_code = {row["fua_code"]: row for row in fua_population_rows}
    if len(population_by_code) != len(fua_population_rows):
        raise ValueError("FUA population input contains duplicate FUA codes")

    bands: list[dict[str, object]] = []
    for row in catalog_rows:
        band_id = row["returned_spotify_id"]
        monthly_listeners = _integer(row, "monthly_listeners")
        followers = _integer(row, "followers")
        if monthly_listeners < 0 or followers < 0:
            raise ValueError("Spotify metrics must be nonnegative")
        popularity_rank = _integer(row, "popularity_rank")

        origin = row["origin_cluster"]
        if not origin or origin == "Unresolved":
            origin = None
            location = None
        else:
            location = coordinates_by_origin.get(origin)
            if location is None:
                raise ValueError(f"No reviewed location record for {origin}")

        genre = genre_by_id[band_id]
        wikipedia_title = genre["enwiki_title"].strip() or None
        latitude = longitude = None
        if location and location["location_status"] == "uk":
            latitude = float(location["latitude"])
            longitude = float(location["longitude"])
        mapping = fua_mapping_by_origin.get(origin or "")
        fua_code = (
            mapping["fua_code"]
            if mapping and mapping["mapping_tier"] == "strict"
            else None
        )
        if fua_code and fua_code not in population_by_code:
            raise ValueError(f"No population record for {fua_code}")

        bands.append(
            {
                "id": band_id,
                "name": row["spotify_name"],
                "catalogName": row["band_name"] or row["spotify_name"],
                "spotifyUrl": f"https://open.spotify.com/artist/{band_id}",
                "wikipediaTitle": wikipedia_title,
                "wikipediaUrl": _wikipedia_url(wikipedia_title or ""),
                "catalogRank": popularity_rank,
                "monthlyListeners": monthly_listeners,
                "followers": followers,
                "spotifyExtractedAtUtc": _utc(row["stats_extracted_at_utc"]),
                "originCluster": origin,
                "originResolution": row["origin_resolution"] or None,
                "placeType": location["place_type"] if location else None,
                "locationStatus": (
                    location["location_status"] if location else "unresolved"
                ),
                "latitude": latitude,
                "longitude": longitude,
                "fuaCode": fua_code,
                "fuaMappingTier": mapping["mapping_tier"] if mapping else None,
                "genres": _split_values(genre["genre_labels"]),
                "genreFamilies": _split_values(genre["genre_families"]),
                "placeRankMonthlyListeners": None,
                "placeRankFollowers": None,
                "fuaRankMonthlyListeners": None,
                "fuaRankFollowers": None,
            }
        )

    _rank_bands(
        bands,
        "monthlyListeners",
        "originCluster",
        "placeRankMonthlyListeners",
    )
    _rank_bands(bands, "followers", "originCluster", "placeRankFollowers")
    _rank_bands(
        bands,
        "monthlyListeners",
        "fuaCode",
        "fuaRankMonthlyListeners",
    )
    _rank_bands(bands, "followers", "fuaCode", "fuaRankFollowers")

    bands_by_origin: dict[str, list[dict[str, object]]] = defaultdict(list)
    for band in bands:
        if band["originCluster"]:
            bands_by_origin[str(band["originCluster"])].append(band)

    places: list[dict[str, object]] = []
    for origin in sorted(bands_by_origin, key=str.casefold):
        origin_bands = bands_by_origin[origin]
        location = coordinates_by_origin[origin]
        monthly_leader = min(
            origin_bands, key=lambda band: band["placeRankMonthlyListeners"]
        )
        follower_leader = min(
            origin_bands, key=lambda band: band["placeRankFollowers"]
        )
        places.append(
            {
                "id": origin,
                "label": origin,
                "placeType": location["place_type"],
                "locationStatus": location["location_status"],
                "latitude": (
                    float(location["latitude"])
                    if location["location_status"] == "uk"
                    else None
                ),
                "longitude": (
                    float(location["longitude"])
                    if location["location_status"] == "uk"
                    else None
                ),
                "fuaCode": (
                    fua_mapping_by_origin[origin]["fua_code"]
                    if fua_mapping_by_origin[origin]["mapping_tier"] == "strict"
                    else None
                ),
                "bandCount": len(origin_bands),
                "monthlyListenersTotal": sum(
                    int(band["monthlyListeners"]) for band in origin_bands
                ),
                "followersTotal": sum(
                    int(band["followers"]) for band in origin_bands
                ),
                "leadingBandMonthlyListenersId": monthly_leader["id"],
                "leadingBandFollowersId": follower_leader["id"],
            }
        )

    bands_by_fua: dict[str, list[dict[str, object]]] = defaultdict(list)
    origins_by_fua: dict[str, set[str]] = defaultdict(set)
    for band in bands:
        if band["fuaCode"]:
            fua_code = str(band["fuaCode"])
            bands_by_fua[fua_code].append(band)
            origins_by_fua[fua_code].add(str(band["originCluster"]))

    fuas: list[dict[str, object]] = []
    for fua_code in sorted(
        bands_by_fua,
        key=lambda code: population_by_code[code]["study_city_label"].casefold(),
    ):
        population_row = population_by_code[fua_code]
        population = _integer(population_row, "population")
        label = population_row["study_city_label"]
        fua_bands = bands_by_fua[fua_code]
        origin_locations = [
            coordinates_by_origin[origin]
            for origin in sorted(origins_by_fua[fua_code], key=str.casefold)
            if coordinates_by_origin[origin]["location_status"] == "uk"
        ]
        label_location = coordinates_by_origin.get(label)
        if label_location and label_location["location_status"] == "uk":
            latitude = float(label_location["latitude"])
            longitude = float(label_location["longitude"])
            coordinate_method = "label_formation_place"
        elif origin_locations:
            latitude = sum(float(row["latitude"]) for row in origin_locations) / len(origin_locations)
            longitude = sum(float(row["longitude"]) for row in origin_locations) / len(origin_locations)
            coordinate_method = "mapped_formation_place_centroid"
        else:
            raise ValueError(f"No representative coordinate for {label} FUA")
        monthly_total = sum(int(band["monthlyListeners"]) for band in fua_bands)
        followers_total = sum(int(band["followers"]) for band in fua_bands)
        monthly_leader = min(
            fua_bands, key=lambda band: band["fuaRankMonthlyListeners"]
        )
        follower_leader = min(
            fua_bands, key=lambda band: band["fuaRankFollowers"]
        )
        fuas.append(
            {
                "id": fua_code,
                "label": label,
                "officialName": population_row["official_fua_name"],
                "placeType": "fua",
                "locationStatus": "uk",
                "latitude": latitude,
                "longitude": longitude,
                "coordinateMethod": coordinate_method,
                "populationYear": FUA_POPULATION_YEAR,
                "population": population,
                "bandCount": len(fua_bands),
                "formationPlaceCount": len(origins_by_fua[fua_code]),
                "monthlyListenersTotal": monthly_total,
                "followersTotal": followers_total,
                "monthlyListenersPerResident": monthly_total / population,
                "followersPerResident": followers_total / population,
                "leadingBandMonthlyListenersId": monthly_leader["id"],
                "leadingBandFollowersId": follower_leader["id"],
            }
        )

    genre_capture = json.loads(GENRE_CAPTURE_PATH.read_text(encoding="utf-8"))
    spotify_freshness = max(
        _utc(row["stats_extracted_at_utc"]) for row in catalog_rows
    )
    coordinate_freshness = max(
        _utc(row["captured_at_utc"]) for row in coordinate_rows
    )
    fua_mapping_freshness = _capture_date_from_filename(FUA_MAPPING_PATH)
    population_freshness = max(
        _utc(row["captured_at_utc"]) for row in fua_population_rows
    )
    genre_freshness = _utc(genre_capture["captured_at_utc"])
    built_at = datetime.now(timezone.utc).isoformat()

    meta = {
        "builtAtUtc": built_at,
        "snapshotId": POPULARITY_FIRST_SNAPSHOT_ID,
        "sourceFilename": POPULARITY_FIRST_TOP1000_BANDS_PATH.name,
        "sourcePath": _relative(POPULARITY_FIRST_TOP1000_BANDS_PATH),
        "catalogBands": len(bands),
        "recordCount": len(bands),
        "resolvedOriginBands": sum(
            band["originCluster"] is not None for band in bands
        ),
        "ukLocatedBands": sum(
            band["locationStatus"] == "uk" for band in bands
        ),
        "outsideUkBands": sum(
            band["locationStatus"] == "outside_uk" for band in bands
        ),
        "unresolvedOriginBands": sum(
            band["locationStatus"] == "unresolved" for band in bands
        ),
        "resolvedOriginPlaces": len(places),
        "ukOriginPlaces": sum(
            place["locationStatus"] == "uk" for place in places
        ),
        "outsideUkPlaces": sum(
            place["locationStatus"] == "outside_uk" for place in places
        ),
        "bandsWithGenre": sum(bool(band["genres"]) for band in bands),
        "bandsWithWikipedia": sum(
            band["wikipediaUrl"] is not None for band in bands
        ),
        "strictFuaMappedBands": sum(
            band["fuaCode"] is not None for band in bands
        ),
        "strictFuaCount": len(fuas),
        "strictFuaMonthlyListenerShare": (
            sum(
                int(band["monthlyListeners"])
                for band in bands
                if band["fuaCode"] is not None
            )
            / sum(int(band["monthlyListeners"]) for band in bands)
        ),
        "strictFuaFollowerShare": (
            sum(
                int(band["followers"])
                for band in bands
                if band["fuaCode"] is not None
            )
            / sum(int(band["followers"]) for band in bands)
        ),
        "fuaPopulationYear": FUA_POPULATION_YEAR,
        "freshness": {
            "spotify": spotify_freshness,
            "coordinates": coordinate_freshness,
            "genres": genre_freshness,
            "fuaMapping": fua_mapping_freshness,
            "population": population_freshness,
        },
        "sources": [
            {
                "label": "Popularity-first top-1,000 catalog and Spotify snapshot",
                "path": _relative(POPULARITY_FIRST_TOP1000_BANDS_PATH),
                "capturedAtUtc": spotify_freshness,
                "sourceUrl": None,
            },
            {
                "label": "Reviewed formation-place coordinates",
                "path": _relative(ORIGIN_COORDINATES_PATH),
                "capturedAtUtc": coordinate_freshness,
                "sourceUrl": "https://www.wikidata.org/",
            },
            {
                "label": "English Wikipedia titles (Wikidata)",
                "path": _relative(GENRE_AUDIT_PATH),
                "capturedAtUtc": genre_freshness,
                "sourceUrl": genre_capture["source_url"],
            },
            {
                "label": "Natural Earth United Kingdom outline",
                "path": _relative(UK_OUTLINE_PATH),
                "capturedAtUtc": _capture_date_from_filename(UK_OUTLINE_PATH),
                "sourceUrl": "https://www.naturalearthdata.com/",
            },
            {
                "label": "Strict reviewed formation-place to FUA mapping",
                "path": _relative(FUA_MAPPING_PATH),
                "capturedAtUtc": fua_mapping_freshness,
                "sourceUrl": None,
            },
            {
                "label": "2024 OECD Functional Urban Area population",
                "path": _relative(FUA_POPULATION_PATH),
                "capturedAtUtc": population_freshness,
                "sourceUrl": fua_population_rows[0]["source_dataset_url"],
            },
        ],
    }
    payload = {
        "schemaVersion": 3,
        "meta": meta,
        "bands": bands,
        "places": places,
        "fuas": fuas,
    }
    return payload, _validate_package(payload, coordinate_rows)


def main() -> None:
    payload, validation = build_dashboard()
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(UK_OUTLINE_PATH, OUTLINE_BROWSER_PATH)
    print(DASHBOARD_PATH.relative_to(PROJECT_ROOT))
    print(VALIDATION_PATH.relative_to(PROJECT_ROOT))
    print(OUTLINE_BROWSER_PATH.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
