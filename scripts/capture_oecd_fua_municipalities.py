#!/usr/bin/env python3
"""Capture the official OECD UK municipality-to-FUA crosswalk."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.fua_mapping import OECD_MUNICIPALITY_SOURCE  # noqa: E402
from python_uk_bands.io import write_csv, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    response = requests.get(
        OECD_MUNICIPALITY_SOURCE,
        headers={"User-Agent": "uk-music-cities/1.0 (research capture)"},
        timeout=60,
    )
    response.raise_for_status()
    complete = pd.read_csv(BytesIO(response.content), keep_default_na=False)
    required = {
        "Country",
        "ISO3 code",
        "Municipality name",
        "FUA ID",
        "FUA name",
    }
    missing = required.difference(complete.columns)
    if missing:
        raise ValueError(f"OECD crosswalk is missing columns: {sorted(missing)}")
    uk = complete.loc[complete["ISO3 code"].eq("GBR")].copy()
    if uk.empty or uk["Municipality name"].duplicated().any():
        raise ValueError("Expected unique UK municipality rows")

    output_path = args.output.resolve()
    report_path = output_path.with_name(f"{output_path.stem}_report.json")
    write_csv(uk, output_path)
    captured_at = datetime.now(timezone.utc).isoformat()
    report = {
        "captured_at_utc": captured_at,
        "source_url": OECD_MUNICIPALITY_SOURCE,
        "source_sha256": hashlib.sha256(response.content).hexdigest(),
        "source_rows": len(complete),
        "uk_rows": len(uk),
        "uk_fuas": int(uk["FUA ID"].nunique()),
        "output": str(output_path.relative_to(PROJECT_ROOT)),
    }
    write_json(report, report_path)
    print(output_path.relative_to(PROJECT_ROOT))
    print(report_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
