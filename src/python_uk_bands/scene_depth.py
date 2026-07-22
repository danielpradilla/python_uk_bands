"""Isolated calculations for the expanded scene-depth experiment."""

from __future__ import annotations

import pandas as pd


def validate_scene_depth_dataset(
    bands: pd.DataFrame,
    *,
    expected_cities: int = 10,
    bands_per_city: int = 10,
) -> None:
    """Validate the fixed, balanced design used by the scene-depth test."""
    required_columns = {"band", "city", "population"}
    missing = sorted(required_columns.difference(bands.columns))
    if missing:
        raise ValueError(f"Scene-depth dataset is missing required columns: {missing}")
    if bands.empty:
        raise ValueError("Scene-depth dataset is empty")
    if bands["band"].duplicated().any():
        duplicates = bands.loc[bands["band"].duplicated(), "band"].tolist()
        raise ValueError(f"Scene-depth dataset contains duplicate bands: {duplicates}")
    required = bands.loc[:, sorted(required_columns)]
    if required.isna().any().any():
        null_columns = required.columns[required.isna().any()].tolist()
        raise ValueError(
            f"Scene-depth dataset has nulls in required columns: {null_columns}"
        )
    if not pd.api.types.is_numeric_dtype(bands["population"]):
        raise ValueError("Population must be numeric")
    if (bands["population"] <= 0).any():
        raise ValueError("Population values must be positive")
    inconsistent_populations = bands.groupby("city")["population"].nunique()
    if (inconsistent_populations > 1).any():
        cities = inconsistent_populations[inconsistent_populations > 1].index.tolist()
        raise ValueError(f"Cities have inconsistent population values: {cities}")
    if bands_per_city < 3:
        raise ValueError("Scene-depth analysis requires at least three bands per city")

    city_counts = bands.groupby("city").size()
    if len(city_counts) != expected_cities:
        raise ValueError(
            f"Expected {expected_cities} cities, found {len(city_counts)}"
        )
    if not (city_counts == bands_per_city).all():
        counts = ", ".join(f"{city}={count}" for city, count in city_counts.items())
        raise ValueError(
            f"Expected {bands_per_city} bands per city; observed {counts}"
        )


def build_primary_scene_depth_rankings(
    bands: pd.DataFrame,
    *,
    metric: str = "monthly_listeners",
    expected_cities: int = 10,
    bands_per_city: int = 10,
) -> pd.DataFrame:
    """Build the all-band primary result and largest-band scene-depth test."""

    validate_scene_depth_dataset(
        bands,
        expected_cities=expected_cities,
        bands_per_city=bands_per_city,
    )
    if metric not in bands.columns:
        raise ValueError(f"Unknown metric: {metric}")
    if not pd.api.types.is_numeric_dtype(bands[metric]):
        raise ValueError(f"Metric must be numeric: {metric}")
    if bands[metric].isna().any():
        raise ValueError(f"Metric contains null values: {metric}")
    if (bands[metric] < 0).any():
        raise ValueError(f"Metric cannot be negative: {metric}")

    rows: list[dict] = []
    for city, group in bands.groupby("city", sort=True):
        ordered = group.sort_values(
            [metric, "band"],
            ascending=[True, True],
        ).reset_index(drop=True)
        population = ordered["population"].iloc[0]
        all_ten_value = ordered[metric].sum()
        largest = ordered.iloc[-1]
        top_excluded_value = ordered.iloc[:-1][metric].sum()
        rows.append(
            {
                "city": city,
                "population": population,
                "input_bands": len(ordered),
                "top_excluded_retained_bands": len(ordered) - 1,
                "highest_excluded_bands": largest["band"],
                "all_ten_value": all_ten_value,
                "all_ten_ratio": all_ten_value / population,
                "top_excluded_value": top_excluded_value,
                "top_excluded_ratio": top_excluded_value / population,
                "top_band_concentration": (
                    largest[metric] / all_ten_value
                ),
                "metric": metric,
            }
        )

    rankings = pd.DataFrame(rows)
    rankings["raw_total_rank"] = (
        rankings["all_ten_value"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    rankings["all_ten_rank"] = (
        rankings["all_ten_ratio"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    rankings["top_excluded_rank"] = (
        rankings["top_excluded_ratio"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    return rankings.sort_values(
        ["all_ten_rank", "city"]
    ).reset_index(drop=True)


def build_scene_depth_rankings(
    bands: pd.DataFrame,
    *,
    metric: str = "monthly_listeners",
    trim_each_tail: int = 1,
    expected_cities: int = 10,
    bands_per_city: int = 10,
) -> pd.DataFrame:
    """Rank cities after symmetrically trimming each city's extreme bands.

    With the intended ten-band design and ``trim_each_tail=1``, the highest and
    lowest band are removed and the middle eight bands form the scene-depth
    score. The score is their trimmed mean divided by population. Because every
    city retains the same number of bands, this produces the same order as the
    population-normalized trimmed total.
    """
    validate_scene_depth_dataset(
        bands,
        expected_cities=expected_cities,
        bands_per_city=bands_per_city,
    )
    if metric not in bands.columns:
        raise ValueError(f"Unknown metric: {metric}")
    if not pd.api.types.is_numeric_dtype(bands[metric]):
        raise ValueError(f"Metric must be numeric: {metric}")
    if bands[metric].isna().any():
        raise ValueError(f"Metric contains null values: {metric}")
    if (bands[metric] < 0).any():
        raise ValueError(f"Metric cannot be negative: {metric}")
    if trim_each_tail < 1:
        raise ValueError("trim_each_tail must be at least 1")
    if bands_per_city <= trim_each_tail * 2:
        raise ValueError("Trimming would leave no bands in the scene-depth score")

    rows: list[dict] = []
    for city, group in bands.groupby("city", sort=True):
        ordered = group.sort_values(
            [metric, "band"],
            ascending=[True, True],
        ).reset_index(drop=True)
        retained = ordered.iloc[trim_each_tail : len(ordered) - trim_each_tail]
        low = ordered.iloc[:trim_each_tail]
        high = ordered.iloc[len(ordered) - trim_each_tail :]
        population = ordered["population"].iloc[0]
        trimmed_value = retained[metric].sum()
        trimmed_mean = retained[metric].mean()
        untrimmed_value = ordered[metric].sum()
        top_excluded_value = ordered.iloc[:-trim_each_tail][metric].sum()

        rows.append(
            {
                "city": city,
                "population": population,
                "input_bands": len(ordered),
                "retained_bands": len(retained),
                "trim_each_tail": trim_each_tail,
                "trim_fraction_each_tail": trim_each_tail / len(ordered),
                "lowest_excluded_bands": " | ".join(low["band"]),
                "highest_excluded_bands": " | ".join(
                    high.sort_values(
                        [metric, "band"],
                        ascending=[False, True],
                    )["band"]
                ),
                "retained_band_names": " | ".join(
                    retained.sort_values(
                        [metric, "band"],
                        ascending=[False, True],
                    )["band"]
                ),
                "untrimmed_value": untrimmed_value,
                "untrimmed_ratio": untrimmed_value / population,
                "top_excluded_value": top_excluded_value,
                "top_excluded_ratio": top_excluded_value / population,
                "trimmed_value": trimmed_value,
                "trimmed_mean": trimmed_mean,
                "population_normalized_trimmed_mean": (
                    trimmed_mean / population
                ),
                "scene_depth_ratio": trimmed_value / population,
                "top_band_concentration": ordered[metric].iloc[-1] / untrimmed_value,
                "metric": metric,
            }
        )

    rankings = pd.DataFrame(rows)
    rankings["untrimmed_rank"] = (
        rankings["untrimmed_ratio"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    rankings["top_excluded_rank"] = (
        rankings["top_excluded_ratio"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    rankings["rank"] = (
        rankings["population_normalized_trimmed_mean"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    rankings["rank_shift_after_trim"] = rankings["untrimmed_rank"] - rankings["rank"]
    rankings["symmetric_vs_top_only_rank_shift"] = (
        rankings["top_excluded_rank"] - rankings["rank"]
    )
    return rankings.sort_values(["rank", "city"]).reset_index(drop=True)
