"""House-styled charts for the reader-facing notebook."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd

from .config import CHART_DIR


HOUSE = {
    "page": "#fffdf9",
    "paper_soft": "#f7f7f5",
    "ink": "#000000",
    "ink_soft": "#28303d",
    "muted": "#39414d",
    "secondary": "#6d6d6d",
    "rule": "#d1d1d1",
    "rule_soft": "#e5e5e5",
    "blue": "#2f5f7f",
    "blue_soft": "#d1dfe4",
    "gray_blue": "#abb8c3",
    "warning": "#7a6100",
    "warning_soft": "#f1e7bd",
}

TOP_CITY_COLORS = ("#2f5f7f", "#c28a00", "#b05a7a")


def apply_chart_style() -> None:
    """Configure the house style for Matplotlib charts only."""
    plt.rcParams.update(
        {
            "figure.facecolor": HOUSE["page"],
            "axes.facecolor": HOUSE["page"],
            "axes.edgecolor": HOUSE["ink"],
            "axes.labelcolor": HOUSE["ink"],
            "axes.titlecolor": HOUSE["ink"],
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Helvetica Neue",
                "Arial",
                "DejaVu Sans",
            ],
            "font.size": 10.5,
            "font.weight": 300,
            "xtick.color": HOUSE["secondary"],
            "ytick.color": HOUSE["ink_soft"],
            "grid.color": HOUSE["rule_soft"],
            "grid.linewidth": 0.8,
        }
    )


def _new_chart(figsize: tuple[float, float] = (10, 6.2)) -> tuple[Figure, Axes]:
    return plt.subplots(figsize=figsize)


def _colors_for_highlighted_cities(
    cities: pd.Series,
    highlighted_cities: Sequence[str],
) -> list[str]:
    """Color three focal cities consistently and mute every other city."""
    if len(highlighted_cities) != 3 or len(set(highlighted_cities)) != 3:
        raise ValueError("Exactly three unique highlighted cities are required")
    palette = dict(zip(highlighted_cities, TOP_CITY_COLORS))
    return [palette.get(city, HOUSE["gray_blue"]) for city in cities]


def _finish_chart(
    ax: Axes,
    *,
    number: int,
    title: str,
    subtitle: str,
    filename: str,
    output_dir: Path = CHART_DIR,
) -> Path:
    title_artist = ax.set_title(
        f"{number:02d}. {title}",
        loc="left",
        x=0,
        pad=32,
        fontsize=15,
        fontweight="normal",
    )
    title_artist.set_clip_on(False)
    ax.text(
        0,
        1.012,
        subtitle,
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
        fontweight=300,
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(HOUSE["ink"])
    ax.spines[["left", "bottom"]].set_linewidth(0.8)
    if len(ax.figure.axes) == 1:
        ax.figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    ax.figure.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=HOUSE["page"])
    plt.show()
    return output_path


def plot_top_three_ratio(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    follower_threshold: int,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot the preferred monthly-listener ranking."""
    plot_data = rankings.sort_values("top_n_ratio")
    colors = [
        HOUSE["blue"] if city == rankings.iloc[0]["city"] else HOUSE["gray_blue"]
        for city in plot_data["city"]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        plot_data["city"],
        plot_data["top_n_ratio"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    ax.set_xlabel("Global monthly-listener count divided by built-up-area population")
    ax.set_ylabel("")
    ax.set_xlim(0, plot_data["top_n_ratio"].max() * 1.18)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data["top_n_ratio"]):
        ax.text(
            value + 0.7,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}x",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.5,
        )

    return _finish_chart(
        ax,
        number=6,
        title="Top-three monthly-listener reach relative to population",
        subtitle=(
            f"50-band shortlist · {follower_threshold:,}-follower threshold · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename="chart_06_top_three_monthly_listener_ratio.png",
        output_dir=output_dir,
    )


def plot_metric_rank_comparison(
    rank_comparison: pd.DataFrame,
    correlation: float,
    *,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot monthly-listener and follower ranks on a shared scale."""
    comparison = rank_comparison.sort_values("monthly_listener_rank", ascending=False)
    y_positions = list(range(len(comparison)))
    monthly_y = [value + 0.08 for value in y_positions]
    follower_y = [value - 0.08 for value in y_positions]

    _, ax = _new_chart()
    for monthly_position, follower_position, row in zip(
        monthly_y,
        follower_y,
        comparison.itertuples(index=False),
    ):
        ax.plot(
            [row.monthly_listener_rank, row.follower_rank],
            [monthly_position, follower_position],
            color=HOUSE["rule"],
            linewidth=1.2,
            zorder=1,
        )

    ax.scatter(
        comparison["monthly_listener_rank"],
        monthly_y,
        s=65,
        marker="o",
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
        label="Monthly listeners",
        zorder=2,
    )
    ax.scatter(
        comparison["follower_rank"],
        follower_y,
        s=65,
        marker="s",
        color=HOUSE["page"],
        edgecolor=HOUSE["ink"],
        linewidth=1.2,
        label="Followers",
        zorder=2,
    )
    ax.set_yticks(y_positions, comparison["city"])
    ax.set_xticks(range(1, len(comparison) + 1))
    ax.set_xlim(0.5, len(comparison) + 0.5)
    ax.set_xlabel("City rank (1 is strongest)")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")

    return _finish_chart(
        ax,
        number=7,
        title="Monthly-listener and follower city ranks",
        subtitle=f"Top-three score relative to population · rank correlation {correlation:.2f}",
        filename="chart_07_metric_rank_comparison.png",
        output_dir=output_dir,
    )


def plot_top_band_concentration(
    rankings: pd.DataFrame,
    *,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot the leading band's share of each city total."""
    concentration = rankings.assign(
        top_band_share=rankings["top_value"] / rankings["total_value"]
    ).sort_values("top_band_share")
    colors = [
        HOUSE["warning"] if city == "Bradford" else HOUSE["blue"]
        for city in concentration["city"]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        concentration["city"],
        concentration["top_band_share"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    ax.set_xlim(0, 1.08)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.set_xlabel("Leading band's share of eligible monthly listeners")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, share, band in zip(
        bars,
        concentration["top_band_share"],
        concentration["top_band"],
    ):
        ax.text(
            min(share + 0.018, 1.01),
            bar.get_y() + bar.get_height() / 2,
            f"{share:.0%}  {band}",
            va="center",
            fontsize=9,
            color=HOUSE["ink_soft"],
        )

    return _finish_chart(
        ax,
        number=8,
        title="Leading band's share of city monthly listeners",
        subtitle="Share of each city's eligible shortlist total · Bradford has one eligible band",
        filename="chart_08_top_band_concentration.png",
        output_dir=output_dir,
    )


def plot_threshold_coverage(
    bands: pd.DataFrame,
    eligible_bands: pd.DataFrame,
    *,
    follower_threshold: int,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot retained shortlist coverage after the follower threshold."""
    coverage = (
        bands.groupby("city", as_index=False)
        .size()
        .rename(columns={"size": "shortlisted_bands"})
        .merge(
            eligible_bands.groupby("city", as_index=False)
            .size()
            .rename(columns={"size": "eligible_bands"}),
            on="city",
            how="left",
            validate="one_to_one",
        )
        .fillna({"eligible_bands": 0})
        .sort_values(["eligible_bands", "city"], ascending=[True, False])
    )
    colors = [
        HOUSE["warning"] if value < 3 else HOUSE["blue"]
        for value in coverage["eligible_bands"]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        coverage["city"],
        coverage["eligible_bands"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    ax.set_xlim(0, coverage["shortlisted_bands"].max() + 0.6)
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.set_xlabel(f"Bands remaining after the {follower_threshold:,}-follower threshold")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, eligible, total in zip(
        bars,
        coverage["eligible_bands"],
        coverage["shortlisted_bands"],
    ):
        ax.text(
            eligible + 0.08,
            bar.get_y() + bar.get_height() / 2,
            f"{int(eligible)} of {int(total)}",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.5,
        )

    return _finish_chart(
        ax,
        number=5,
        title="Bands remaining after the follower threshold",
        subtitle="Eligible bands retained from each city's five-band shortlist",
        filename="chart_05_threshold_coverage.png",
        output_dir=output_dir,
    )


def plot_overall_city_monthly_listeners(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    shortlist_size: int,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot raw city monthly-listener totals without a population denominator."""
    plot_data = rankings.sort_values("total_value")
    leader = rankings.sort_values("total_value", ascending=False).iloc[0]["city"]
    colors = [
        HOUSE["blue"] if city == leader else HOUSE["gray_blue"]
        for city in plot_data["city"]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        plot_data["city"],
        plot_data["total_value"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data["total_value"].max()
    ax.set_xlim(0, maximum * 1.18)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1_000_000:.0f}m"))
    ax.set_xlabel("Combined Spotify monthly listeners")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data["total_value"]):
        ax.text(
            value + maximum * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{value / 1_000_000:.1f}m",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.2,
        )

    return _finish_chart(
        ax,
        number=1,
        title="Overall city monthly-listener totals",
        subtitle=(
            f"All {shortlist_size} shortlisted bands · no population adjustment · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename="chart_01_overall_city_monthly_listeners.png",
        output_dir=output_dir,
    )


def plot_population_rank_shift(
    rankings: pd.DataFrame,
    *,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot how city position changes when raw totals are population-adjusted."""
    comparison = rankings[["city", "total_value", "total_ratio"]].copy()
    comparison["raw_rank"] = comparison["total_value"].rank(
        method="min", ascending=False
    ).astype(int)
    comparison["adjusted_rank"] = comparison["total_ratio"].rank(
        method="min", ascending=False
    ).astype(int)
    comparison = comparison.sort_values("raw_rank")

    _, ax = _new_chart(figsize=(11.5, 7.2))
    for row in comparison.itertuples(index=False):
        if row.adjusted_rank < row.raw_rank:
            color = HOUSE["blue"]
            linestyle = "-"
        elif row.adjusted_rank > row.raw_rank:
            color = HOUSE["gray_blue"]
            linestyle = "--"
        else:
            color = HOUSE["rule"]
            linestyle = ":"
        ax.plot(
            [0, 1],
            [row.raw_rank, row.adjusted_rank],
            color=color,
            linestyle=linestyle,
            linewidth=1.8,
            marker="o",
            markersize=4.5,
            markeredgecolor=HOUSE["ink"],
            markeredgewidth=0.4,
            zorder=2,
        )
        ax.text(
            -0.04,
            row.raw_rank,
            f"{row.city}  {row.raw_rank}",
            ha="right",
            va="center",
            fontsize=9,
            color=HOUSE["ink_soft"],
        )
        ax.text(
            1.04,
            row.adjusted_rank,
            f"{row.adjusted_rank}  {row.city}",
            ha="left",
            va="center",
            fontsize=9,
            color=HOUSE["ink_soft"],
        )

    city_count = len(comparison)
    ax.set_xlim(-0.42, 1.42)
    ax.set_ylim(city_count + 0.55, 0.45)
    ax.set_xticks([0, 1], ["Raw total", "Per resident"])
    ax.set_yticks(range(1, city_count + 1))
    ax.set_ylabel("City rank (1 is strongest)")
    ax.grid(axis="y")
    ax.set_axisbelow(True)

    return _finish_chart(
        ax,
        number=4,
        title="City rank before and after population adjustment",
        subtitle=(
            "Same 50-band monthly-listener totals on both sides · "
            "solid blue rises, dashed gray-blue falls"
        ),
        filename="chart_04_population_rank_shift.png",
        output_dir=output_dir,
    )


def plot_city_band_stack(
    bands: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot each city total as five band-level monthly-listener segments."""
    city_totals = (
        bands.groupby("city")["monthly_listeners"]
        .sum()
        .sort_values()
    )
    cities = city_totals.index.tolist()
    segment_colors = [
        HOUSE["blue"],
        HOUSE["gray_blue"],
        HOUSE["warning"],
        HOUSE["blue_soft"],
        HOUSE["paper_soft"],
    ]
    segment_text_colors = [
        HOUSE["page"],
        HOUSE["ink"],
        HOUSE["page"],
        HOUSE["ink"],
        HOUSE["ink"],
    ]

    figure = plt.figure(figsize=(15, 8.4), layout="constrained")
    grid = figure.add_gridspec(1, 2, width_ratios=[1.35, 1.65], wspace=0.04)
    ax = figure.add_subplot(grid[0, 0])
    key_ax = figure.add_subplot(grid[0, 1])

    for y_position, city in enumerate(cities):
        city_bands = (
            bands.loc[bands["city"] == city]
            .sort_values(["monthly_listeners", "band"], ascending=[False, True])
            .reset_index(drop=True)
        )
        left = 0.0
        band_key: list[str] = []
        for position, row in city_bands.iterrows():
            value = float(row["monthly_listeners"])
            color = segment_colors[position]
            ax.barh(
                y_position,
                value,
                left=left,
                height=0.68,
                color=color,
                edgecolor=HOUSE["ink"],
                linewidth=0.45,
            )
            if value >= city_totals.max() * 0.008:
                ax.text(
                    left + value / 2,
                    y_position,
                    str(position + 1),
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    fontfamily="monospace",
                    color=segment_text_colors[position],
                )
            band_key.append(f"{position + 1} {row['band']}")
            left += value

        key_ax.text(
            0,
            y_position,
            "  ·  ".join(band_key),
            va="center",
            fontsize=7.2,
            color=HOUSE["ink_soft"],
        )

    ax.set_yticks(range(len(cities)), cities)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1_000_000:.0f}m"))
    ax.set_xlabel("Combined Spotify monthly listeners")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    key_ax.set_ylim(ax.get_ylim())
    key_ax.set_xlim(0, 1)
    key_ax.axis("off")

    return _finish_chart(
        ax,
        number=2,
        title="City monthly listeners stacked by band",
        subtitle=(
            f"All 50 shortlisted bands · segment numbers match the band key · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename="chart_02_city_band_stack.png",
        output_dir=output_dir,
    )


def plot_top_bands_by_followers(
    bands: pd.DataFrame,
    *,
    snapshot_date: str,
    highlighted_cities: Sequence[str],
    top_n: int = 20,
    output_dir: Path = CHART_DIR,
) -> Path:
    """Plot the shortlist's leading bands by Spotify followers."""
    leaders = bands.nlargest(top_n, "followers").sort_values("followers")
    labels = leaders["band"] + "  ·  " + leaders["city"]
    colors = _colors_for_highlighted_cities(
        leaders["city"],
        highlighted_cities,
    )
    highlighted_label = (
        f"{', '.join(highlighted_cities[:-1])} and {highlighted_cities[-1]}"
    )

    _, ax = _new_chart(figsize=(10.5, 8.5))
    bars = ax.barh(
        labels,
        leaders["followers"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.45,
    )
    maximum = leaders["followers"].max()
    ax.set_xlim(0, maximum * 1.17)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1_000_000:.0f}m"))
    ax.set_xlabel("Spotify followers")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, leaders["followers"]):
        ax.text(
            value + maximum * 0.009,
            bar.get_y() + bar.get_height() / 2,
            f"{value / 1_000_000:.1f}m",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=8.6,
        )

    return _finish_chart(
        ax,
        number=3,
        title="Top shortlisted British bands by Spotify followers",
        subtitle=(
            f"Top {len(leaders)} of the 50-band exploratory shortlist · "
            f"{highlighted_label} highlighted; all others grey · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename="chart_03_top_bands_by_followers.png",
        output_dir=output_dir,
    )
