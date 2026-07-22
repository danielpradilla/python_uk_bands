#!/usr/bin/env python3
"""Build the offline ten-band scene-depth experiment notebook."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat as nbf
import pandas as pd
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "notebooks"
    / "experiments"
    / "uk_bands_scene_depth_10_per_city.ipynb"
)
DEFAULT_SNAPSHOT_SELECTOR = "20260717T203002Z"
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.analysis import build_city_rankings
from python_uk_bands.dataset import load_shortlist_dataset
from python_uk_bands.scene_depth import build_scene_depth_rankings
from python_uk_bands.scene_depth_snapshots import (
    SceneDepthSnapshot,
    resolve_scene_depth_snapshot,
)


FOLLOWER_THRESHOLD = 100_000
PUBLISHED_TOP_N = 3


def markdown(source: str):
    """Create a normalized markdown cell."""
    return nbf.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    """Create a normalized code cell."""
    return nbf.v4.new_code_cell(source.strip() + "\n")


def _natural_list(values: list[str]) -> str:
    """Join a short list for reader-facing prose."""
    if len(values) < 2:
        return "".join(values)
    return f"{', '.join(values[:-1])} and {values[-1]}"


def _notebook_path_reference(path: Path) -> tuple[str, str]:
    """Return reader-facing text and runnable code for a local path."""
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return str(path), f"Path({str(path)!r})"
    return relative.as_posix(), f"PROJECT_ROOT / {relative.as_posix()!r}"


def build_facts(snapshot: SceneDepthSnapshot) -> dict:
    """Calculate the volatile statements used in the notebook narrative."""
    bands = pd.read_csv(snapshot.metrics_path)
    rankings = build_scene_depth_rankings(
        bands,
        metric="monthly_listeners",
        trim_each_tail=1,
        expected_cities=10,
        bands_per_city=10,
    )
    saved = pd.read_csv(snapshot.rankings_path)
    assert_frame_equal(
        rankings.loc[:, saved.columns],
        saved,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )

    published_bands = load_shortlist_dataset()
    published_eligible = published_bands.loc[
        published_bands["followers"] >= FOLLOWER_THRESHOLD
    ].copy()
    published = build_city_rankings(
        published_eligible,
        metric="monthly_listeners",
        top_n=PUBLISHED_TOP_N,
    )

    untrimmed_top = (
        rankings.sort_values("untrimmed_rank").head(3)["city"].tolist()
    )
    top_excluded_top = (
        rankings.sort_values("top_excluded_rank").head(3)["city"].tolist()
    )
    symmetric_top = rankings.sort_values("rank").head(3)["city"].tolist()
    published_top = published.sort_values("rank").head(3)["city"].tolist()
    concentration = rankings.set_index("city")["top_band_concentration"]
    london = rankings.set_index("city").loc[
        "London", "population_normalized_trimmed_mean"
    ]
    birmingham = rankings.set_index("city").loc[
        "Birmingham", "population_normalized_trimmed_mean"
    ]

    return {
        "snapshot_date": pd.to_datetime(bands["stats_extracted_at"]).max(),
        "untrimmed_top": _natural_list(untrimmed_top),
        "top_excluded_top": _natural_list(top_excluded_top),
        "symmetric_top": _natural_list(symmetric_top),
        "published_top": _natural_list(published_top),
        "top_only_matches_symmetric": bool(
            rankings["symmetric_vs_top_only_rank_shift"].eq(0).all()
        ),
        "liverpool_concentration": concentration["Liverpool"],
        "sheffield_concentration": concentration["Sheffield"],
        "london_birmingham_gap": abs(london - birmingham) / max(london, birmingham),
        "medium_origin_rows": int(bands["origin_confidence"].eq("medium").sum()),
        "review_rows": int(bands["editorial_review_flag"].sum()),
    }


def build_notebook(
    snapshot: SceneDepthSnapshot,
    *,
    chart_output_dir: Path,
):
    """Return the complete scene-depth experiment notebook."""
    facts = build_facts(snapshot)
    snapshot_long = facts["snapshot_date"].strftime("%d %B %Y")
    snapshot_short = facts["snapshot_date"].strftime("%d %b %Y")
    metrics_display, metrics_reference = _notebook_path_reference(
        snapshot.metrics_path
    )
    rankings_display, rankings_reference = _notebook_path_reference(
        snapshot.rankings_path
    )
    _, chart_dir_reference = _notebook_path_reference(chart_output_dir)

    cells = [
        markdown(
            f"""
# Scene-depth experiment: ten bands per city

## tl;dr

This companion notebook tests whether the published city ranking survives a broader, balanced sample of ten bands per city. It does not replace the five-band publication notebook.

On the frozen Spotify snapshot from {snapshot_long}, the untrimmed ten-band ranking starts with {facts['untrimmed_top']}. Removing each city's largest band changes the top three to {facts['top_excluded_top']}. Removing both the largest and smallest band produces {facts['symmetric_top']}.

The top-excluded and symmetric-trim variants produce the same city order. Manchester becomes first, Sheffield remains second after Arctic Monkeys is removed, and Liverpool falls from third to fifth after the Beatles are removed. This is evidence that the original ordering is sensitive to superstar concentration and catalogue breadth.
            """
        ),
        markdown(
            """
## Context & Methods

The published notebook uses `reference/original_shortlist.csv`: 50 bands, five per city. This experiment uses `reference/scene_depth_bands.csv`: 100 bands, ten per city.

Three population-normalized variants are compared:

1. **All ten:** sum all ten bands' monthly listeners and divide by built-up-area population.
2. **Highest excluded:** remove the largest band, sum the other nine and divide by population.
3. **Symmetric trim:** remove one highest and one lowest band, calculate the mean of the middle eight and divide by population.

Removing one observation from each tail is a 10% trim per tail, or 20% of observations removed overall. The primary symmetric-trim measure is the **population-normalized trimmed mean**: the middle-eight mean divided by built-up-area population. Because every city retains eight bands, its ranking is identical to the earlier trimmed-total formulation; only the displayed scale changes.

### Key assumptions

- The manually curated 100-band catalogue is treated as fixed. Recreating the selection from scratch is not deterministic.
- Spotify monthly listeners measure global platform reach, not listening by local residents.
- Built-up-area population is a normalization denominator, not an estimate of each band's local audience.
- The 2021 population data and the selected Spotify snapshot refer to different dates.
            """
        ),
        code(
            """
# Locate the repository and import the reusable experiment code.
from pathlib import Path
import sys

import pandas as pd
from pandas.testing import assert_frame_equal
from IPython.display import display


def find_project_root() -> Path:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "reference" / "scene_depth_bands.csv").exists():
            return candidate
    raise FileNotFoundError("Run this notebook from inside the uk-music-cities repository")


PROJECT_ROOT = find_project_root()
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


from python_uk_bands.analysis import build_city_rankings
from python_uk_bands.dataset import load_shortlist_dataset
from python_uk_bands.scene_depth import (
    build_scene_depth_rankings,
    validate_scene_depth_dataset,
)
from python_uk_bands.scene_depth_visuals import (
    plot_scene_depth_rank_comparison,
    plot_scene_depth_scores,
    plot_top_band_concentration,
)
from python_uk_bands.visuals import apply_chart_style

apply_chart_style()
            """
        ),
        markdown(
            f"""
## Data

Notebook execution is offline and reads only frozen local inputs:

- `reference/scene_depth_bands.csv`: the fixed 100-band catalogue and row-level origin evidence.
- `{metrics_display}`: band identities, monthly listeners and population.
- `{rankings_display}`: the saved result used for the reproducibility check.
- `reference/original_shortlist.csv` and `data/processed/shortlist_spotify_metrics.json`: the published 50-band baseline used only for rank comparison.

The selected snapshot is **`{snapshot.snapshot_id}`**, with Spotify metrics dated **{snapshot_long}**. No Spotify or MusicBrainz requests occur during notebook execution.
            """
        ),
        code(
            f"""
# Load the frozen experiment inputs.
SNAPSHOT_ID = "{snapshot.snapshot_id}"
CATALOG_PATH = PROJECT_ROOT / "reference" / "scene_depth_bands.csv"
METRICS_PATH = {metrics_reference}
SAVED_RANKINGS_PATH = {rankings_reference}
CHART_OUTPUT_DIR = {chart_dir_reference}

catalog = pd.read_csv(CATALOG_PATH, keep_default_na=False)
band_data = pd.read_csv(METRICS_PATH)
saved_rankings = pd.read_csv(SAVED_RANKINGS_PATH)

display(
    band_data[
        [
            "band",
            "city",
            "monthly_listeners",
            "population",
            "origin_confidence",
            "stats_extracted_at",
        ]
    ].head()
)
            """
        ),
        markdown(
            f"""
### Data-quality checks

The design requires exactly 100 unique bands, ten cities and ten bands per city. Every row must have a positive population, a non-negative monthly-listener value and an exact reviewed Spotify name match.

The catalogue contains {facts['medium_origin_rows']} medium-confidence origin assignments, all of which remain flagged for editorial review. That does not prevent calculation, but it limits how definitively the result should be presented.
            """
        ),
        code(
            """
# Validate the balanced design, identity coverage and frozen snapshot.
validate_scene_depth_dataset(
    band_data,
    expected_cities=10,
    bands_per_city=10,
)
assert len(band_data) == 100
assert band_data["band"].nunique() == 100
assert band_data["spotify_id"].nunique() == 100
assert band_data["match_quality"].eq("exact").all()
assert band_data["monthly_listeners"].ge(0).all()
assert band_data["stats_extracted_at"].nunique() == 1
assert set(catalog["band_name"]) == set(band_data["band"])

quality_summary = pd.DataFrame(
    {
        "Check": [
            "Bands",
            "Cities",
            "Bands per city",
            "Exact Spotify matches",
            "Medium-confidence origins",
            "Editorial-review flags",
        ],
        "Value": [
            len(band_data),
            band_data["city"].nunique(),
            int(band_data.groupby("city").size().min()),
            int(band_data["match_quality"].eq("exact").sum()),
            int(band_data["origin_confidence"].eq("medium").sum()),
            int(band_data["editorial_review_flag"].sum()),
        ],
    }
)
display(quality_summary)
            """
        ),
        markdown(
            """
## Results

### 1. Recalculate and verify the saved result

The ranking is recomputed from the frozen band-level metrics. The cell then compares every saved output column with the timestamped result. Any discrepancy stops execution.
            """
        ),
        code(
            """
# Recalculate all three ranking variants and verify the saved snapshot.
rankings = build_scene_depth_rankings(
    band_data,
    metric="monthly_listeners",
    trim_each_tail=1,
    expected_cities=10,
    bands_per_city=10,
)
assert_frame_equal(
    rankings.loc[:, saved_rankings.columns],
    saved_rankings,
    check_exact=False,
    rtol=1e-12,
    atol=1e-12,
)

rank_table = rankings[
    [
        "city",
        "untrimmed_rank",
        "top_excluded_rank",
        "rank",
        "population_normalized_trimmed_mean",
        "highest_excluded_bands",
        "lowest_excluded_bands",
    ]
].rename(
    columns={
        "city": "City",
        "untrimmed_rank": "All ten rank",
        "top_excluded_rank": "Highest excluded rank",
        "rank": "High + low excluded rank",
        "population_normalized_trimmed_mean": (
            "Population-normalized trimmed mean"
        ),
        "highest_excluded_bands": "Highest excluded",
        "lowest_excluded_bands": "Lowest excluded",
    }
)
display(rank_table)
            """
        ),
        code(
            f"""
# Compare city rank under the untrimmed and two trimmed variants.
figure_01_path = plot_scene_depth_rank_comparison(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_01_path)
            """
        ),
        markdown(
            f"""
The highest-only and symmetric-trim variants have identical ranks for all ten cities. Removing the smallest band therefore does not change the ordering in this snapshot; the rank changes come from removing the largest band.

Under the symmetric trim, {facts['symmetric_top']} are the top three cities.
            """
        ),
        markdown(
            """
### 2. Population-normalized trimmed mean

The population-normalized trimmed mean averages the middle eight bands' monthly listeners and divides that mean by built-up-area population. It is a comparative normalization ratio, not a local listening rate.
            """
        ),
        code(
            f"""
# Plot the population-normalized mean of the middle eight bands.
figure_02_path = plot_scene_depth_scores(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
London and Birmingham are effectively tied: their population-normalized trimmed means differ by only {facts['london_birmingham_gap']:.2%}. Their third- and fourth-place order should not be treated as a meaningful separation.
            """
        ),
        markdown(
            """
### 3. Superstar concentration

The following chart shows the share of each untrimmed ten-band total contributed by its largest band. A large share indicates that a city is more exposed to a single act's current popularity.
            """
        ),
        code(
            f"""
# Show how much of each city total comes from its largest selected band.
figure_03_path = plot_top_band_concentration(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_03_path)
            """
        ),
        markdown(
            f"""
The Beatles account for {facts['liverpool_concentration']:.1%} of Liverpool's selected total, while Arctic Monkeys account for {facts['sheffield_concentration']:.1%} of Sheffield's. Liverpool drops from third to fifth when its largest band is excluded. Sheffield drops from first to second but remains near the top, indicating greater reach among the remaining selected bands.
            """
        ),
        markdown(
            """
### 4. Comparison with the published five-band baseline

The published notebook uses five bands per city, a 100,000-follower eligibility threshold, the top three eligible bands and a September 2025 Spotify snapshot. This experiment uses ten bands, no follower threshold and a July 2026 snapshot. The comparison is a sensitivity check, not an apples-to-apples causal decomposition.
            """
        ),
        code(
            """
# Compare the experiment with the frozen published ranking.
FOLLOWER_THRESHOLD = 100_000
PUBLISHED_TOP_N = 3

published_bands = load_shortlist_dataset()
published_eligible = published_bands.loc[
    published_bands["followers"] >= FOLLOWER_THRESHOLD
].copy()
published_rankings = build_city_rankings(
    published_eligible,
    metric="monthly_listeners",
    top_n=PUBLISHED_TOP_N,
)

baseline_comparison = (
    published_rankings[["city", "rank"]]
    .rename(columns={"rank": "published_five_band_rank"})
    .merge(
        rankings[
            [
                "city",
                "untrimmed_rank",
                "top_excluded_rank",
                "rank",
            ]
        ].rename(columns={"rank": "symmetric_trim_rank"}),
        on="city",
        validate="one_to_one",
    )
    .sort_values("symmetric_trim_rank")
)
display(
    baseline_comparison.rename(
        columns={
            "city": "City",
            "published_five_band_rank": "Published rank",
            "untrimmed_rank": "Expanded all-ten rank",
            "top_excluded_rank": "Expanded top-excluded rank",
            "symmetric_trim_rank": "Expanded symmetric-trim rank",
        }
    )
)
            """
        ),
        markdown(
            f"""
## Takeaways

- The published top three are {facts['published_top']}; the expanded symmetric-trim top three are {facts['symmetric_top']}.
- Manchester has the strongest result after the largest act is removed.
- Sheffield remains second after Arctic Monkeys is removed, so its result is not solely a single-band anomaly.
- Liverpool is more sensitive to the Beatles and falls two places after the largest act is removed.
- Removing the lowest act has no additional rank effect in this snapshot.

### Limitations

This experiment is reproducible for the frozen files, but the manually curated selection is still subjective. {facts['review_rows']} origin assignments are medium confidence and flagged for review. Spotify monthly listeners change over time, and a refreshed snapshot may change both values and ranks. The experiment supports a robustness statement about this catalogue; it does not establish a definitive ranking of British music scenes.
            """
        ),
    ]

    return nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
    )


def build_parser() -> argparse.ArgumentParser:
    """Return command-line arguments for selecting a frozen snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        default=DEFAULT_SNAPSHOT_SELECTOR,
        help="Snapshot timestamp, YYYY-MM-DD date, or 'latest'",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Notebook path. Defaults to the canonical experiment for the "
            "publication snapshot and to a timestamped copy otherwise."
        ),
    )
    parser.add_argument(
        "--chart-dir",
        type=Path,
        help="Chart directory; defaults to a snapshot-specific directory",
    )
    return parser


def _default_output_path(snapshot_id: str) -> Path:
    if snapshot_id == DEFAULT_SNAPSHOT_SELECTOR:
        return DEFAULT_OUTPUT_PATH
    return (
        PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "snapshots"
        / f"uk_bands_scene_depth_{snapshot_id}.ipynb"
    )


def main(argv: list[str] | None = None) -> None:
    """Write the experiment notebook without touching the publication notebook."""
    args = build_parser().parse_args(argv)
    snapshot = resolve_scene_depth_snapshot(args.snapshot)
    output_path = args.output or _default_output_path(snapshot.snapshot_id)
    if args.chart_dir:
        chart_output_dir = args.chart_dir
    elif snapshot.snapshot_id == DEFAULT_SNAPSHOT_SELECTOR:
        chart_output_dir = PROJECT_ROOT / "artifacts" / "scene_depth"
    else:
        chart_output_dir = (
            PROJECT_ROOT / "artifacts" / "scene_depth" / snapshot.snapshot_id
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(
        build_notebook(snapshot, chart_output_dir=chart_output_dir),
        output_path,
    )
    print(output_path)


if __name__ == "__main__":
    main(sys.argv[1:])
