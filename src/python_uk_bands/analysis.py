"""Reusable calculations for the UK bands city analysis."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd


REQUIRED_BAND_COLUMNS: tuple[str, ...] = (
    "band",
    "city",
    "followers",
    "monthly_listeners",
    "population",
)


def validate_band_dataset(bands: pd.DataFrame) -> None:
    """Raise a useful error when the band-level analysis input is malformed."""
    missing = sorted(set(REQUIRED_BAND_COLUMNS).difference(bands.columns))
    if missing:
        raise ValueError(f"Band dataset is missing required columns: {missing}")
    if bands.empty:
        raise ValueError("Band dataset is empty")
    if bands["band"].duplicated().any():
        duplicates = bands.loc[bands["band"].duplicated(), "band"].tolist()
        raise ValueError(f"Band dataset contains duplicate bands: {duplicates}")
    required = bands.loc[:, REQUIRED_BAND_COLUMNS]
    if required.isna().any().any():
        null_columns = required.columns[required.isna().any()].tolist()
        raise ValueError(f"Band dataset has nulls in required columns: {null_columns}")
    if (bands["population"] <= 0).any():
        raise ValueError("Population values must be positive")
    if (bands[["followers", "monthly_listeners"]] < 0).any().any():
        raise ValueError("Popularity metrics cannot be negative")
    inconsistent_populations = bands.groupby("city")["population"].nunique()
    if (inconsistent_populations > 1).any():
        cities = inconsistent_populations[inconsistent_populations > 1].index.tolist()
        raise ValueError(f"Cities have inconsistent population values: {cities}")


def _validate_metric(bands: pd.DataFrame, metric: str) -> None:
    if metric not in bands.columns:
        raise ValueError(f"Unknown metric: {metric}")
    if not pd.api.types.is_numeric_dtype(bands[metric]):
        raise ValueError(f"Metric must be numeric: {metric}")


def build_city_rankings(
    bands: pd.DataFrame,
    *,
    metric: str,
    top_n: int = 3,
) -> pd.DataFrame:
    """Aggregate one band-level popularity metric into comparable city scores.

    The output includes three views used throughout the project: the sum across
    all eligible bands, the sum of each city's top N bands, and its leading band.
    Each view is normalized per million residents.
    """
    validate_band_dataset(bands)
    _validate_metric(bands, metric)
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    ordered = bands.sort_values(["city", metric, "band"], ascending=[True, False, True])
    city_totals = ordered.groupby("city", as_index=False).agg(
        population=("population", "first"),
        eligible_bands=("band", "size"),
        total_value=(metric, "sum"),
        top_value=(metric, "first"),
        top_band=("band", "first"),
    )
    top_n_totals = (
        ordered.groupby("city", group_keys=False)
        .head(top_n)
        .groupby("city", as_index=False)[metric]
        .sum()
        .rename(columns={metric: "top_n_value"})
    )
    rankings = city_totals.merge(top_n_totals, on="city", validate="one_to_one")
    rankings["total_ratio"] = rankings["total_value"] / rankings["population"]
    rankings["top_n_ratio"] = rankings["top_n_value"] / rankings["population"]
    rankings["top_band_ratio"] = rankings["top_value"] / rankings["population"]

    rankings["rank"] = rankings["top_n_ratio"].rank(method="min", ascending=False).astype(int)
    rankings["metric"] = metric
    rankings["top_n"] = top_n
    return rankings.sort_values(["rank", "city"]).reset_index(drop=True)


def build_threshold_sensitivity(
    bands: pd.DataFrame,
    *,
    thresholds: Iterable[int],
    metric: str = "monthly_listeners",
    top_n: int = 3,
) -> pd.DataFrame:
    """Recalculate city rankings across follower eligibility thresholds."""
    validate_band_dataset(bands)
    normalized_thresholds: Sequence[int] = sorted({int(value) for value in thresholds})
    if any(value < 0 for value in normalized_thresholds):
        raise ValueError("Follower thresholds cannot be negative")

    frames: list[pd.DataFrame] = []
    for threshold in normalized_thresholds:
        eligible = bands.loc[bands["followers"] >= threshold].copy()
        if eligible.empty:
            continue
        ranking = build_city_rankings(eligible, metric=metric, top_n=top_n)
        ranking.insert(0, "follower_threshold", int(threshold))
        frames.append(ranking)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
