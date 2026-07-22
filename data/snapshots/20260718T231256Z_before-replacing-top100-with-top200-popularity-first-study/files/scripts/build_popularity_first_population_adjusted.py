#!/usr/bin/env python3
"""Build population-adjusted views of a frozen popularity-first top 100."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_csv, write_json
from python_uk_bands.popularity_first import (
    attach_fua_population,
    build_population_adjusted_metrics,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", required=True, type=Path)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--population", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    return parser


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bands = pd.read_csv(args.bands, keep_default_na=False)
    origins = pd.read_csv(args.origins, keep_default_na=False)
    mapping = pd.read_csv(args.mapping, keep_default_na=False)
    population = pd.read_csv(args.population, keep_default_na=False)

    if len(bands) != 100 or bands["returned_spotify_id"].nunique() != 100:
        raise ValueError("Population-adjusted experiment requires 100 bands")
    if origins["band_count"].sum() != 100:
        raise ValueError("Raw origin concentration must cover all 100 bands")

    attached = attach_fua_population(bands, mapping, population)
    strict, strict_coverage = build_population_adjusted_metrics(
        attached,
        included_tiers={"strict"},
    )
    extended, extended_coverage = build_population_adjusted_metrics(
        attached,
        included_tiers={"strict", "reviewed_extended"},
    )

    prefix = f"popularity_first_top100_{args.snapshot_id}"
    audit_path = (
        PROJECT_ROOT / "data" / "interim" / f"{prefix}_fua_mapping_audit.csv"
    )
    strict_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"{prefix}_population_strict.csv"
    )
    extended_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"{prefix}_population_extended.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"{prefix}_population_adjusted_report.json"
    )

    audit_columns = [
        "popularity_rank",
        "spotify_name",
        "returned_spotify_id",
        "monthly_listeners",
        "origin_cluster",
        "mapping_tier",
        "mapping_method",
        "fua_code",
        "official_fua_name",
        "study_city_label",
        "population_year",
        "population",
        "notes",
    ]
    write_csv(attached[audit_columns], audit_path)
    write_csv(strict, strict_path)
    write_csv(extended, extended_path)

    unmapped = (
        attached.loc[
            ~attached["mapping_tier"].isin(
                {"strict", "reviewed_extended"}
            ),
            [
                "spotify_name",
                "origin_cluster",
                "monthly_listeners",
                "mapping_tier",
            ],
        ]
        .sort_values("monthly_listeners", ascending=False)
        .to_dict(orient="records")
    )
    strict_top_stable = (
        strict.loc[strict["band_count"].ge(2)]
        .sort_values("rank_by_listener_reach_per_resident")
        .head(10)["study_city_label"]
        .tolist()
    )
    report = {
        "snapshot_id": args.snapshot_id,
        "study_kind": "popularity-first population-adjusted sensitivity",
        "population_definition": "OECD/EU Functional Urban Area",
        "population_year": int(population["population_year"].unique().item()),
        "formulas": {
            "top100_bands_per_million_residents": (
                "selected top-100 band count / FUA population * 1,000,000"
            ),
            "top100_monthly_listeners_per_resident": (
                "sum of captured monthly listeners for selected top-100 "
                "bands / FUA population"
            ),
        },
        "strict_mapping": {
            **strict_coverage,
            "included_tiers": ["strict"],
            "top_fua_by_listener_reach_per_resident": strict.iloc[0][
                "study_city_label"
            ],
            "top_fua_band_count": int(strict.iloc[0]["band_count"]),
            "top_stable_fuas_with_at_least_two_bands": strict_top_stable,
        },
        "extended_mapping_sensitivity": {
            **extended_coverage,
            "included_tiers": ["strict", "reviewed_extended"],
            "top_fua_by_listener_reach_per_resident": extended.iloc[0][
                "study_city_label"
            ],
        },
        "unmapped_after_extended_review": unmapped,
        "interpretation_guardrail": (
            "These rates normalize the output represented in a "
            "popularity-selected top 100. They do not estimate scene depth, "
            "and one-band FUAs are highly sensitive to a single global hit."
        ),
        "inputs": {
            "bands": _relative(args.bands),
            "origins": _relative(args.origins),
            "mapping": _relative(args.mapping),
            "population": _relative(args.population),
        },
        "outputs": {
            "mapping_audit": _relative(audit_path),
            "strict_metrics": _relative(strict_path),
            "extended_metrics": _relative(extended_path),
        },
        "original_popularity_first_outputs_modified": False,
        "published_notebook_modified": False,
    }
    write_json(report, report_path)

    for path in [audit_path, strict_path, extended_path, report_path]:
        print(path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
