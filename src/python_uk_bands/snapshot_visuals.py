"""Charts for comparing frozen popularity snapshots."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .visuals import HOUSE, _finish_chart, _new_chart


def plot_city_score_snapshot_change(
    comparison: pd.DataFrame,
    *,
    baseline_column: str,
    candidate_column: str,
    baseline_label: str,
    candidate_label: str,
    title: str,
    subtitle: str,
    x_label: str,
    number: int,
    filename: str,
    output_dir: Path,
) -> Path:
    """Draw a compact dumbbell chart for two city-score snapshots."""
    plot_data = comparison.sort_values(candidate_column).reset_index(drop=True)
    y_positions = list(range(len(plot_data)))

    _, ax = _new_chart(figsize=(10.5, 6.8))
    for position, row in zip(y_positions, plot_data.itertuples(index=False)):
        baseline = getattr(row, baseline_column)
        candidate = getattr(row, candidate_column)
        ax.plot(
            [baseline, candidate],
            [position, position],
            color=HOUSE["rule"],
            linewidth=1.5,
            zorder=1,
        )

    ax.scatter(
        plot_data[baseline_column],
        y_positions,
        s=64,
        marker="o",
        color=HOUSE["page"],
        edgecolor=HOUSE["ink"],
        linewidth=1.1,
        label=baseline_label,
        zorder=2,
    )
    ax.scatter(
        plot_data[candidate_column],
        y_positions,
        s=70,
        marker="D",
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink"],
        linewidth=0.5,
        label=candidate_label,
        zorder=3,
    )
    ax.set_yticks(y_positions, plot_data["city"])
    ax.set_xlabel(x_label)
    ax.set_ylabel("")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")

    return _finish_chart(
        ax,
        number=number,
        title=title,
        subtitle=subtitle,
        filename=filename,
        output_dir=output_dir,
    )
