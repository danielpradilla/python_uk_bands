#!/usr/bin/env python3
"""Build a dated, balanced catalogue for the top-20 city-first study."""

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

from python_uk_bands.io import write_csv, write_json
from python_uk_bands.top20 import build_top20_catalog


def _project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scene-depth-catalog",
        type=Path,
        default=PROJECT_ROOT / "reference" / "scene_depth_bands.csv",
    )
    parser.add_argument(
        "--existing-metrics",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "scene_depth_band_metrics_20260717T225650Z.csv"
        ),
    )
    parser.add_argument("--additions-review", required=True, type=Path)
    parser.add_argument(
        "--fua-universe",
        type=Path,
        default=PROJECT_ROOT / "reference" / "uk_fua_top20_2021.csv",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = (
        PROJECT_ROOT
        / "data"
        / "interim"
        / f"top20_city_band_catalog_{timestamp}.csv"
    )
    report_path = (
        PROJECT_ROOT
        / "data"
        / "interim"
        / f"top20_city_band_catalog_{timestamp}_report.json"
    )

    catalogue = build_top20_catalog(
        scene_depth_catalog=pd.read_csv(
            args.scene_depth_catalog,
            keep_default_na=False,
        ),
        existing_metrics=pd.read_csv(
            args.existing_metrics,
            keep_default_na=False,
        ),
        additions_review=pd.read_csv(
            args.additions_review,
            keep_default_na=False,
        ),
        fua_universe=pd.read_csv(
            args.fua_universe,
            keep_default_na=False,
        ),
    )
    write_csv(catalogue, output_path)
    pending = catalogue.loc[
        ~catalogue["catalogue_review_ready"],
        ["band_name", "study_city_label", "origin_review_status", "spotify_id"],
    ]
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalogue_rows": len(catalogue),
        "cities": catalogue["study_city_label"].nunique(),
        "bands_per_city": sorted(
            catalogue.groupby("study_city_label").size().unique().tolist()
        ),
        "review_ready_rows": int(catalogue["catalogue_review_ready"].sum()),
        "pending_review_rows": len(pending),
        "missing_spotify_ids": int(catalogue["spotify_id"].eq("").sum()),
        "status": (
            "publication_ready"
            if pending.empty
            else "provisional_origin_review_incomplete"
        ),
        "pending_bands": pending.to_dict("records"),
        "input_paths": {
            "scene_depth_catalog": _project_relative(args.scene_depth_catalog),
            "existing_metrics": _project_relative(args.existing_metrics),
            "additions_review": _project_relative(args.additions_review),
            "fua_universe": _project_relative(args.fua_universe),
        },
        "output_path": str(output_path.relative_to(PROJECT_ROOT)),
        "canonical_files_modified": False,
    }
    write_json(report, report_path)
    print(f"Catalogue: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
