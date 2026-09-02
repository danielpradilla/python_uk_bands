#!/usr/bin/env python3
"""Capture reviewed representative coordinates for explorer origin clusters."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.config import (  # noqa: E402
    POPULARITY_FIRST_TOP1000_BANDS_PATH,
)


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "uk-music-cities-interactive/1.0 (contact: info@danielpradilla.info)"

QID_OVERRIDES = {
    "Bradford": "Q22905",
    "Canterbury": "Q29303",
    "Cheshunt": "Q19790",
    "Crosby": "Q1141046",
    "Dagenham": "Q1075299",
    "Hertford": "Q9681",
    "Isle of Wight": "Q9679",
    "Isle of Skye": "Q107393",
    "Meriden": "Q1747363",
    "Redcliffe": "Q1026184",
    "St Andrews": "Q207736",
    "Sunderland": "Q188304",
    "Wallasey": "Q780923",
    "Water Orton": "Q1858244",
    "West Lothian": "Q204940",
}

OUTSIDE_UK_ORIGINS = {
    "Dublin": "Q1761",
    "Greece": "Q41",
    "Hamburg": "Q1055",
    "New York City": "Q60",
    "Redcliffe": "Q1026184",
    "United States": "Q30",
}

REGION_ORIGINS = {
    "Buckinghamshire",
    "Cambridgeshire",
    "County Tyrone",
    "Dorset",
    "Essex",
    "Hampshire",
    "Herefordshire",
    "Isle of Wight",
    "Leicestershire",
    "Norfolk",
    "Northern Ireland",
    "Scotland",
    "Shropshire",
    "Somerset",
    "Suffolk",
    "Tyne and Wear",
    "Wales",
    "West Lothian",
    "West Midlands",
    "Worcestershire",
}

DISTRICT_ORIGINS = {
    "Battersea",
    "Brixton",
    "Catford",
    "Chelsea",
    "Chingford",
    "Crouch End",
    "Dalmarnock",
    "Ealing",
    "East End of London",
    "Ladbroke Grove",
    "Little Hulton",
    "North London",
    "Notting Hill",
    "Peckham",
    "Plumstead",
    "South London",
    "Tottenham",
    "Walthamstow",
    "Westminster",
    "Wimbledon",
}


def _catalog_rows() -> list[dict[str, str]]:
    with POPULARITY_FIRST_TOP1000_BANDS_PATH.open(
        newline="", encoding="utf-8"
    ) as source:
        return list(csv.DictReader(source))


def _origin_qids(rows: list[dict[str, str]]) -> dict[str, str]:
    origins = sorted(
        {
            row["origin_cluster"]
            for row in rows
            if row["origin_cluster"]
            and row["origin_cluster"] != "Unresolved"
        }
    )
    qids: dict[str, str] = {}
    for origin in origins:
        if origin in QID_OVERRIDES:
            qids[origin] = QID_OVERRIDES[origin]
            continue
        exact_qids = {
            qid
            for row in rows
            if row["origin_cluster"] == origin
            for qid, label in zip(
                row["formation_qid"].split("|"),
                row["formation_label"].split("|"),
            )
            if qid and label == origin
        }
        if len(exact_qids) != 1:
            raise ValueError(
                f"{origin!r} needs a reviewed QID override: {sorted(exact_qids)}"
            )
        qids[origin] = exact_qids.pop()
    return qids


def _wikidata_entities(qids: set[str]) -> dict[str, object]:
    entities: dict[str, object] = {}
    ordered = sorted(qids)
    for start in range(0, len(ordered), 40):
        query = urlencode(
            {
                "action": "wbgetentities",
                "ids": "|".join(ordered[start : start + 40]),
                "props": "claims|labels",
                "languages": "en|en-gb",
                "languagefallback": "1",
                "format": "json",
            }
        )
        request = Request(
            f"{WIKIDATA_API}?{query}", headers={"User-Agent": USER_AGENT}
        )
        with urlopen(request, timeout=30) as response:
            entities.update(json.load(response)["entities"])
    return entities


def _coordinate(entity: dict[str, object]) -> tuple[float, float]:
    claims = entity.get("claims", {})
    statements = claims.get("P625", [])
    if not statements:
        raise ValueError("Wikidata entity has no coordinate statement")
    value = statements[0]["mainsnak"]["datavalue"]["value"]
    return float(value["latitude"]), float(value["longitude"])


def _place_type(origin: str) -> str:
    if origin == "United States":
        return "country"
    if origin in REGION_ORIGINS:
        return "region"
    if origin in DISTRICT_ORIGINS:
        return "district"
    if origin == "University of Leeds":
        return "institution"
    return "locality"


def capture(output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite immutable coordinate capture: {output_path}"
        )

    qids = _origin_qids(_catalog_rows())
    if {origin for origin in qids if origin in OUTSIDE_UK_ORIGINS} != set(
        OUTSIDE_UK_ORIGINS
    ):
        raise ValueError("Outside-UK origin review is incomplete")

    entities = _wikidata_entities(set(qids.values()))
    captured_at = datetime.now(timezone.utc).isoformat()
    captured_rows = []
    for origin, qid in qids.items():
        outside_uk = origin in OUTSIDE_UK_ORIGINS
        latitude = longitude = ""
        notes = "Resolved origin retained outside the UK map."
        if not outside_uk:
            latitude_value, longitude_value = _coordinate(entities[qid])
            if not (
                49 <= latitude_value <= 61.5
                and -9 <= longitude_value <= 2.5
            ):
                raise ValueError(
                    f"Coordinate outside broad UK bounds: {origin} "
                    f"({latitude_value}, {longitude_value})"
                )
            latitude = f"{latitude_value:.12g}"
            longitude = f"{longitude_value:.12g}"
            notes = (
                "Representative Wikidata coordinate; region-level origins use "
                "the source entity's representative point."
                if origin in REGION_ORIGINS
                else "Representative Wikidata coordinate for the reviewed origin."
            )
        captured_rows.append(
            {
                "origin_cluster": origin,
                "place_type": _place_type(origin),
                "location_status": "outside_uk" if outside_uk else "uk",
                "wikidata_qid": qid,
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_source_url": f"https://www.wikidata.org/wiki/{qid}",
                "captured_at_utc": captured_at,
                "review_notes": notes,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(captured_rows[0]))
        writer.writeheader()
        writer.writerows(captured_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    capture(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
