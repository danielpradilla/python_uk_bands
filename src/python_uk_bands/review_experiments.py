"""Shared calculations and charts for the study-review follow-up experiments."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from .config import FINAL_STUDY_BAND_METRICS_PATH
from .visuals import HOUSE, apply_chart_style


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    *,
    label: str,
) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing columns: {sorted(missing)}")


def rank_city_scores(
    frame: pd.DataFrame,
    *,
    specification: str,
    family: str,
    score_column: str,
    city_column: str = "study_city_label",
    higher_is_better: bool = True,
) -> pd.DataFrame:
    """Return deterministic within-specification ranks for one-row-per-city data."""

    _require_columns(
        frame,
        {city_column, score_column},
        label="score frame",
    )
    if frame[city_column].duplicated().any():
        raise ValueError("Score frame must contain one row per city")

    ranked = frame[[city_column, score_column]].copy()
    ranked[score_column] = pd.to_numeric(ranked[score_column], errors="raise")
    if ranked[score_column].isna().any() or not np.isfinite(
        ranked[score_column]
    ).all():
        raise ValueError("Scores must be finite and non-missing")
    ranked = ranked.rename(
        columns={city_column: "study_city_label", score_column: "score"}
    )
    ranked = ranked.sort_values(
        ["score", "study_city_label"],
        ascending=[not higher_is_better, True],
    ).reset_index(drop=True)
    ranked["rank"] = (
        ranked["score"]
        .rank(method="min", ascending=not higher_is_better)
        .astype(int)
    )
    ranked["specification"] = specification
    ranked["family"] = family
    ranked["eligible_cities"] = len(ranked)
    return ranked[
        [
            "specification",
            "family",
            "study_city_label",
            "score",
            "rank",
            "eligible_cities",
        ]
    ]


def summarize_rank_stability(
    ranked: pd.DataFrame,
    *,
    top_n: int = 5,
) -> pd.DataFrame:
    """Summarize each city's observed rank range across included specifications."""

    _require_columns(
        ranked,
        {"specification", "study_city_label", "rank"},
        label="ranked specifications",
    )
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if ranked.duplicated(["specification", "study_city_label"]).any():
        raise ValueError("Each specification may rank a city only once")

    frame = ranked.copy()
    frame["rank"] = pd.to_numeric(frame["rank"], errors="raise")
    frame["top_finish"] = frame["rank"].le(top_n)
    summary = (
        frame.groupby("study_city_label", as_index=False)
        .agg(
            specifications=("specification", "nunique"),
            best_rank=("rank", "min"),
            median_rank=("rank", "median"),
            worst_rank=("rank", "max"),
            rank_q1=("rank", lambda values: values.quantile(0.25)),
            rank_q3=("rank", lambda values: values.quantile(0.75)),
            top_finishes=("top_finish", "sum"),
        )
    )
    summary["rank_iqr"] = summary["rank_q3"] - summary["rank_q1"]
    summary["rank_range"] = summary["worst_rank"] - summary["best_rank"]
    summary["top_finish_share"] = (
        summary["top_finishes"] / summary["specifications"]
    )
    return summary.sort_values(
        ["top_finish_share", "median_rank", "study_city_label"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def summarize_scene_depth(
    bands: pd.DataFrame,
    *,
    group_column: str = "study_city_label",
    band_column: str = "returned_spotify_id",
    value_column: str = "followers",
    threshold: float = 100_000,
) -> pd.DataFrame:
    """Calculate concentration and effective-band measures for each city."""

    _require_columns(
        bands,
        {group_column, band_column, value_column},
        label="band frame",
    )
    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    if bands.duplicated([group_column, band_column]).any():
        raise ValueError("Band identities must be unique within each city")

    frame = bands[[group_column, band_column, value_column]].copy()
    frame[value_column] = pd.to_numeric(frame[value_column], errors="raise")
    if frame[value_column].isna().any() or not np.isfinite(
        frame[value_column]
    ).all():
        raise ValueError("Band values must be finite and non-missing")
    if frame[value_column].lt(0).any():
        raise ValueError("Band values must be non-negative")

    rows: list[dict[str, float | int | str]] = []
    for city, city_bands in frame.groupby(group_column, sort=True):
        values = np.sort(city_bands[value_column].to_numpy(dtype=float))[::-1]
        total = float(values.sum())
        shares = values / total if total > 0 else np.zeros_like(values)
        hhi = float(np.square(shares).sum()) if total > 0 else np.nan
        rows.append(
            {
                "study_city_label": str(city),
                "band_count": int(city_bands[band_column].nunique()),
                "audience_total": total,
                "audience_median": float(np.median(values)),
                "largest_band_audience": float(values[0]),
                "largest_band_share": float(shares[0]) if total > 0 else np.nan,
                "top_three_share": (
                    float(shares[:3].sum()) if total > 0 else np.nan
                ),
                "herfindahl_index": hhi,
                "effective_band_count": 1.0 / hhi if hhi > 0 else np.nan,
                "bands_above_threshold": int((values >= threshold).sum()),
                "audience_threshold": float(threshold),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["effective_band_count", "audience_total", "study_city_label"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def extract_frozen_formation_years(
    artist_capture_paths: Iterable[Path],
    resolution_path: Path,
) -> pd.DataFrame:
    """Extract formation years from the repository's frozen MusicBrainz data."""

    rows: list[dict[str, object]] = []
    for capture_path in artist_capture_paths:
        payload = json.loads(capture_path.read_text())
        for record in payload.get("records", []):
            begin = str(record.get("life_span_begin") or "")
            year = begin[:4]
            if year.isdigit():
                rows.append(
                    {
                        "musicbrainz_id": str(record.get("musicbrainz_id") or ""),
                        # These broad search captures are authoritative by ID,
                        # but exact-name fallback could select a namesake.
                        "band_name_key": "",
                        "formed_year": int(year),
                        "formation_year_source": str(capture_path),
                    }
                )

    resolution = json.loads(resolution_path.read_text()).get("musicbrainz", {})
    for band_name, record in resolution.items():
        details = record.get("details", {}) if isinstance(record, dict) else {}
        begin = str((details.get("life-span") or {}).get("begin") or "")
        musicbrainz_id = str(details.get("id") or "")
        if not begin[:4].isdigit() and isinstance(record, dict):
            search_results = record.get("search", {}).get("artists", [])
            exact = next(
                (
                    result
                    for result in search_results
                    if str(result.get("name") or "").casefold()
                    == str(band_name).casefold()
                ),
                None,
            )
            if exact is not None:
                begin = str((exact.get("life-span") or {}).get("begin") or "")
                musicbrainz_id = str(exact.get("id") or "")
        if begin[:4].isdigit():
            rows.append(
                {
                    "musicbrainz_id": musicbrainz_id,
                    "band_name_key": str(band_name).casefold(),
                    "formed_year": int(begin[:4]),
                    "formation_year_source": str(resolution_path),
                }
            )

    lookup = pd.DataFrame(rows)
    if lookup.empty:
        return pd.DataFrame(
            columns=[
                "musicbrainz_id",
                "band_name_key",
                "formed_year",
                "formation_year_source",
            ]
        )
    lookup = lookup.sort_values(
        ["musicbrainz_id", "band_name_key", "formation_year_source"]
    ).drop_duplicates(["musicbrainz_id", "band_name_key", "formed_year"])
    return lookup.reset_index(drop=True)


def attach_formation_years(
    bands: pd.DataFrame,
    lookup: pd.DataFrame,
    *,
    band_name_column: str = "band_name",
    musicbrainz_column: str = "musicbrainz_id",
) -> pd.DataFrame:
    """Attach formation years, preferring MusicBrainz IDs over exact names."""

    _require_columns(
        bands,
        {band_name_column, musicbrainz_column},
        label="band frame",
    )
    _require_columns(
        lookup,
        {
            "musicbrainz_id",
            "band_name_key",
            "formed_year",
            "formation_year_source",
        },
        label="formation-year lookup",
    )

    result = bands.copy()
    result["band_name_key"] = result[band_name_column].astype(str).str.casefold()
    by_id = (
        lookup.loc[lookup["musicbrainz_id"].ne("")]
        .sort_values("formation_year_source")
        .drop_duplicates("musicbrainz_id")
        .set_index("musicbrainz_id")
    )
    by_name = (
        lookup.loc[lookup["band_name_key"].ne("")]
        .sort_values("formation_year_source")
        .drop_duplicates("band_name_key")
        .set_index("band_name_key")
    )
    result["formed_year"] = result[musicbrainz_column].map(
        by_id["formed_year"]
    )
    result["formation_year_source"] = result[musicbrainz_column].map(
        by_id["formation_year_source"]
    )
    missing = result["formed_year"].isna()
    result.loc[missing, "formed_year"] = result.loc[
        missing, "band_name_key"
    ].map(by_name["formed_year"])
    result.loc[missing, "formation_year_source"] = result.loc[
        missing, "band_name_key"
    ].map(by_name["formation_year_source"])
    result["formed_year"] = result["formed_year"].astype("Int64")
    result["formation_year_source"] = result[
        "formation_year_source"
    ].fillna("")
    return result.drop(columns="band_name_key")


def summarize_formation_year_coverage(
    bands: pd.DataFrame,
    *,
    city_column: str = "study_city_label",
) -> pd.DataFrame:
    """Report formation-year completeness by city."""

    _require_columns(
        bands,
        {city_column, "formed_year"},
        label="formation-year band frame",
    )
    frame = bands.copy()
    frame["year_known"] = frame["formed_year"].notna()
    coverage = (
        frame.groupby(city_column, as_index=False)
        .agg(
            selected_bands=("year_known", "size"),
            bands_with_year=("year_known", "sum"),
        )
        .rename(columns={city_column: "study_city_label"})
    )
    coverage["formation_year_coverage"] = (
        coverage["bands_with_year"] / coverage["selected_bands"]
    )
    return coverage.sort_values(
        ["formation_year_coverage", "study_city_label"],
        ascending=[False, True],
    ).reset_index(drop=True)


def build_specification_multiverse(
    project_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the review's rank multiverse from the frozen experiment inputs."""

    from .output_share import build_output_share_metrics

    ranked_parts: list[pd.DataFrame] = []
    catalogue_rows: list[dict[str, object]] = []

    def add_specification(
        frame: pd.DataFrame,
        *,
        specification: str,
        family: str,
        score_column: str,
        universe: str,
        mapping: str,
        metric: str,
        scoring: str,
    ) -> None:
        ranked = rank_city_scores(
            frame,
            specification=specification,
            family=family,
            score_column=score_column,
        )
        ranked_parts.append(ranked)
        catalogue_rows.append(
            {
                "specification": specification,
                "family": family,
                "universe": universe,
                "mapping": mapping,
                "metric": metric,
                "scoring": scoring,
                "eligible_cities": len(ranked),
            }
        )

    for city_count in [10, 20]:
        path = FINAL_STUDY_BAND_METRICS_PATH
        if city_count == 20:
            path = (
                project_root
                / "data/processed/fua_top20_band_metrics_20260718T204000Z.csv"
            )
        bands = pd.read_csv(path, keep_default_na=False)
        grouped = (
            bands.groupby("study_city_label", as_index=False)
            .agg(
                population=("population", "first"),
                monthly_listeners_total=("monthly_listeners", "sum"),
                followers_total=("followers", "sum"),
                largest_monthly_listeners=("monthly_listeners", "max"),
                largest_followers=("followers", "max"),
            )
        )
        for metric, total_column, largest_column in [
            ("monthly listeners", "monthly_listeners_total", "largest_monthly_listeners"),
            ("followers", "followers_total", "largest_followers"),
        ]:
            metric_key = metric.replace(" ", "_")
            grouped["raw_score"] = grouped[total_column]
            grouped["per_million_score"] = (
                grouped[total_column] / grouped["population"] * 1_000_000
            )
            grouped["largest_excluded_per_million_score"] = (
                (grouped[total_column] - grouped[largest_column])
                / grouped["population"]
                * 1_000_000
            )
            for scoring, score_column in [
                ("raw total", "raw_score"),
                ("per million residents", "per_million_score"),
                (
                    "largest band excluded per million residents",
                    "largest_excluded_per_million_score",
                ),
            ]:
                scoring_key = (
                    scoring.replace(" ", "_").replace("-", "_")
                )
                add_specification(
                    grouped,
                    specification=(
                        f"balanced_{city_count}_{metric_key}_{scoring_key}"
                    ),
                    family="balanced city-first",
                    score_column=score_column,
                    universe=f"balanced top-{city_count} FUAs",
                    mapping="catalogue-assigned FUA",
                    metric=metric,
                    scoring=scoring,
                )

    population = pd.read_csv(
        project_root
        / "data/processed/uk_fua_population_2024_20260830T221015Z.csv",
        keep_default_na=False,
    )
    for selected_count in [100, 200, 1000]:
        bands = pd.read_csv(
            project_root
            / "data/processed"
            / (
                f"popularity_first_top{selected_count}_"
                "20260718T204522Z_bands.csv"
            ),
            keep_default_na=False,
        )
        mapping = pd.read_csv(
            project_root
            / "data/interim"
            / (
                f"popularity_first_top{selected_count}_"
                "20260718T204522Z_fua_mapping_audit.csv"
            ),
            keep_default_na=False,
        )
        for mapping_label, tiers in [
            ("strict", {"strict"}),
            ("reviewed extended", {"strict", "reviewed_extended"}),
        ]:
            metrics, _ = build_output_share_metrics(
                bands,
                mapping,
                population,
                included_tiers=tiers,
            )
            for metric, score_column in [
                ("selected-band output quotient", "band_output_quotient"),
                (
                    "monthly-listener output quotient",
                    "monthly_listener_output_quotient",
                ),
                ("follower output quotient", "follower_output_quotient"),
            ]:
                mapping_key = mapping_label.replace(" ", "_")
                metric_key = (
                    metric.replace(" ", "_").replace("-", "_")
                )
                add_specification(
                    metrics,
                    specification=(
                        f"popularity_{selected_count}_{mapping_key}_{metric_key}"
                    ),
                    family="popularity-first output quotient",
                    score_column=score_column,
                    universe=f"popularity-first top {selected_count}",
                    mapping=mapping_label,
                    metric=metric,
                    scoring="output share / population share",
                )

    model_dir = (
        project_root
        / "artifacts/experiments/top1000_scaling_models/20260718T204522Z"
    )
    negative_binomial = pd.read_csv(
        model_dir / "negative_binomial_fua_results.csv",
        keep_default_na=False,
    )
    add_specification(
        negative_binomial,
        specification="top1000_negative_binomial_count_residual",
        family="expected-output residual",
        score_column="pearson_residual",
        universe="popularity-first top 1,000",
        mapping="reviewed extended",
        metric="mapped-band count",
        scoring="negative-binomial Pearson residual",
    )
    loglog = pd.read_csv(
        model_dir / "loglog_follower_fua_results.csv",
        keep_default_na=False,
    )
    loglog["model_included"] = loglog["model_included"].astype(str).str.lower().eq(
        "true"
    )
    add_specification(
        loglog.loc[loglog["model_included"]],
        specification="top1000_loglog_follower_residual",
        family="expected-output residual",
        score_column="log_residual",
        universe="popularity-first top 1,000 positive-output FUAs",
        mapping="reviewed extended",
        metric="followers",
        scoring="log-log residual",
    )

    ranked = pd.concat(ranked_parts, ignore_index=True)
    catalogue = pd.DataFrame(catalogue_rows)
    stability = summarize_rank_stability(ranked, top_n=5)
    return ranked, stability, catalogue


def build_top1000_scene_depth(
    project_root: Path,
    *,
    follower_threshold: float = 100_000,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    """Build effective-band and concentration metrics for mapped top-1,000 bands."""

    from .output_share import build_output_share_metrics

    bands = pd.read_csv(
        project_root
        / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv",
        keep_default_na=False,
    )
    mapping = pd.read_csv(
        project_root
        / "data/interim/popularity_first_top1000_20260718T204522Z_fua_mapping_audit.csv",
        keep_default_na=False,
    )
    population = pd.read_csv(
        project_root
        / "data/processed/uk_fua_population_2024_20260830T221015Z.csv",
        keep_default_na=False,
    )
    mapped = bands[
        ["returned_spotify_id", "spotify_name", "followers", "monthly_listeners"]
    ].merge(
        mapping[
            ["returned_spotify_id", "mapping_tier", "fua_code"]
        ],
        on="returned_spotify_id",
        how="left",
        validate="one_to_one",
    )
    mapped = mapped.loc[
        mapped["mapping_tier"].isin({"strict", "reviewed_extended"})
    ].merge(
        population[["fua_code", "study_city_label", "population"]],
        on="fua_code",
        how="left",
        validate="many_to_one",
    )
    if mapped["study_city_label"].isna().any():
        raise ValueError("Every included band must map to a population FUA")

    depth = summarize_scene_depth(
        mapped,
        group_column="study_city_label",
        band_column="returned_spotify_id",
        value_column="followers",
        threshold=follower_threshold,
    )
    output_metrics, coverage = build_output_share_metrics(
        bands,
        mapping,
        population,
        included_tiers={"strict", "reviewed_extended"},
    )
    depth = depth.merge(
        output_metrics[
            [
                "study_city_label",
                "fua_code",
                "population",
                "followers_total",
                "follower_output_quotient",
                "largest_band_by_followers",
            ]
        ],
        on="study_city_label",
        how="left",
        validate="one_to_one",
    )
    depth = depth.sort_values(
        ["effective_band_count", "follower_output_quotient", "study_city_label"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return depth, mapped, coverage


def build_top20_generation_analysis(
    project_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Build the partial formation-decade analysis from frozen MusicBrainz data."""

    bands = pd.read_csv(
        project_root
        / "data/processed/fua_top20_band_metrics_20260718T204000Z.csv",
        keep_default_na=False,
    )
    artist_captures = sorted(
        (project_root / "data/raw/musicbrainz").glob("artists_*_latest.json")
    )
    resolution_path = (
        project_root
        / "data/raw/musicbrainz/top20_band_resolution_20260718T202426Z.json"
    )
    lookup = extract_frozen_formation_years(artist_captures, resolution_path)
    bands = attach_formation_years(bands, lookup)
    known_years = bands["formed_year"].dropna().astype(int)
    if not known_years.between(1900, 2026).all():
        raise ValueError("Formation years must be plausible four-digit years")
    coverage = summarize_formation_year_coverage(bands)
    known = bands.dropna(subset=["formed_year"]).copy()
    known["formation_decade"] = (known["formed_year"].astype(int) // 10) * 10
    decade_summary = (
        known.groupby(["study_city_label", "formation_decade"], as_index=False)
        .agg(
            bands_with_known_year=("band_name", "nunique"),
            followers=("followers", "sum"),
            monthly_listeners=("monthly_listeners", "sum"),
        )
    )
    overall = {
        "selected_bands": int(len(bands)),
        "bands_with_year": int(bands["formed_year"].notna().sum()),
        "formation_year_coverage": float(bands["formed_year"].notna().mean()),
        "cities": int(bands["study_city_label"].nunique()),
        "cities_with_complete_years": int(
            coverage["formation_year_coverage"].eq(1).sum()
        ),
        "cities_with_no_years": int(
            coverage["formation_year_coverage"].eq(0).sum()
        ),
        "earliest_observed_year": int(known_years.min()),
        "latest_observed_year": int(known_years.max()),
        "formation_year_sources": [
            str(path.relative_to(project_root))
            for path in [*artist_captures, resolution_path]
        ],
    }
    return bands, coverage, decade_summary, overall


def _save_figure(fig: plt.Figure, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=HOUSE["page"])
    plt.close(fig)
    return output_path


def plot_rank_intervals(
    stability: pd.DataFrame,
    *,
    output_path: Path,
    max_cities: int = 15,
) -> Path:
    """Plot best, median and worst observed ranks for the most stable leaders."""

    _require_columns(
        stability,
        {
            "study_city_label",
            "best_rank",
            "median_rank",
            "worst_rank",
            "top_finish_share",
        },
        label="rank-stability frame",
    )
    apply_chart_style()
    shown = stability.head(max_cities).sort_values(
        ["median_rank", "study_city_label"], ascending=[False, False]
    )
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    y = np.arange(len(shown))
    ax.hlines(
        y,
        shown["best_rank"],
        shown["worst_rank"],
        color=HOUSE["gray_blue"],
        linewidth=3.0,
    )
    ax.scatter(
        shown["median_rank"],
        y,
        s=58,
        facecolor=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
        zorder=3,
    )
    ax.set_yticks(y, shown["study_city_label"])
    ax.set_xlabel("Rank across included specifications · lower is better")
    ax.set_title(
        "Observed rank intervals across defensible specifications",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Line = best to worst observed rank · dot = median rank",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_xlim(left=0.5)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_top_finish_share(
    stability: pd.DataFrame,
    *,
    output_path: Path,
    top_n: int = 5,
    max_cities: int = 15,
) -> Path:
    """Plot the share of included specifications in which each city is top-N."""

    apply_chart_style()
    shown = stability.head(max_cities).sort_values(
        ["top_finish_share", "study_city_label"], ascending=[True, False]
    )
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    bars = ax.barh(
        shown["study_city_label"],
        shown["top_finish_share"],
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
    )
    ax.bar_label(
        bars,
        labels=[f"{value:.0%}" for value in shown["top_finish_share"]],
        padding=4,
        color=HOUSE["ink_soft"],
        fontsize=9,
    )
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.set_xlabel(f"Share of applicable specifications with a top-{top_n} finish")
    ax.set_title(
        f"Frequency of a top-{top_n} finish",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Denominators vary because balanced catalogues cover fewer FUAs",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_depth_vs_output(
    depth: pd.DataFrame,
    *,
    output_path: Path,
    label_cities: Sequence[str] = (),
) -> Path:
    """Plot effective band count against follower output quotient."""

    _require_columns(
        depth,
        {
            "study_city_label",
            "effective_band_count",
            "follower_output_quotient",
            "largest_band_share",
        },
        label="scene-depth frame",
    )
    apply_chart_style()
    shown = depth.loc[
        depth["effective_band_count"].notna()
        & depth["follower_output_quotient"].gt(0)
    ].copy()
    concentrated = shown["largest_band_share"].ge(0.5)
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    ax.scatter(
        shown.loc[~concentrated, "effective_band_count"],
        shown.loc[~concentrated, "follower_output_quotient"],
        s=56,
        facecolor=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
        label="Largest band below 50%",
    )
    ax.scatter(
        shown.loc[concentrated, "effective_band_count"],
        shown.loc[concentrated, "follower_output_quotient"],
        s=56,
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.2,
        label="Largest band at least 50%",
    )
    labels = set(label_cities)
    label_offsets = {
        "Bath and North East Somerset": (8, -14),
        "Liverpool": (8, -13),
        "Oxford": (-42, 8),
        "Sheffield": (8, 8),
    }
    for row in shown.itertuples():
        if row.study_city_label in labels:
            offset = label_offsets.get(row.study_city_label, (5, 5))
            ax.annotate(
                row.study_city_label,
                (row.effective_band_count, row.follower_output_quotient),
                xytext=offset,
                textcoords="offset points",
                fontsize=8.5,
                color=HOUSE["ink_soft"],
            )
    ax.axhline(1, color=HOUSE["secondary"], linewidth=1.0, linestyle=(0, (4, 4)))
    ax.set_yscale("log")
    ax.set_xlabel("Effective number of equally followed mapped bands")
    ax.set_ylabel("Follower output quotient · log scale")
    ax.set_title(
        "Scene breadth and population-adjusted follower output",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Top-1,000 popularity-first catalogue · reviewed-extended FUA mapping",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, which="major")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_effective_band_ranking(
    depth: pd.DataFrame,
    *,
    output_path: Path,
    max_cities: int = 20,
) -> Path:
    """Plot the cities with the largest effective-band counts."""

    apply_chart_style()
    shown = depth.dropna(subset=["effective_band_count"]).head(max_cities)
    shown = shown.sort_values("effective_band_count", ascending=True)
    fig, ax = plt.subplots(figsize=(10.8, 7.4))
    bars = ax.barh(
        shown["study_city_label"],
        shown["effective_band_count"],
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
    )
    ax.bar_label(
        bars,
        labels=[f"{value:.1f}" for value in shown["effective_band_count"]],
        padding=4,
        fontsize=8.8,
        color=HOUSE["ink_soft"],
    )
    ax.set_xlabel("Effective number of equally followed mapped bands")
    ax.set_title(
        "Largest effective-band counts",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Inverse Herfindahl index using mapped-band follower shares",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_formation_year_coverage(
    coverage: pd.DataFrame,
    *,
    output_path: Path,
) -> Path:
    """Plot formation-year completeness across the balanced top-20 catalogue."""

    apply_chart_style()
    shown = coverage.sort_values(
        ["formation_year_coverage", "study_city_label"], ascending=[True, False]
    )
    fig, ax = plt.subplots(figsize=(10.8, 7.6))
    bars = ax.barh(
        shown["study_city_label"],
        shown["formation_year_coverage"],
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
    )
    ax.bar_label(
        bars,
        labels=[
            f"{known}/{selected}"
            for known, selected in zip(
                shown["bands_with_year"], shown["selected_bands"], strict=True
            )
        ],
        padding=4,
        fontsize=8.8,
        color=HOUSE["ink_soft"],
    )
    ax.set_xlim(0, 1.12)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.set_xlabel("Share of selected bands with a frozen formation year")
    ax.set_title(
        "Formation-year coverage by FUA",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Balanced top-20 catalogue · labels show known years / selected bands",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_decade_heatmap(
    bands: pd.DataFrame,
    coverage: pd.DataFrame,
    *,
    output_path: Path,
) -> Path:
    """Plot observed formation-decade counts, leaving missing years explicit."""

    _require_columns(
        bands,
        {"study_city_label", "formed_year"},
        label="formation-year band frame",
    )
    known = bands.dropna(subset=["formed_year"]).copy()
    known["formation_decade"] = (known["formed_year"].astype(int) // 10) * 10
    minimum_decade = int(known["formation_decade"].min())
    maximum_decade = int(known["formation_decade"].max())
    decades = list(range(minimum_decade, maximum_decade + 10, 10))
    matrix = (
        known.groupby(["study_city_label", "formation_decade"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=decades, fill_value=0)
    )
    city_order = coverage.sort_values(
        ["formation_year_coverage", "study_city_label"],
        ascending=[False, True],
    )["study_city_label"]
    matrix = matrix.reindex(city_order, fill_value=0)

    apply_chart_style()
    cmap = LinearSegmentedColormap.from_list(
        "house_blue", [HOUSE["page"], HOUSE["blue_soft"], HOUSE["blue"]]
    )
    fig, ax = plt.subplots(figsize=(11.2, 8.0))
    image = ax.imshow(matrix.to_numpy(), aspect="auto", cmap=cmap, vmin=0)
    ax.set_xticks(np.arange(len(decades)), [f"{decade}s" for decade in decades])
    ax.set_yticks(np.arange(len(matrix)), matrix.index)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = int(matrix.iat[row, column])
            if value:
                ax.text(
                    column,
                    row,
                    str(value),
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    color=HOUSE["page"] if value >= 5 else HOUSE["ink_soft"],
                )
    ax.set_xlabel("Formation decade")
    ax.set_title(
        "Observed formation decades in the frozen MusicBrainz data",
        loc="left",
        pad=34,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.015,
        "Counts include known years only; blank cells are not evidence of no bands",
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.025)
    colorbar.set_label("Bands with known formation year")
    ax.tick_params(axis="x", rotation=0)
    ax.spines[:].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)
