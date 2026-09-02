"""Share-of-output calculations and charting for UK FUA experiments."""

from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

from .visuals import HOUSE, add_superposed_bubble_legend, apply_chart_style


INCLUDED_MAPPING_TIERS = {"strict", "reviewed_extended"}


def build_output_share_metrics(
    bands: pd.DataFrame,
    mapping_audit: pd.DataFrame,
    population: pd.DataFrame,
    *,
    included_tiers: set[str],
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Compare each FUA's output shares with its share of UK FUA population.

    Music-output denominators include the complete selected catalogue, while
    the population denominator includes every FUA in the supplied population
    universe. Mapped shares can therefore sum to less than one; unresolved or
    excluded bands are not silently redistributed across mapped places.
    """

    required_bands = {
        "returned_spotify_id",
        "spotify_name",
        "monthly_listeners",
        "followers",
    }
    required_mapping = {
        "returned_spotify_id",
        "mapping_tier",
        "fua_code",
    }
    required_population = {
        "fua_code",
        "official_fua_name",
        "study_city_label",
        "population_year",
        "population",
    }
    for frame, required, label in [
        (bands, required_bands, "bands"),
        (mapping_audit, required_mapping, "mapping audit"),
        (population, required_population, "population"),
    ]:
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} is missing columns: {sorted(missing)}")

    if not included_tiers or not included_tiers.issubset(
        INCLUDED_MAPPING_TIERS
    ):
        raise ValueError(
            "included_tiers must be a non-empty subset of "
            f"{sorted(INCLUDED_MAPPING_TIERS)}"
        )
    if bands["returned_spotify_id"].duplicated().any():
        raise ValueError("Bands must contain unique returned Spotify IDs")
    if mapping_audit["returned_spotify_id"].duplicated().any():
        raise ValueError("Mapping audit must contain unique returned Spotify IDs")
    if population["fua_code"].duplicated().any():
        raise ValueError("Population must contain unique FUA codes")

    band_ids = set(bands["returned_spotify_id"])
    audit_ids = set(mapping_audit["returned_spotify_id"])
    if band_ids != audit_ids:
        raise ValueError(
            "Mapping audit must cover the selected band universe exactly"
        )

    selected = bands[
        [
            "returned_spotify_id",
            "spotify_name",
            "monthly_listeners",
            "followers",
        ]
    ].copy()
    selected["monthly_listeners"] = pd.to_numeric(
        selected["monthly_listeners"], errors="raise"
    )
    selected["followers"] = pd.to_numeric(
        selected["followers"], errors="raise"
    )
    if (selected[["monthly_listeners", "followers"]] < 0).any().any():
        raise ValueError("Audience metrics must be non-negative")

    population_frame = population[
        [
            "fua_code",
            "official_fua_name",
            "study_city_label",
            "population_year",
            "population",
        ]
    ].copy()
    population_frame["population"] = pd.to_numeric(
        population_frame["population"], errors="raise"
    )
    if (population_frame["population"] <= 0).any():
        raise ValueError("FUA populations must be positive")

    selected = selected.merge(
        mapping_audit[
            ["returned_spotify_id", "mapping_tier", "fua_code"]
        ],
        on="returned_spotify_id",
        how="left",
        validate="one_to_one",
    )
    mapped = selected.loc[
        selected["mapping_tier"].isin(included_tiers)
    ].copy()
    if mapped["fua_code"].eq("").any() or mapped["fua_code"].isna().any():
        raise ValueError("Included mapping tiers require a FUA code")

    unknown_codes = sorted(
        set(mapped["fua_code"]).difference(population_frame["fua_code"])
    )
    if unknown_codes:
        raise ValueError(
            f"Mapped FUA codes are missing from population: {unknown_codes}"
        )

    grouped = (
        mapped.groupby("fua_code", as_index=False)
        .agg(
            band_count=("returned_spotify_id", "nunique"),
            monthly_listeners_total=("monthly_listeners", "sum"),
            followers_total=("followers", "sum"),
        )
    )
    largest_bands = (
        mapped.sort_values(
            ["followers", "spotify_name"], ascending=[False, True]
        )
        .drop_duplicates("fua_code")
        [["fua_code", "spotify_name", "followers"]]
        .rename(
            columns={
                "spotify_name": "largest_band_by_followers",
                "followers": "largest_band_followers",
            }
        )
    )
    result = population_frame.merge(
        grouped, on="fua_code", how="left", validate="one_to_one"
    ).merge(
        largest_bands, on="fua_code", how="left", validate="one_to_one"
    )
    numeric_output_columns = [
        "band_count",
        "monthly_listeners_total",
        "followers_total",
        "largest_band_followers",
    ]
    result[numeric_output_columns] = result[numeric_output_columns].fillna(0)
    result["band_count"] = result["band_count"].astype(int)
    result["largest_band_by_followers"] = result[
        "largest_band_by_followers"
    ].fillna("")

    selected_band_count = selected["returned_spotify_id"].nunique()
    selected_listener_total = selected["monthly_listeners"].sum()
    selected_follower_total = selected["followers"].sum()
    population_total = population_frame["population"].sum()
    if selected_listener_total <= 0 or selected_follower_total <= 0:
        raise ValueError("Selected audience totals must be positive")

    result["population_share"] = result["population"] / population_total
    result["band_share"] = result["band_count"] / selected_band_count
    result["monthly_listener_share"] = (
        result["monthly_listeners_total"] / selected_listener_total
    )
    result["follower_share"] = (
        result["followers_total"] / selected_follower_total
    )
    result["band_output_quotient"] = (
        result["band_share"] / result["population_share"]
    )
    result["monthly_listener_output_quotient"] = (
        result["monthly_listener_share"] / result["population_share"]
    )
    result["follower_output_quotient"] = (
        result["follower_share"] / result["population_share"]
    )
    result["largest_band_follower_share"] = (
        result["largest_band_followers"] / result["followers_total"]
    ).fillna(0)
    result["representation_status"] = result["band_count"].map(
        lambda count: (
            "zero selected bands"
            if count == 0
            else "one selected band"
            if count == 1
            else "two or more selected bands"
        )
    )

    result = result.sort_values(
        ["band_output_quotient", "follower_output_quotient", "study_city_label"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    coverage: dict[str, float | int] = {
        "selected_bands": int(selected_band_count),
        "mapped_bands": int(mapped["returned_spotify_id"].nunique()),
        "mapped_band_share": float(result["band_share"].sum()),
        "selected_monthly_listeners": int(selected_listener_total),
        "mapped_monthly_listener_share": float(
            result["monthly_listener_share"].sum()
        ),
        "selected_followers": int(selected_follower_total),
        "mapped_follower_share": float(result["follower_share"].sum()),
        "population_fuas": int(len(population_frame)),
        "mapped_fuas": int(result["band_count"].gt(0).sum()),
        "zero_band_fuas": int(result["band_count"].eq(0).sum()),
        "population_total": int(population_total),
    }
    return result, coverage


def _format_share_tick(value: float, _: int) -> str:
    if value < 0.0001:
        return f"{value:.3%}"
    if value < 0.001:
        return f"{value:.2%}"
    if value < 0.01:
        return f"{value:.1%}"
    return f"{value:.0%}"


def _bubble_size(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 70
    return 70 + 1_500 * math.sqrt(value / maximum)


def plot_follower_share_vs_population_share(
    shares: pd.DataFrame,
    *,
    snapshot_date: str,
    selected_count: int,
    mapping_label: str,
    output_dir: Path,
    filename: str = "chart_01_follower_share_vs_population_share.png",
    label_cities: Iterable[str] = (
        "Bath and North East Somerset",
        "Birmingham",
        "Crawley",
        "Glasgow",
        "Leeds",
        "Liverpool",
        "London",
        "Manchester",
        "Oxford",
        "Sheffield",
    ),
) -> Path:
    """Plot selected-band follower share against FUA population share."""

    required = {
        "study_city_label",
        "population_share",
        "follower_share",
        "band_count",
    }
    missing = required.difference(shares.columns)
    if missing:
        raise ValueError(f"Share metrics are missing columns: {sorted(missing)}")
    plot_data = shares.loc[
        shares["band_count"].gt(0) & shares["follower_share"].gt(0)
    ].copy()
    if len(plot_data) < 8:
        raise ValueError("At least eight represented FUAs are required")

    apply_chart_style()
    fig, ax = plt.subplots(figsize=(11.8, 8.2))
    max_band_count = float(plot_data["band_count"].max())
    plot_data["bubble_size"] = plot_data["band_count"].map(
        lambda value: _bubble_size(float(value), max_band_count)
    )
    one_band = plot_data["band_count"].eq(1)
    multi_band = plot_data["band_count"].ge(2)
    ax.scatter(
        plot_data.loc[multi_band, "population_share"],
        plot_data.loc[multi_band, "follower_share"],
        s=plot_data.loc[multi_band, "bubble_size"],
        color=HOUSE["blue_soft"],
        edgecolor=HOUSE["blue"],
        linewidth=1.2,
        alpha=0.78,
        zorder=3,
    )
    ax.scatter(
        plot_data.loc[one_band, "population_share"],
        plot_data.loc[one_band, "follower_share"],
        s=plot_data.loc[one_band, "bubble_size"],
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.5,
        alpha=0.95,
        zorder=4,
    )

    minimum = min(
        float(plot_data["population_share"].min()),
        float(plot_data["follower_share"].min()),
    )
    maximum = max(
        float(plot_data["population_share"].max()),
        float(plot_data["follower_share"].max()),
    )
    lower_limit = 10 ** math.floor(math.log10(minimum)) / 1.6
    upper_limit = min(1.0, 10 ** math.ceil(math.log10(maximum)))
    ax.plot(
        [lower_limit, upper_limit],
        [lower_limit, upper_limit],
        color=HOUSE["ink_soft"],
        linewidth=1.1,
        linestyle=(0, (4, 4)),
        zorder=1,
    )
    ax.text(
        0.018,
        0.032,
        "Parity · 1.0× follower quotient",
        transform=ax.transAxes,
        rotation=35,
        color=HOUSE["secondary"],
        fontsize=9,
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lower_limit, upper_limit)
    ax.set_ylim(lower_limit, upper_limit)
    ax.xaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.grid(which="major", color=HOUSE["rule_soft"], linewidth=0.9)
    ax.grid(which="minor", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlabel(
        f"Share of population across all {len(shares)} UK FUAs · 2024 · log scale"
    )
    ax.set_ylabel(
        f"Share of followers across selected top-{selected_count} bands · log scale"
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(HOUSE["ink"])
    ax.spines[["left", "bottom"]].set_linewidth(0.8)

    offsets = {
        "Bath and North East Somerset": (8, 10),
        "Birmingham": (8, 5),
        "Crawley": (8, 10),
        "Glasgow": (8, -17),
        "Leeds": (8, -18),
        "Liverpool": (8, 9),
        "London": (-48, 15),
        "Manchester": (8, 9),
        "Oxford": (8, 9),
        "Sheffield": (8, 10),
    }
    labels = set(label_cities)
    for row in plot_data.loc[
        plot_data["study_city_label"].isin(labels)
    ].itertuples(index=False):
        ax.annotate(
            row.study_city_label,
            (row.population_share, row.follower_share),
            xytext=offsets.get(row.study_city_label, (6, 6)),
            textcoords="offset points",
            fontsize=9,
            color=(
                HOUSE["warning"]
                if row.band_count == 1
                else HOUSE["ink_soft"]
            ),
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": HOUSE["page"],
                "edgecolor": "none",
                "alpha": 0.82,
            },
            zorder=6,
        )

    count_references = [1, 10, 100]
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · selected bands",
        areas=[
            _bubble_size(value, max_band_count)
            for value in count_references
        ],
        labels=[f"{value}" for value in count_references],
        items=[
            {
                "kind": "marker",
                "label": "Multi-band cities",
                "facecolor": HOUSE["blue_soft"],
                "edgecolor": HOUSE["blue"],
            },
            {
                "kind": "marker",
                "label": "Single-band cities",
                "facecolor": HOUSE["page"],
                "edgecolor": HOUSE["warning"],
            },
        ],
        loc="lower right",
    )

    ax.set_title(
        "UK FUA share of selected-band followers versus population",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        (
            f"Top {selected_count} UK groups · Spotify snapshot {snapshot_date} · "
            f"{mapping_label} · bubble area shows selected-band count"
        ),
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    zero_count = int(shares["band_count"].eq(0).sum())
    fig.text(
        0.083,
        0.012,
        (
            f"{len(plot_data)} represented FUAs shown; {zero_count} zero-band FUAs "
            "remain in the population denominator but cannot appear on log axes. "
            "Follower shares use the full selected-band denominator, including "
            "unmapped bands."
        ),
        color=HOUSE["secondary"],
        fontsize=8.7,
    )
    fig.tight_layout(rect=(0.02, 0.045, 1, 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=HOUSE["page"],
    )
    plt.show()
    return output_path


def plot_band_share_vs_population_share(
    shares: pd.DataFrame,
    *,
    snapshot_date: str,
    selected_count: int,
    mapping_label: str,
    output_dir: Path,
    filename: str = "chart_01_band_share_vs_population_share.png",
    label_cities: Iterable[str] = (
        "Bath and North East Somerset",
        "Birmingham",
        "Crawley",
        "Glasgow",
        "Leeds",
        "Liverpool",
        "London",
        "Manchester",
        "Oxford",
        "Sheffield",
    ),
) -> Path:
    """Plot selected-band share against population share on matching log axes."""

    required = {
        "study_city_label",
        "population_share",
        "band_share",
        "follower_share",
        "band_count",
    }
    missing = required.difference(shares.columns)
    if missing:
        raise ValueError(f"Share metrics are missing columns: {sorted(missing)}")

    plot_data = shares.loc[shares["band_count"].gt(0)].copy()
    if len(plot_data) < 8:
        raise ValueError("At least eight represented FUAs are required")

    apply_chart_style()
    fig, ax = plt.subplots(figsize=(11.8, 8.2))
    max_follower_share = float(plot_data["follower_share"].max())
    plot_data["bubble_size"] = plot_data["follower_share"].map(
        lambda value: _bubble_size(float(value), max_follower_share)
    )

    one_band = plot_data["band_count"].eq(1)
    multi_band = plot_data["band_count"].ge(2)
    ax.scatter(
        plot_data.loc[multi_band, "population_share"],
        plot_data.loc[multi_band, "band_share"],
        s=plot_data.loc[multi_band, "bubble_size"],
        color=HOUSE["blue_soft"],
        edgecolor=HOUSE["blue"],
        linewidth=1.2,
        alpha=0.78,
        zorder=3,
    )
    ax.scatter(
        plot_data.loc[one_band, "population_share"],
        plot_data.loc[one_band, "band_share"],
        s=plot_data.loc[one_band, "bubble_size"],
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.5,
        alpha=0.95,
        zorder=4,
    )

    minimum = min(
        float(plot_data["population_share"].min()),
        float(plot_data["band_share"].min()),
    )
    maximum = max(
        float(plot_data["population_share"].max()),
        float(plot_data["band_share"].max()),
    )
    lower_limit = 10 ** math.floor(math.log10(minimum)) / 1.6
    upper_limit = min(1.0, 10 ** math.ceil(math.log10(maximum)))
    ax.plot(
        [lower_limit, upper_limit],
        [lower_limit, upper_limit],
        color=HOUSE["ink_soft"],
        linewidth=1.1,
        linestyle=(0, (4, 4)),
        zorder=1,
    )
    ax.text(
        0.018,
        0.032,
        "Parity · 1.0× output quotient",
        transform=ax.transAxes,
        rotation=35,
        color=HOUSE["secondary"],
        fontsize=9,
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lower_limit, upper_limit)
    ax.set_ylim(lower_limit, upper_limit)
    ax.xaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(_format_share_tick))
    ax.grid(which="major", color=HOUSE["rule_soft"], linewidth=0.9)
    ax.grid(which="minor", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlabel(
        f"Share of population across all {len(shares)} UK FUAs · 2024 · log scale"
    )
    ax.set_ylabel(
        f"Share of selected top-{selected_count} bands · log scale"
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(HOUSE["ink"])
    ax.spines[["left", "bottom"]].set_linewidth(0.8)

    offsets = {
        "Bath and North East Somerset": (7, 11),
        "Birmingham": (8, 4),
        "Crawley": (7, -18),
        "Glasgow": (7, 9),
        "Leeds": (8, -20),
        "Liverpool": (8, 10),
        "London": (-48, 15),
        "Manchester": (8, 9),
        "Oxford": (8, 9),
        "Sheffield": (8, 11),
    }
    labels = set(label_cities)
    for row in plot_data.loc[
        plot_data["study_city_label"].isin(labels)
    ].itertuples(index=False):
        ax.annotate(
            row.study_city_label,
            (row.population_share, row.band_share),
            xytext=offsets.get(row.study_city_label, (6, 6)),
            textcoords="offset points",
            fontsize=9,
            color=(
                HOUSE["warning"]
                if row.band_count == 1
                else HOUSE["ink_soft"]
            ),
            bbox={
                "boxstyle": "round,pad=0.15",
                "facecolor": HOUSE["page"],
                "edgecolor": "none",
                "alpha": 0.82,
            },
            zorder=6,
        )

    follower_reference_shares = [0.01, 0.10, 0.50]
    add_superposed_bubble_legend(
        ax,
        title="Bubble area · follower share",
        areas=[
            _bubble_size(value, max_follower_share)
            for value in follower_reference_shares
        ],
        labels=[f"{value:.0%}" for value in follower_reference_shares],
        items=[
            {
                "kind": "marker",
                "label": "Multi-band cities",
                "facecolor": HOUSE["blue_soft"],
                "edgecolor": HOUSE["blue"],
            },
            {
                "kind": "marker",
                "label": "Single-band cities",
                "facecolor": HOUSE["page"],
                "edgecolor": HOUSE["warning"],
            },
        ],
        loc="lower right",
    )

    ax.set_title(
        "UK FUA share of selected bands versus population",
        loc="left",
        pad=35,
        fontsize=15,
        fontweight="normal",
    )
    ax.text(
        0,
        1.018,
        (
            f"Top {selected_count} UK groups · Spotify snapshot {snapshot_date} · "
            f"{mapping_label} · bubble area shows follower share"
        ),
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )
    zero_count = int(shares["band_count"].eq(0).sum())
    fig.text(
        0.083,
        0.012,
        (
            f"{len(plot_data)} represented FUAs shown; {zero_count} zero-band FUAs "
            "remain in the population denominator but cannot appear on log axes. "
            "Shares use the full selected-band denominator, including unmapped "
            "bands."
        ),
        color=HOUSE["secondary"],
        fontsize=8.7,
    )
    fig.tight_layout(rect=(0.02, 0.045, 1, 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=HOUSE["page"],
    )
    plt.show()
    return output_path
