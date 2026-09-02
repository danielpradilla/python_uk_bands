#!/usr/bin/env python3
"""Freeze geography, coordinates, and licensed band photos for the map notebook."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.output_share import build_output_share_metrics  # noqa: E402


SNAPSHOT_ID = "20260718T204522Z"
POPULATION_YEAR = 2024
POPULATION_SNAPSHOT_ID = "20260830T221015Z"
ASSET_DATE = "20260723"
TOP_CITY_COUNT = 10
USER_AGENT = (
    "uk-music-cities/1.0 (reproducible research notebook; "
    "https://github.com/dpradilla/uk-music-cities)"
)
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
NATURAL_EARTH_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)


CITY_SPECS = {
    "UK001F": {
        "city_qid": "Q84",
        "band_qid": "Q45188",
        "band_name": "Coldplay",
        "commons_filename": "ColdplayWembley120925 (cropped).jpg",
    },
    "UK008F": {
        "city_qid": "Q18125",
        "band_qid": "Q382890",
        "band_name": "Oasis",
        "commons_filename": (
            "Oasis - Wembley Stadium - Saturday 27th September 2025.jpg"
        ),
    },
    "UK010F": {
        "city_qid": "Q42448",
        "band_qid": "Q170599",
        "band_name": "Arctic Monkeys",
        "commons_filename": (
            "Arctic Monkeys - Orange Stage - Roskilde Festival 2014.jpg"
        ),
    },
    "UK006F": {
        "city_qid": "Q24826",
        "band_qid": "Q1299",
        "band_name": "The Beatles",
        "commons_filename": "Beatles Trenter 1963.jpg",
    },
    "UK002F": {
        "city_qid": "Q2256",
        "band_qid": "Q47670",
        "band_name": "Black Sabbath",
        "commons_filename": "Black Sabbath (1970).png",
    },
    "UK560F": {
        "city_qid": "Q34217",
        "band_qid": "Q44190",
        "band_name": "Radiohead",
        "commons_filename": "RadioheadO2211125 composite.jpg",
    },
    "UK004F": {
        "city_qid": "Q4093",
        "band_qid": "Q173180",
        "band_name": "Franz Ferdinand",
        "commons_filename": "Franz Ferdinand.jpg",
    },
    "UK003F": {
        "city_qid": "Q39121",
        "band_qid": "Q47996",
        "band_name": "alt-J",
        "commons_filename": "Alt-J, Pryzm, Kingston (52132709047).jpg",
    },
    "UK018F": {
        "city_qid": "Q134672",
        "band_qid": "Q22151",
        "band_name": "Muse",
        "commons_filename": "Muse 2006 003.jpg",
    },
    "UK576F": {
        "city_qid": "Q844908",
        "band_qid": "Q484427",
        "band_name": "The Cure",
        "commons_filename": (
            "The Cure Live in Singapore 2- 1st August 2007.jpg"
        ),
    },
}


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str) -> str:
    parser = _PlainTextParser()
    parser.feed(value or "")
    return " ".join(" ".join(parser.parts).split())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _request_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    attempts: int = 4,
) -> dict[str, Any]:
    for attempt in range(attempts):
        response = session.get(url, params=params, timeout=90)
        if response.ok:
            return response.json()
        if attempt == attempts - 1:
            response.raise_for_status()
        time.sleep(2**attempt)
    raise RuntimeError("Unreachable request retry state")


def _request_bytes(
    session: requests.Session,
    url: str,
    *,
    attempts: int = 4,
) -> bytes:
    for attempt in range(attempts):
        response = session.get(url, timeout=120)
        if response.ok:
            return response.content
        if attempt == attempts - 1:
            response.raise_for_status()
        time.sleep(2**attempt)
    raise RuntimeError("Unreachable request retry state")


def _claim_value(entity: dict[str, Any], property_id: str) -> Any:
    claims = entity.get("claims", {}).get(property_id, [])
    if not claims:
        raise ValueError(
            f"{entity.get('id', 'Entity')} has no {property_id} claim"
        )
    preferred = [
        claim for claim in claims if claim.get("rank") == "preferred"
    ]
    claim = (preferred or claims)[0]
    return claim["mainsnak"]["datavalue"]["value"]


def _slug(value: str) -> str:
    return "_".join(
        "".join(character.lower() if character.isalnum() else " " for character in value)
        .split()
    )


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _write_bytes(path: Path, content: bytes, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _load_top_cities() -> pd.DataFrame:
    bands = pd.read_csv(
        PROJECT_ROOT
        / f"data/processed/popularity_first_top1000_{SNAPSHOT_ID}_bands.csv",
        keep_default_na=False,
    )
    mapping = pd.read_csv(
        PROJECT_ROOT
        / f"data/interim/popularity_first_top1000_{SNAPSHOT_ID}_fua_mapping_audit.csv",
        keep_default_na=False,
    )
    population = pd.read_csv(
        PROJECT_ROOT
        / (
            f"data/processed/uk_fua_population_{POPULATION_YEAR}_"
            f"{POPULATION_SNAPSHOT_ID}.csv"
        ),
        keep_default_na=False,
    )
    shares, _ = build_output_share_metrics(
        bands,
        mapping,
        population,
        included_tiers={"strict", "reviewed_extended"},
    )
    top = (
        shares.loc[shares["followers_total"].gt(0)]
        .sort_values(
            ["followers_total", "study_city_label"],
            ascending=[False, True],
        )
        .head(TOP_CITY_COUNT)
        .reset_index(drop=True)
    )
    if set(top["fua_code"]) != set(CITY_SPECS):
        raise ValueError(
            "CITY_SPECS no longer matches the top-city set for the frozen data"
        )
    for row in top.itertuples(index=False):
        expected = CITY_SPECS[row.fua_code]["band_name"]
        if row.largest_band_by_followers != expected:
            raise ValueError(
                f"Expected {expected} for {row.fua_code}, got "
                f"{row.largest_band_by_followers}"
            )
    return top


def capture(*, force: bool) -> None:
    top = _load_top_cities()
    captured_at = pd.Timestamp.now(tz="UTC").isoformat()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    geography_path = (
        PROJECT_ROOT
        / "data/raw/geography"
        / f"natural_earth_50m_united_kingdom_{ASSET_DATE}.geojson"
    )
    natural_earth = _request_json(session, NATURAL_EARTH_URL)
    uk_features = [
        feature
        for feature in natural_earth["features"]
        if feature["properties"].get("ADM0_A3") == "GBR"
    ]
    if len(uk_features) != 1:
        raise ValueError(
            f"Expected one GBR feature from Natural Earth, got {len(uk_features)}"
        )
    uk_geojson = {
        "type": "FeatureCollection",
        "name": "United Kingdom — Natural Earth 1:50m Admin 0",
        "features": uk_features,
    }
    geography_bytes = (
        json.dumps(uk_geojson, ensure_ascii=False, separators=(",", ":"))
        .encode("utf-8")
    )
    _write_bytes(geography_path, geography_bytes, force=force)

    city_qids = [CITY_SPECS[code]["city_qid"] for code in top["fua_code"]]
    entity_payload = _request_json(
        session,
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "format": "json",
            "ids": "|".join(city_qids),
            "props": "labels|claims",
            "languages": "en",
        },
    )
    entities = entity_payload["entities"]
    coordinate_rows: list[dict[str, Any]] = []
    for row in top.itertuples(index=False):
        spec = CITY_SPECS[row.fua_code]
        entity = entities[spec["city_qid"]]
        coordinate = _claim_value(entity, "P625")
        coordinate_rows.append(
            {
                "fua_code": row.fua_code,
                "study_city_label": row.study_city_label,
                "city_qid": spec["city_qid"],
                "wikidata_label": entity["labels"]["en"]["value"],
                "latitude": coordinate["latitude"],
                "longitude": coordinate["longitude"],
                "coordinate_source_url": (
                    "https://www.wikidata.org/wiki/" + spec["city_qid"]
                ),
                "captured_at_utc": captured_at,
            }
        )

    commons_filenames = [
        CITY_SPECS[code]["commons_filename"] for code in top["fua_code"]
    ]
    commons_payload = _request_json(
        session,
        COMMONS_API,
        params={
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": "|".join(
                f"File:{filename}" for filename in commons_filenames
            ),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": "900",
        },
    )
    pages_by_filename = {
        page["title"].removeprefix("File:"): page
        for page in commons_payload["query"]["pages"]
    }
    image_dir = (
        PROJECT_ROOT
        / "data/raw/wikimedia"
        / f"top1000_city_band_photos_{ASSET_DATE}"
    )
    manifest_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(top.itertuples(index=False), start=1):
        spec = CITY_SPECS[row.fua_code]
        filename = spec["commons_filename"]
        page = pages_by_filename.get(filename)
        if not page or "imageinfo" not in page:
            raise ValueError(f"Commons image is unavailable: {filename}")
        info = page["imageinfo"][0]
        metadata = info.get("extmetadata", {})

        def metadata_value(key: str) -> str:
            return metadata.get(key, {}).get("value", "")

        download_url = info.get("thumburl") or info["url"]
        image_content = _request_bytes(session, download_url)
        suffix = Path(filename).suffix.lower()
        local_path = image_dir / (
            f"{rank:02d}_{_slug(row.study_city_label)}_"
            f"{_slug(spec['band_name'])}{suffix}"
        )
        _write_bytes(local_path, image_content, force=force)
        license_name = metadata_value("LicenseShortName")
        license_url = metadata_value("LicenseUrl")
        artist = _plain_text(metadata_value("Artist"))
        credit = _plain_text(metadata_value("Credit"))
        attribution = f"{spec['band_name']} photo: {artist or credit}"
        if license_name:
            attribution += f" · {license_name}"
        manifest_rows.append(
            {
                "fua_code": row.fua_code,
                "study_city_label": row.study_city_label,
                "rank_by_followers": rank,
                "band_name": spec["band_name"],
                "band_qid": spec["band_qid"],
                "commons_filename": filename,
                "commons_page_url": info["descriptionurl"],
                "download_url": download_url,
                "local_path": _relative(local_path),
                "image_sha256": _sha256(image_content),
                "artist": artist,
                "credit": credit,
                "license_short_name": license_name,
                "license_url": license_url,
                "attribution_text": attribution,
                "captured_at_utc": captured_at,
            }
        )

    coordinate_path = (
        PROJECT_ROOT
        / "reference"
        / f"top1000_fua_map_coordinates_{ASSET_DATE}.csv"
    )
    manifest_path = (
        PROJECT_ROOT
        / "reference"
        / f"top1000_city_band_photo_manifest_{ASSET_DATE}.csv"
    )
    metadata_path = (
        PROJECT_ROOT
        / "reference"
        / f"top1000_follower_map_asset_capture_{ASSET_DATE}.json"
    )
    for output_path in (coordinate_path, manifest_path, metadata_path):
        if output_path.exists() and not force:
            raise FileExistsError(
                f"Refusing to overwrite {output_path}; pass --force"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(coordinate_rows).to_csv(coordinate_path, index=False)
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    capture_metadata = {
        "asset_date": ASSET_DATE,
        "captured_at_utc": captured_at,
        "top_city_count": TOP_CITY_COUNT,
        "study_snapshot_id": SNAPSHOT_ID,
        "population_snapshot_id": POPULATION_SNAPSHOT_ID,
        "natural_earth": {
            "source_url": NATURAL_EARTH_URL,
            "source_page_url": (
                "https://www.naturalearthdata.com/downloads/50m-cultural-vectors/"
                "50m-admin-0-countries-2/"
            ),
            "terms_url": "https://www.naturalearthdata.com/about/terms-of-use/",
            "license": "Public domain",
            "local_path": _relative(geography_path),
            "sha256": _sha256(geography_bytes),
        },
        "wikidata": {
            "api_url": WIKIDATA_API,
            "coordinate_property": "P625",
            "license": "CC0 1.0",
            "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
            "local_path": _relative(coordinate_path),
        },
        "wikimedia_commons": {
            "api_url": COMMONS_API,
            "manifest_path": _relative(manifest_path),
            "note": "Per-file creators and licences are stored in the manifest.",
        },
    }
    metadata_path.write_text(
        json.dumps(capture_metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {_relative(geography_path)}")
    print(f"Saved {_relative(coordinate_path)}")
    print(f"Saved {_relative(manifest_path)}")
    print(f"Saved {_relative(metadata_path)}")
    print(f"Saved {len(manifest_rows)} licensed photos under {_relative(image_dir)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    capture(force=args.force)


if __name__ == "__main__":
    main()
