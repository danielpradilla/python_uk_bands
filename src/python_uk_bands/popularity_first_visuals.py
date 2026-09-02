"""House-styled charts for the canonical popularity-first experiment."""

from __future__ import annotations

from pathlib import Path

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator
import pandas as pd

from .visuals import HOUSE, _finish_chart, _new_chart


def add_raw_reach_rank(strict: pd.DataFrame) -> pd.DataFrame:
    """Add a reproducible raw-reach rank to the strict FUA result."""

    required = {
        "study_city_label",
        "band_count",
        "monthly_listeners_total",
        "rank_by_listener_reach_per_resident",
    }
    missing = sorted(required - set(strict.columns))
    if missing:
        raise ValueError(f"Strict FUA result is missing columns: {missing}")

    ranked = strict.copy()
    ranked["raw_reach_rank"] = (
        ranked["monthly_listeners_total"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    return ranked


def _listener_formatter(value: float, _: int) -> str:
    return f"{value / 1_000_000:.0f}m"


def _normalized_reach_column(frame: pd.DataFrame) -> str:
    """Use the catalogue-neutral rate, with legacy top-100 compatibility."""

    if "selected_monthly_listeners_per_resident" in frame.columns:
        return "selected_monthly_listeners_per_resident"
    return "top100_monthly_listeners_per_resident"


def plot_top_selected_bands(
    bands: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path,
    number: int = 1,
    filename: str = "chart_01_top_selected_bands.png",
) -> Path:
    """Show the top of the selected popularity-first band catalogue."""

    plot_data = bands.nsmallest(20, "popularity_rank").sort_values("monthly_listeners")
    colors = []
    for row in plot_data.itertuples(index=False):
        if row.spotify_name == "The Cure":
            colors.append(HOUSE["warning_soft"])
        elif row.popularity_rank <= 3:
            colors.append(HOUSE["blue"])
        else:
            colors.append(HOUSE["gray_blue"])

    _, ax = _new_chart(figsize=(10.5, 8.2))
    bars = ax.barh(
        plot_data["spotify_name"],
        plot_data["monthly_listeners"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data["monthly_listeners"].max()
    ax.set_xlim(0, maximum * 1.17)
    ax.xaxis.set_major_locator(MultipleLocator(20_000_000))
    ax.xaxis.set_major_formatter(FuncFormatter(_listener_formatter))
    ax.set_xlabel("Captured current global Spotify monthly listeners")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, value in zip(bars, plot_data["monthly_listeners"]):
        ax.text(
            value + maximum * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{value / 1_000_000:.1f}m",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=8.8,
        )
    ax.legend(
        handles=[
            Patch(
                facecolor=HOUSE["blue"],
                edgecolor=HOUSE["ink"],
                label="Top three selected bands",
            ),
            Patch(
                facecolor=HOUSE["warning_soft"],
                edgecolor=HOUSE["ink"],
                label="The Cure / Crawley",
            ),
        ],
        frameon=False,
        loc="lower right",
    )

    return _finish_chart(
        ax,
        number=number,
        title=(
            "The most-listened-to bands in the selected UK "
            f"top {len(bands)}"
        ),
        subtitle=(
            "Top 20 shown · The Cure is highlighted because Crawley later leads "
            f"the normalized view · Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_raw_fua_reach(
    strict: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path,
    number: int = 2,
    filename: str = "chart_02_raw_fua_reach.png",
) -> Path:
    """Plot raw captured reach for the strictly mapped FUAs."""

    plot_data = add_raw_reach_rank(strict).sort_values("monthly_listeners_total")
    colors = [
        HOUSE["blue"] if rank <= 3 else HOUSE["gray_blue"]
        for rank in plot_data["raw_reach_rank"]
    ]

    _, ax = _new_chart(figsize=(10.5, 9.2))
    bars = ax.barh(
        plot_data["study_city_label"],
        plot_data["monthly_listeners_total"],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data["monthly_listeners_total"].max()
    ax.set_xlim(0, maximum * 1.2)
    ax.xaxis.set_major_locator(MultipleLocator(200_000_000))
    ax.xaxis.set_major_formatter(FuncFormatter(_listener_formatter))
    ax.set_xlabel("Combined captured monthly listeners before normalization")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, (_, row) in zip(bars, plot_data.iterrows()):
        ax.text(
            row["monthly_listeners_total"] + maximum * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{row['monthly_listeners_total'] / 1_000_000:.1f}m · "
            f"n={int(row['band_count'])}",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=8.6,
        )

    return _finish_chart(
        ax,
        number=number,
        title="Captured reach before applying a population denominator",
        subtitle=(
            "Strictly mapped OECD/EU FUAs · top three raw totals in blue · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_population_adjusted_fua_reach(
    strict: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path,
    number: int = 3,
    filename: str = "chart_03_population_adjusted_fua_reach.png",
    selected_count: int | None = None,
) -> Path:
    """Plot the main population-adjusted result and flag one-band FUAs."""

    rate_column = _normalized_reach_column(strict)
    plot_data = strict.sort_values(rate_column)
    colors = []
    hatches = []
    for row in plot_data.itertuples(index=False):
        if row.band_count == 1:
            colors.append(HOUSE["warning_soft"])
            hatches.append("////")
        elif row.rank_by_listener_reach_per_resident <= 3:
            colors.append(HOUSE["blue"])
            hatches.append("")
        else:
            colors.append(HOUSE["gray_blue"])
            hatches.append("")

    _, ax = _new_chart(figsize=(10.5, 9.2))
    bars = ax.barh(
        plot_data["study_city_label"],
        plot_data[rate_column],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)

    maximum = plot_data[rate_column].max()
    ax.set_xlim(0, maximum * 1.2)
    ax.xaxis.set_major_locator(MultipleLocator(50))
    ax.set_xlabel(
        "Combined captured global monthly listeners divided by 2024 FUA population"
    )
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, (_, row) in zip(bars, plot_data.iterrows()):
        ax.text(
            row[rate_column] + maximum * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{row[rate_column]:.1f}x · "
            f"n={int(row['band_count'])}",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=8.6,
        )
    ax.legend(
        handles=[
            Patch(
                facecolor=HOUSE["warning_soft"],
                edgecolor=HOUSE["ink"],
                hatch="////",
                label="One selected band",
            ),
            Patch(
                facecolor=HOUSE["blue"],
                edgecolor=HOUSE["ink"],
                label="Top-three multi-band FUA",
            ),
            Patch(
                facecolor=HOUSE["gray_blue"],
                edgecolor=HOUSE["ink"],
                label="Other multi-band FUA",
            ),
        ],
        frameon=False,
        loc="lower right",
    )

    return _finish_chart(
        ax,
        number=number,
        title=(
            f"Captured top-{selected_count} reach relative to FUA population"
            if selected_count is not None
            else "Captured selected-band reach relative to FUA population"
        ),
        subtitle=(
            "Strict origin-to-FUA mapping · hatched bars depend on one selected "
            f"band · Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_multiband_stability(
    strict: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path,
    number: int = 4,
    filename: str = "chart_04_multiband_stability.png",
    selected_count: int | None = None,
) -> Path:
    """Show the normalized result among FUAs with at least two selected bands."""

    stable = strict.loc[strict["band_count"].ge(2)].copy()
    rate_column = _normalized_reach_column(stable)
    stable["stable_rank"] = (
        stable[rate_column]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    plot_data = stable.sort_values(rate_column)
    colors = [
        HOUSE["blue"] if rank <= 3 else HOUSE["gray_blue"]
        for rank in plot_data["stable_rank"]
    ]

    _, ax = _new_chart(figsize=(10.5, 6.6))
    bars = ax.barh(
        plot_data["study_city_label"],
        plot_data[rate_column],
        color=colors,
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
    )
    maximum = plot_data[rate_column].max()
    ax.set_xlim(0, maximum * 1.22)
    ax.xaxis.set_major_locator(MultipleLocator(20))
    ax.set_xlabel(
        "Combined captured global monthly listeners divided by 2024 FUA population"
    )
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    for bar, (_, row) in zip(bars, plot_data.iterrows()):
        ax.text(
            row[rate_column] + maximum * 0.016,
            bar.get_y() + bar.get_height() / 2,
            f"{row[rate_column]:.1f}x · "
            f"n={int(row['band_count'])}",
            va="center",
            color=HOUSE["ink_soft"],
            fontfamily="monospace",
            fontsize=8.8,
        )

    return _finish_chart(
        ax,
        number=number,
        title="Population-adjusted reach among multi-band FUAs",
        subtitle=(
            "Diagnostic restricted to areas with at least two selected bands; "
            "not a replacement for the complete "
            f"top-{selected_count or 'N'} ranking · Spotify snapshot "
            f"{snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )


def plot_raw_vs_normalized_fua_ranks(
    strict: pd.DataFrame,
    *,
    snapshot_date: str,
    output_dir: Path,
    number: int = 5,
    filename: str = "chart_05_raw_vs_normalized_fua_ranks.png",
) -> Path:
    """Compare raw and population-adjusted reach ranks on the same FUA set."""

    plot_data = add_raw_reach_rank(strict).sort_values(
        "rank_by_listener_reach_per_resident",
        ascending=False,
    )
    y_positions = list(range(len(plot_data)))
    labels = [
        f"{row.study_city_label} · n=1" if row.band_count == 1 else row.study_city_label
        for row in plot_data.itertuples(index=False)
    ]

    _, ax = _new_chart(figsize=(11.2, 9.4))
    for y_position, row in zip(y_positions, plot_data.itertuples(index=False)):
        ax.plot(
            [
                row.raw_reach_rank,
                row.rank_by_listener_reach_per_resident,
            ],
            [y_position, y_position],
            color=HOUSE["rule"],
            linewidth=1.2,
            zorder=1,
        )

    ax.scatter(
        plot_data["raw_reach_rank"],
        [position - 0.09 for position in y_positions],
        s=66,
        marker="o",
        color=HOUSE["page"],
        edgecolor=HOUSE["ink"],
        linewidth=1,
        label="Raw captured-reach rank",
        zorder=2,
    )
    ax.scatter(
        plot_data["rank_by_listener_reach_per_resident"],
        [position + 0.09 for position in y_positions],
        s=70,
        marker="D",
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink"],
        linewidth=0.8,
        label="Population-adjusted rank",
        zorder=2,
    )

    ax.set_yticks(y_positions, labels)
    for label, row in zip(ax.get_yticklabels(), plot_data.itertuples(index=False)):
        if row.band_count == 1:
            label.set_color(HOUSE["warning"])
    ax.set_xticks(range(1, len(plot_data) + 1))
    ax.set_xlim(0.5, len(plot_data) + 0.5)
    ax.set_xlabel("FUA rank (1 is strongest)")
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(
        handles=[
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=HOUSE["page"],
                markeredgecolor=HOUSE["ink"],
                label="Raw captured-reach rank",
            ),
            Line2D(
                [0],
                [0],
                marker="D",
                color="none",
                markerfacecolor=HOUSE["blue"],
                markeredgecolor=HOUSE["ink"],
                label="Population-adjusted rank",
            ),
        ],
        frameon=False,
        loc="upper right",
    )

    return _finish_chart(
        ax,
        number=number,
        title="FUA rank before and after population normalization",
        subtitle=(
            f"Same {len(plot_data)} strictly mapped FUAs in both views · "
            "one-band labels include n=1 · "
            f"Spotify snapshot {snapshot_date}"
        ),
        filename=filename,
        output_dir=output_dir,
    )
