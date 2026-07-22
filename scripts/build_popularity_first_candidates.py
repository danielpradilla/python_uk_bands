#!/usr/bin/env python3
"""Build a frozen Spotify-capture table from a Wikidata query response.

The input is an archived Wikidata SPARQL JSON response containing UK musical
groups, Spotify artist identifiers, and formation places. The output keeps one
row per unique Spotify artist identifier. Multiple identifiers attached to the
same Wikidata entity are deliberately retained for later identity review.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_csv, write_json


def _value(binding: dict, key: str) -> str:
    return binding.get(key, {}).get("value", "")


def _entity_id(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else ""


def build_candidates(payload: dict) -> pd.DataFrame:
    """Return one deterministic capture row per Spotify artist identifier."""

    rows = []
    for binding in payload["results"]["bindings"]:
        qid = _entity_id(_value(binding, "item"))
        spotify_id = _value(binding, "spotifyId")
        band_name = _value(binding, "itemLabel")
        formation_qid = _entity_id(_value(binding, "formation"))
        formation_label = _value(binding, "formationLabel")
        rows.append(
            {
                "wikidata_qid": qid,
                "band_name": band_name,
                "spotify_id": spotify_id,
                "spotify_expected_name": band_name,
                "formation_qid": formation_qid,
                "formation_label": formation_label,
                "instance_label": _value(binding, "instanceLabel"),
                "country_label": _value(binding, "countryLabel"),
            }
        )

    frame = pd.DataFrame(rows).drop_duplicates()
    grouped = (
        frame.groupby(["spotify_id"], as_index=False, dropna=False)
        .agg(
            wikidata_qid=(
                "wikidata_qid",
                lambda values: "|".join(sorted(set(filter(None, values)))),
            ),
            band_name=(
                "band_name",
                lambda values: " / ".join(sorted(set(filter(None, values)))),
            ),
            spotify_expected_name=(
                "spotify_expected_name",
                lambda values: " / ".join(sorted(set(filter(None, values)))),
            ),
            formation_qid=(
                "formation_qid",
                lambda values: "|".join(sorted(set(filter(None, values)))),
            ),
            formation_label=(
                "formation_label",
                lambda values: "|".join(sorted(set(filter(None, values)))),
            ),
            instance_label=(
                "instance_label",
                lambda values: "|".join(sorted(set(filter(None, values)))),
            ),
            country_label=(
                "country_label",
                lambda values: "|".join(sorted(set(filter(None, values)))),
            ),
        )
        .sort_values(["band_name", "wikidata_qid", "spotify_id"])
        .reset_index(drop=True)
    )
    grouped.insert(
        0,
        "capture_key",
        grouped["band_name"] + " [" + grouped["spotify_id"] + "]",
    )
    if grouped["capture_key"].duplicated().any():
        raise ValueError("Capture keys must be unique")
    if grouped["spotify_id"].duplicated().any():
        raise ValueError("Spotify identifiers must be unique after aggregation")
    return grouped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input.resolve()
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    candidates = build_candidates(payload)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = (
        args.output
        or PROJECT_ROOT
        / "data"
        / "interim"
        / f"uk_group_spotify_candidates_{timestamp}.csv"
    ).resolve()
    report_path = output_path.with_name(f"{output_path.stem}_report.json")

    write_csv(candidates, output_path)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path.relative_to(PROJECT_ROOT)),
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
        "wikidata_bindings": len(payload["results"]["bindings"]),
        "candidate_spotify_ids": len(candidates),
        "wikidata_entities": len(
            {
                qid
                for value in candidates["wikidata_qid"]
                for qid in value.split("|")
            }
        ),
        "entities_with_multiple_spotify_ids": int(
            (
                candidates.assign(
                    wikidata_qid=candidates["wikidata_qid"].str.split("|")
                )
                .explode("wikidata_qid")
                .groupby("wikidata_qid")
                .size()
                > 1
            ).sum()
        ),
        "unresolved_formation_labels": int(
            candidates["formation_label"].str.match(r"^(Q\d+)(\|Q\d+)*$").sum()
        ),
        "empty_formation_labels": int(
            candidates["formation_label"].eq("").sum()
        ),
        "selection_frame": (
            "Wikidata entities returned by the archived UK musical-group "
            "query that have a Spotify artist identifier"
        ),
        "canonical_files_modified": False,
    }
    write_json(report, report_path)
    print(output_path.relative_to(PROJECT_ROOT))
    print(report_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
