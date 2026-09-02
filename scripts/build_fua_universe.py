#!/usr/bin/env python3
"""Fetch and freeze a population-ranked UK Functional Urban Area universe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.fua import (
    build_uk_fua_universe,
    fetch_oecd_fua_population,
    validate_top_fua_universe,
)
from python_uk_bands.io import write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Write the selected universe to reference/uk_fua_top20_2024.csv",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    captured_at = datetime.now(timezone.utc)
    timestamp = captured_at.strftime("%Y%m%dT%H%M%SZ")
    raw_csv, request_url = fetch_oecd_fua_population(args.year)

    all_uk = build_uk_fua_universe(
        raw_csv,
        year=args.year,
        captured_at_utc=captured_at.isoformat(),
    )
    selected = all_uk.head(args.top_n).copy()
    validate_top_fua_universe(
        selected,
        expected_rows=args.top_n,
        year=args.year,
    )

    raw_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "geography"
        / f"oecd_fua_population_{args.year}_{timestamp}.csv"
    )
    all_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"uk_fua_population_{args.year}_{timestamp}.csv"
    )
    selected_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"uk_fua_top{args.top_n}_{args.year}_{timestamp}.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "geography"
        / f"oecd_fua_population_{args.year}_{timestamp}_report.json"
    )

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(raw_csv)
    write_csv(all_uk, all_path)
    write_csv(selected, selected_path)
    report = {
        "captured_at_utc": captured_at.isoformat(),
        "request_url": request_url,
        "reference_year": args.year,
        "uk_fua_rows": len(all_uk),
        "selected_rows": len(selected),
        "top_n": args.top_n,
        "observation_statuses": sorted(
            selected["observation_status"].unique().tolist()
        ),
        "promoted": bool(args.promote),
    }

    if args.promote:
        if args.top_n != 20 or args.year != 2024:
            raise ValueError(
                "The canonical reference path is reserved for top 20 / 2024"
            )
        reference_path = (
            PROJECT_ROOT / "reference" / "uk_fua_top20_2024.csv"
        )
        write_csv(selected, reference_path)
        report["reference_path"] = str(reference_path.relative_to(PROJECT_ROOT))

    write_json(report, report_path)
    print(f"Raw source snapshot: {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Processed UK universe: {all_path.relative_to(PROJECT_ROOT)}")
    print(f"Selected study universe: {selected_path.relative_to(PROJECT_ROOT)}")
    if args.promote:
        print("Reference universe: reference/uk_fua_top20_2024.csv")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
