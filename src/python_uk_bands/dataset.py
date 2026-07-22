"""Load and validate the saved shortlist analysis inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .analysis import validate_band_dataset
from .config import BUILT_UP_AREAS_PATH, SHORTLIST_METRICS_PATH, SHORTLIST_PATH


def load_shortlist_dataset(
    shortlist_path: Path = SHORTLIST_PATH,
    populations_path: Path = BUILT_UP_AREAS_PATH,
    metrics_path: Path = SHORTLIST_METRICS_PATH,
) -> pd.DataFrame:
    """Return one analysis row per shortlisted band."""
    shortlist = pd.read_csv(shortlist_path)
    populations = pd.read_csv(populations_path)
    spotify_metrics = pd.read_json(metrics_path)

    bands = (
        shortlist.merge(
            spotify_metrics,
            left_on="band_name",
            right_on="band",
            how="left",
            validate="one_to_one",
        )
        .merge(
            populations[["bua_name", "population", "population_year", "source"]],
            left_on="original_city_label",
            right_on="bua_name",
            how="left",
            validate="many_to_one",
        )
        .drop(columns=["bua_name"])
    )
    bands["stats_extracted_at"] = pd.to_datetime(bands["stats_extracted_at"])
    validate_band_dataset(bands)
    return bands


def validate_shortlist_shape(
    bands: pd.DataFrame,
    *,
    expected_cities: int = 10,
    bands_per_city: int = 5,
) -> None:
    """Validate the fixed 50-band exploratory design."""
    expected_rows = expected_cities * bands_per_city
    if len(bands) != expected_rows:
        raise ValueError(f"Expected {expected_rows} shortlist rows, found {len(bands)}")
    if bands["band_name"].nunique() != expected_rows:
        raise ValueError("Shortlist band names must be unique")
    if bands["spotify_id"].nunique() != expected_rows:
        raise ValueError("Spotify IDs must be unique")
    if not (bands["original_city_label"] == bands["city"]).all():
        raise ValueError("Shortlist and metric city labels disagree")

    city_counts = bands.groupby("city").size()
    if len(city_counts) != expected_cities or not (city_counts == bands_per_city).all():
        raise ValueError(
            f"Expected {bands_per_city} bands in each of {expected_cities} cities"
        )


def build_quality_summary(bands: pd.DataFrame) -> pd.DataFrame:
    """Return the compact integrity table shown in the final notebook."""
    return pd.DataFrame(
        {
            "check": [
                "Shortlist rows",
                "Unique bands",
                "Cities represented",
                "Missing Spotify IDs",
                "Missing populations",
                "Missing popularity metrics",
                "Duplicate Spotify IDs",
                "Snapshot dates",
            ],
            "result": [
                len(bands),
                bands["band_name"].nunique(),
                bands["city"].nunique(),
                int(bands["spotify_id"].isna().sum()),
                int(bands["population"].isna().sum()),
                int(bands[["followers", "monthly_listeners"]].isna().any(axis=1).sum()),
                int(bands["spotify_id"].duplicated().sum()),
                bands["stats_extracted_at"].dt.strftime("%Y-%m-%d").nunique(),
            ],
        }
    )


def build_match_review_queue(bands: pd.DataFrame) -> pd.DataFrame:
    """Surface non-exact matches and implausibly small matched accounts."""
    columns = [
        "band_name",
        "spotify_name",
        "match_quality",
        "followers",
        "monthly_listeners",
    ]
    needs_review = (bands["match_quality"] != "exact") | (bands["followers"] < 100)
    return bands.loc[needs_review, columns].sort_values("followers").reset_index(drop=True)
