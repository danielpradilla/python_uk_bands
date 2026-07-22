#!/usr/bin/env python3
"""Capture Wikidata labels and administrative parents for band origins."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_json  # noqa: E402


WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-depth", type=int, default=6)
    return parser


def _parents(entity: dict) -> list[str]:
    parents: list[str] = []
    for claim in entity.get("claims", {}).get("P131", []):
        value = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
        )
        if isinstance(value, dict) and value.get("id"):
            parents.append(str(value["id"]))
    return sorted(set(parents))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bands = pd.read_csv(args.bands, keep_default_na=False)
    if "formation_qid" not in bands.columns:
        raise ValueError("Bands input requires formation_qid")
    seed_qids = sorted(
        {
            qid
            for value in bands["formation_qid"]
            for qid in str(value).split("|")
            if re.fullmatch(r"Q\d+", qid)
        }
    )

    session = requests.Session()
    session.headers["User-Agent"] = (
        "uk-music-cities/1.0 (research mapping; info@danielpradilla.info)"
    )
    raw_entities: dict[str, dict] = {}
    frontier = set(seed_qids)
    for _ in range(args.max_depth + 1):
        pending = sorted(frontier.difference(raw_entities))
        if not pending:
            break
        for start in range(0, len(pending), 50):
            response = session.get(
                WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "format": "json",
                    "props": "claims|labels",
                    "languages": "en",
                    "ids": "|".join(pending[start : start + 50]),
                },
                timeout=60,
            )
            response.raise_for_status()
            raw_entities.update(response.json()["entities"])
        frontier = {
            parent
            for qid in pending
            for parent in _parents(raw_entities.get(qid, {}))
        }

    entities = {
        qid: {
            "label": entity.get("labels", {}).get("en", {}).get("value", ""),
            "located_in": _parents(entity),
        }
        for qid, entity in sorted(raw_entities.items())
    }
    output = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": WIKIDATA_API,
        "bands_input": str(args.bands.resolve().relative_to(PROJECT_ROOT)),
        "max_depth": args.max_depth,
        "seed_qids": seed_qids,
        "entities": entities,
    }
    output_path = args.output.resolve()
    write_json(output, output_path)
    print(output_path.relative_to(PROJECT_ROOT))
    print(f"seed_qids={len(seed_qids)} entities={len(entities)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
