"""Charts for the isolated ten-band scene-depth experiment."""

from __future__ import annotations

from pathlib import Path

from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd

from .config import PROJECT_ROOT
from .visuals import HOUSE, _finish_chart, _new_chart


SCENE_DEPTH_CHART_DIR = PROJECT_ROOT / "artifacts" / "scene_depth"


def plot_scene_depth_rank_comparison(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 1,
    filename: str = "chart_01_scene_depth_rank_comparison.png",
) -> Path:
    """Compare each city's rank under the three scene-depth variants."""
    plot_data = rankings.sort_values("rank", ascending=False).reset_index(drop=True)
    y_positions = list(range(len(plot_data)))

    _, ax = _new_chart(figsize=(10.5, 6.8))
    for y_position, row in zip(y_positions, plot_data.itertuples(index=False)):
        ranks = [row.untrimmed_rank, row.top_excluded_rank, row.rank]
        ax.plot(
            [min(ranks), max(ranks)],
            [y_position, y_position],
            color=HOUSE["rule"],
            linewidth=1.2,
            zorder=1,
        )

    method_styles = (
        ("untrimmed_rank", "All ten bands", -0.14, "o", HOUSE["page"], HOUSE["ink"]),
        (
            "top_excluded_rank",
            "Highest excluded",
            0,
            "s",
            HOUSE["warning_soft"],
            HOUSE["warning"],
        ),
        (
            "rank",
            "Highest and lowest excluded",
            0.14,
            "D",
            HOUSE["blue"],
            HOUSE["ink"],
        ),
    )
    for column, label, offset, marker, fill, edge in method_styles:
        ax.scatter(
            plot_data[column],
            [position + offset for position in y_positions],
            s=68,
            marker=marker,
            color=fill,
            edgecolor=edge,
            linewidth=1,
            label=label,
            zorder=2,
        )

    ax.set_yticks(y_positions, plot_data["city"])
    ax.set_xticks(range(1, len(plot_data) + 1))
    ax.set_xlim(0.5, len(plot_data) + 0.5)
    ax.set_xlabel("City rank (1 is strongest)")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")

    return _finish_chart(
        ax,
        number=number,
        title="City rank under three ten-band scoring variants",
        subtitle=(
            "Current global Spotify monthly listeners divided by population · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_primary_vs_top_excluded_rank_comparison(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 4,
    filename: str = "chart_04_all_ten_vs_largest_excluded_rank.png",
) -> Path:
    """Compare the primary all-ten rank with the largest-band-excluded rank."""

    plot_data = rankings.sort_values(
        "untrimmed_rank", ascending=False
    ).reset_index(drop=True)
    y_positions = list(range(len(plot_data)))

    _, ax = _new_chart(figsize=(10.5, 6.8))
    for y_position, row in zip(
        y_positions, plot_data.itertuples(index=False)
    ):
        ax.plot(
            [row.untrimmed_rank, row.top_excluded_rank],
            [y_position, y_position],
            color=HOUSE["rule"],
            linewidth=1.2,
            zorder=1,
        )

    method_styles = (
        (
            "untrimmed_rank",
            "Primary: all ten bands",
            -0.08,
            "o",
            HOUSE["page"],
            HOUSE["ink"],
        ),
        (
            "top_excluded_rank",
            "Scene depth: largest band removed",
            0.08,
            "s",
            HOUSE["warning_soft"],
            HOUSE["warning"],
        ),
    )
    for column, label, offset, marker, fill, edge in method_styles:
        ax.scatter(
            plot_data[column],
            [position + offset for position in y_positions],
            s=72,
            marker=marker,
            color=fill,
            edgecolor=edge,
            linewidth=1,
            label=label,
            zorder=2,
        )

    ax.set_yticks(y_positions, plot_data["city"])
    ax.set_xticks(range(1, len(plot_data) + 1))
    ax.set_xlim(0.5, len(plot_data) + 0.5)
    ax.set_xlabel("City rank (1 is strongest)")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")

    return _finish_chart(
        ax,
        number=number,
        title="City rank before and after removing the largest band",
        subtitle=(
            "Population-normalized current global Spotify reach · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def _plot_population_normalized_total(
    rankings: pd.DataFrame,
    *,
    score_column: str,
    rank_column: str,
    snapshot_date: str,
    retained_description: str,
    title: str,
    number: int,
    filename: str,
    output_dir: Path,
    tick_step: float,
) -> Path:
    """Plot one population-normalized city total from the scene-depth results."""
    plot_data = rankings.sort_values(score_column)
    colors = [
        HOUSE["blue"] if rank <= 3 else HOUSE["gray_blue"]
        for rank in plot_data[rank_column]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        plot_data["city"],
        plot_data[score_column],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data[score_column].max()
    ax.set_xlim(0, maximum * 1.18)
    ax.xaxis.set_major_locator(MultipleLocator(tick_step))
    ax.set_xlabel(
        "Combined current global Spotify monthly listeners divided by population"
    )
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data[score_column]):
        ax.text(
            value + maximum * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}x",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.2,
        )

    return _finish_chart(
        ax,
        number=number,
        title=title,
        subtitle=(
            f"{retained_description} · built-up-area population denominator · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_ten_band_population_normalized_total(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 1,
    filename: str = "chart_01_ten_band_population_normalized_total.png",
) -> Path:
    """Plot all ten selected bands relative to city population."""
    return _plot_population_normalized_total(
        rankings,
        score_column="untrimmed_ratio",
        rank_column="untrimmed_rank",
        snapshot_date=snapshot_date,
        retained_description="All ten selected bands",
        title="Current global Spotify reach across ten selected bands",
        number=number,
        filename=filename,
        output_dir=output_dir,
        tick_step=10,
    )


def plot_top_excluded_population_normalized_total(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 3,
    filename: str = "chart_03_largest_band_excluded.png",
) -> Path:
    """Plot the other nine selected bands after removing each city's leader."""
    return _plot_population_normalized_total(
        rankings,
        score_column="top_excluded_ratio",
        rank_column="top_excluded_rank",
        snapshot_date=snapshot_date,
        retained_description="Largest selected band excluded; other nine summed",
        title="Current global Spotify reach after removing the largest band",
        number=number,
        filename=filename,
        output_dir=output_dir,
        tick_step=5,
    )


def plot_scene_depth_scores(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 2,
    filename: str = "chart_02_scene_depth_scores.png",
) -> Path:
    """Plot the population-normalized middle-eight trimmed mean."""
    score_column = "population_normalized_trimmed_mean"
    plot_data = rankings.sort_values(score_column)
    colors = [
        HOUSE["blue"] if rank <= 3 else HOUSE["gray_blue"]
        for rank in plot_data["rank"]
    ]

    _, ax = _new_chart()
    bars = ax.barh(
        plot_data["city"],
        plot_data[score_column],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data[score_column].max()
    ax.set_xlim(0, maximum * 1.18)
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.set_xlabel(
        "Mean current global Spotify monthly listeners divided by population"
    )
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data[score_column]):
        ax.text(
            value + maximum * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}x" if value < 0.1 else f"{value:.1f}x",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.2,
        )

    return _finish_chart(
        ax,
        number=number,
        title="Population-normalized trimmed mean",
        subtitle=(
            "Mean current global reach of middle eight divided by population · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_top_band_concentration(
    rankings: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path = SCENE_DEPTH_CHART_DIR,
    number: int = 3,
    filename: str = "chart_03_top_band_concentration.png",
) -> Path:
    """Plot the share contributed by each city's largest selected band."""
    plot_data = rankings.sort_values("top_band_concentration")
    labels = (
        plot_data["city"]
        + "  ·  "
        + plot_data["highest_excluded_bands"]
    )
    colors = [
        HOUSE["warning"] if share >= 0.5 else HOUSE["blue"]
        for share in plot_data["top_band_concentration"]
    ]

    _, ax = _new_chart(figsize=(10.5, 6.8))
    bars = ax.barh(
        labels,
        plot_data["top_band_concentration"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    ax.set_xlim(0, 0.66)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.xaxis.set_major_locator(MultipleLocator(0.1))
    ax.set_xlabel("Share of the ten-band city total")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data["top_band_concentration"]):
        ax.text(
            value + 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1%}",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=9.2,
        )

    return _finish_chart(
        ax,
        number=number,
        title="Largest band share of each selected city total",
        subtitle=(
            "Before trimming · gold marks shares of at least 50% · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )
