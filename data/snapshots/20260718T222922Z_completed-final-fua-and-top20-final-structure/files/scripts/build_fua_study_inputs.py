#!/usr/bin/env python3
"""Freeze standardized top-10 and top-20 FUA scene-depth study inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.fua import validate_top_fua_universe
from python_uk_bands.scene_depth import (
    build_primary_scene_depth_rankings,
    validate_scene_depth_dataset,
)


SNAPSHOT_PATTERN = re.compile(r"_(\d{8}T\d{6}Z)\.csv$")
DEFAULT_UNIVERSE_PATH = PROJECT_ROOT / "reference" / "uk_fua_top20_2021.csv"


def _snapshot_id(path: Path) -> str:
    match = SNAPSHOT_PATTERN.search(path.name)
    if not match:
        raise ValueError(f"Could not recover a UTC snapshot ID from {path}")
    return match.group(1)


def _project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def build_fua_study_inputs(
    *,
    source_metrics_path: Path,
    universe_path: Path,
    city_count: int,
    force: bool = False,
) -> tuple[Path, Path, Path]:
    """Create one balanced FUA metrics file, ranking file, and QA report."""

    source_metrics_path = source_metrics_path.resolve()
    universe_path = universe_path.resolve()
    snapshot_id = _snapshot_id(source_metrics_path)
    metrics_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"fua_top{city_count}_band_metrics_{snapshot_id}.csv"
    )
    rankings_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"fua_top{city_count}_rankings_{snapshot_id}.csv"
    )
    report_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / f"fua_top{city_count}_study_{snapshot_id}_report.json"
    )
    outputs = (metrics_output_path, rankings_output_path, report_output_path)
    existing = [path for path in outputs if path.exists()]
    if existing and not force:
        raise FileExistsError(
            "Refusing to replace frozen study inputs without --force: "
            + ", ".join(str(path) for path in existing)
        )

    universe = pd.read_csv(universe_path, keep_default_na=False)
    validate_top_fua_universe(
        universe.head(city_count).copy(),
        expected_rows=city_count,
        year=2021,
    )

    source_metrics = pd.read_csv(source_metrics_path, keep_default_na=False)
    required_columns = {
        "band",
        "city",
        "monthly_listeners",
        "population",
        "uk_population_rank",
        "fua_code",
        "population_year",
        "spotify_id",
        "catalogue_review_ready",
        "stats_extracted_at_utc",
    }
    missing = sorted(required_columns.difference(source_metrics.columns))
    if missing:
        raise ValueError(f"Source metrics are missing columns: {missing}")

    bands = (
        source_metrics.loc[
            source_metrics["uk_population_rank"].le(city_count)
        ]
        .sort_values(["uk_population_rank", "band"])
        .reset_index(drop=True)
    )
    validate_scene_depth_dataset(
        bands,
        expected_cities=city_count,
        bands_per_city=10,
    )
    if len(bands) != city_count * 10:
        raise ValueError(
            f"Expected {city_count * 10} band rows, found {len(bands)}"
        )
    if not bands["catalogue_review_ready"].astype(bool).all():
        raise ValueError("Every selected band must be review ready")
    if bands["spotify_id"].duplicated().any():
        raise ValueError("Spotify IDs must be unique within the study")
    if bands["stats_extracted_at_utc"].nunique() != 1:
        raise ValueError("The study must use one Spotify capture timestamp")

    population_check = (
        bands[
            [
                "uk_population_rank",
                "fua_code",
                "city",
                "population_year",
                "population",
            ]
        ]
        .drop_duplicates()
        .sort_values("uk_population_rank")
        .reset_index(drop=True)
    )
    expected_population = (
        universe.head(city_count)[
            [
                "uk_population_rank",
                "fua_code",
                "study_city_label",
                "population_year",
                "population",
            ]
        ]
        .rename(columns={"study_city_label": "city"})
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(
        population_check,
        expected_population,
        check_dtype=False,
    )

    rankings = build_primary_scene_depth_rankings(
        bands,
        metric="monthly_listeners",
        expected_cities=city_count,
        bands_per_city=10,
    )

    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    bands.to_csv(metrics_output_path, index=False)
    rankings.to_csv(rankings_output_path, index=False)
    report = {
        "schema_version": 1,
        "spotify_snapshot_id": snapshot_id,
        "source_metrics_path": str(
            source_metrics_path.relative_to(PROJECT_ROOT)
        ),
        "fua_universe_path": str(universe_path.relative_to(PROJECT_ROOT)),
        "city_count": city_count,
        "bands_per_city": 10,
        "band_rows": len(bands),
        "spotify_capture_timestamp": bands[
            "stats_extracted_at_utc"
        ].iloc[0],
        "metrics_output_path": str(
            metrics_output_path.relative_to(PROJECT_ROOT)
        ),
        "rankings_output_path": str(
            rankings_output_path.relative_to(PROJECT_ROOT)
        ),
        "raw_top_three": rankings.sort_values("raw_total_rank")
        .head(3)["city"]
        .tolist(),
        "normalized_top_three": rankings.sort_values("all_ten_rank")
        .head(3)["city"]
        .tolist(),
        "scene_depth_top_three": rankings.sort_values("top_excluded_rank")
        .head(3)["city"]
        .tolist(),
    }
    report_output_path.write_text(json.dumps(report, indent=2) + "\n")
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-metrics",
        type=Path,
        default=Path(
            "data/processed/top20_city_band_metrics_20260718T204000Z.csv"
        ),
    )
    parser.add_argument(
        "--universe",
        type=Path,
        default=Path("reference/uk_fua_top20_2021.csv"),
    )
    parser.add_argument(
        "--city-count",
        action="append",
        type=int,
        choices=(10, 20),
        help="Repeat to build selected study sizes; defaults to both 10 and 20.",
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    city_counts = args.city_count or [10, 20]
    for city_count in city_counts:
        outputs = build_fua_study_inputs(
            source_metrics_path=_project_path(args.source_metrics),
            universe_path=_project_path(args.universe),
            city_count=city_count,
            force=args.force,
        )
        for path in outputs:
            print(path)


if __name__ == "__main__":
    main(sys.argv[1:])
