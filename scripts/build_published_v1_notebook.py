"""Rebuild the archived September 2025 50-band publication notebook."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "notebooks"
    / "archive"
    / "published-v1"
    / "rebuild"
    / "uk_bands_punching_above_weight.ipynb"
)
ARCHIVED_CHART_DIR = (
    PROJECT_ROOT / "artifacts" / "archive" / "published-v1" / "rebuild"
)
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.analysis import build_city_rankings, build_threshold_sensitivity
from python_uk_bands.config import CHART_DIR, SHORTLIST_METRICS_PATH
from python_uk_bands.dataset import load_shortlist_dataset
from python_uk_bands.shortlist_snapshots import resolve_shortlist_snapshot


FOLLOWER_THRESHOLD = 100_000
TOP_N = 3
FOLLOWER_CHART_HIGHLIGHT_CITIES = ["London", "Sheffield", "Manchester"]


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


def build_facts(metrics_path: Path = SHORTLIST_METRICS_PATH) -> dict:
    """Calculate every volatile statement embedded in notebook prose."""
    bands = load_shortlist_dataset(metrics_path=metrics_path)
    eligible = bands.loc[bands["followers"] >= FOLLOWER_THRESHOLD].copy()
    monthly = build_city_rankings(eligible, metric="monthly_listeners", top_n=TOP_N)
    followers = build_city_rankings(eligible, metric="followers", top_n=TOP_N)
    comparison = (
        monthly[["city", "rank"]]
        .rename(columns={"rank": "monthly_rank"})
        .merge(
            followers[["city", "rank"]].rename(columns={"rank": "follower_rank"}),
            on="city",
            validate="one_to_one",
        )
    )
    correlation = comparison["monthly_rank"].corr(comparison["follower_rank"])
    raw_totals = build_city_rankings(
        bands,
        metric="monthly_listeners",
        top_n=int(bands.groupby("city").size().max()),
    )
    raw_totals["raw_rank"] = raw_totals["total_value"].rank(
        method="min", ascending=False
    ).astype(int)
    raw_totals["adjusted_total_rank"] = raw_totals["total_ratio"].rank(
        method="min", ascending=False
    ).astype(int)
    raw_order = raw_totals.sort_values("raw_rank")
    raw_leader = raw_order.iloc[0]
    raw_second = raw_order.iloc[1]
    adjusted_total_leader = raw_totals.sort_values("adjusted_total_rank").iloc[0]
    largest_rise = raw_totals.assign(
        rank_change=raw_totals["raw_rank"] - raw_totals["adjusted_total_rank"]
    ).sort_values(["rank_change", "city"], ascending=[False, True]).iloc[0]
    largest_fall = raw_totals.assign(
        rank_change=raw_totals["raw_rank"] - raw_totals["adjusted_total_rank"]
    ).sort_values(["rank_change", "city"], ascending=[True, True]).iloc[0]
    follower_order = bands.nlargest(3, "followers")
    follower_leader = follower_order.iloc[0]
    snapshot = bands["stats_extracted_at"].max()
    monthly_top = monthly.sort_values("rank").head(3)["city"].tolist()
    follower_top = followers.sort_values("rank").head(3)["city"].tolist()
    leader = monthly.sort_values("rank").iloc[0]
    leader_bands = (
        eligible.loc[eligible["city"] == leader["city"]]
        .nlargest(TOP_N, "monthly_listeners")["band"]
        .tolist()
    )
    shortlist_counts = bands.groupby("city").size()
    eligible_counts = eligible.groupby("city").size().reindex(shortlist_counts.index, fill_value=0)
    complete_cities = eligible_counts[eligible_counts == shortlist_counts].index.tolist()
    reduced = eligible_counts[eligible_counts < shortlist_counts].sort_values(ascending=False)
    reduced_text = _natural_list([f"{city} ({count})" for city, count in reduced.items()])
    concentration = monthly.assign(
        top_band_share=monthly["top_value"] / monthly["total_value"]
    ).set_index("city")
    sensitivity = build_threshold_sensitivity(
        bands,
        thresholds=[0, 100_000, 500_000, 1_000_000],
        metric="monthly_listeners",
        top_n=TOP_N,
    )
    sensitivity_leaders = (
        sensitivity.sort_values(["follower_threshold", "rank", "city"])
        .groupby("follower_threshold", as_index=False)
        .first()
    )
    threshold_leaders = dict(
        zip(
            sensitivity_leaders["follower_threshold"],
            sensitivity_leaders["city"],
        )
    )
    metric_sources = (
        sorted(bands["source_x"].dropna().unique())
        if "source_x" in bands.columns
        else []
    )

    return {
        "shortlist_rows": len(bands),
        "eligible_rows": len(eligible),
        "snapshot_long": f"{snapshot.day} {snapshot.strftime('%B %Y')}",
        "snapshot_iso": snapshot.strftime("%Y-%m-%d"),
        "correlation": correlation,
        "monthly_top": _natural_list(monthly_top),
        "follower_top": _natural_list(follower_top),
        "leader": leader["city"],
        "leader_ratio": leader["top_n_ratio"],
        "leader_top_n_value_m": leader["top_n_value"] / 1_000_000,
        "leader_population_m": leader["population"] / 1_000_000,
        "leader_bands": _natural_list(leader_bands),
        "complete_city_count": len(complete_cities),
        "reduced_text": reduced_text,
        "raw_leader": raw_leader["city"],
        "raw_leader_total_m": raw_leader["total_value"] / 1_000_000,
        "raw_second_city": raw_second["city"],
        "raw_second_total_m": raw_second["total_value"] / 1_000_000,
        "adjusted_total_leader": adjusted_total_leader["city"],
        "largest_rise_city": largest_rise["city"],
        "largest_rise_from": int(largest_rise["raw_rank"]),
        "largest_rise_to": int(largest_rise["adjusted_total_rank"]),
        "largest_fall_city": largest_fall["city"],
        "largest_fall_from": int(largest_fall["raw_rank"]),
        "largest_fall_to": int(largest_fall["adjusted_total_rank"]),
        "follower_leader": follower_leader["band"],
        "follower_leader_count": int(follower_leader["followers"]),
        "follower_runners_up": _natural_list(follower_order.iloc[1:]["band"].tolist()),
        "liverpool_concentration": concentration.loc[
            "Liverpool", "top_band_share"
        ],
        "sheffield_concentration": concentration.loc[
            "Sheffield", "top_band_share"
        ],
        "manchester_concentration": concentration.loc[
            "Manchester", "top_band_share"
        ],
        "threshold_leaders": threshold_leaders,
        "metric_source": (
            _natural_list(metric_sources)
            if metric_sources
            else "the saved SpotScraper snapshot"
        ),
    }


def build_notebook(
    *,
    metrics_path: Path = SHORTLIST_METRICS_PATH,
    chart_output_dir: Path = CHART_DIR,
    preview_label: str | None = None,
):
    """Return the complete reader-facing analysis notebook."""
    facts = build_facts(metrics_path)
    metrics_display, metrics_reference = _notebook_path_reference(metrics_path)
    _, chart_dir_reference = _notebook_path_reference(chart_output_dir)
    preview_notice = (
        f"\n\n> **CURRENT-DATA PREVIEW — {preview_label}.** "
        "This is a separate sensitivity run. The published notebook remains "
        "pinned to the September 2025 snapshot."
        if preview_label
        else ""
    )
    cells = [
        markdown(
            f"""
# Popular bands by British city: Spotify reach and population
{preview_notice}

## 01. Research question

This notebook compares the Spotify reach of bands associated with ten British cities. The dataset contains a personal shortlist of {facts['shortlist_rows']} bands, five per city. It is an exploratory sample, not a complete catalogue of UK bands or cities.

The main question is whether the selected bands from some cities have unusually high Spotify reach relative to built-up-area population.

Within this shortlist, {facts['leader']} ranks first when each city's top three eligible bands are measured by monthly listeners per resident. {facts['monthly_top']} are the top three cities. A follower-based version produces a similar ordering; the rank correlation is {facts['correlation']:.2f}, where 1.0 would mean identical ranks.
            """
        ),
        markdown(
            f"""
## 02. Scope and scoring

The shortlist covers named bands and groups; solo artists are excluded. It is weighted toward rock, indie, post-punk, new wave and related genres. The ten cities are in England and Scotland, so the sample does not represent the whole United Kingdom.

Each band is assigned to the built-up area where it formed or first became established. A built-up area is the continuously developed urban area around a city, rather than its administrative council boundary.

Monthly listeners approximate the number of unique Spotify users who listened to an artist during a rolling monthly window. Followers are Spotify users who chose to follow the artist. This notebook run uses the {facts['snapshot_long']} snapshot of both measures.

Three city views are used:

- Raw total: combined monthly listeners across all five shortlisted bands.
- Leading-band share: the proportion of a city's eligible listeners attributable to its largest band.
- Preferred score: combined monthly listeners for the top three bands with at least 100,000 followers, divided by built-up-area population.
            """
        ),
        markdown(
            f"""
## 03. Data sources

The band shortlist and city assignments were created manually in the original project scratchpad. They reflect the initial selection used to test the idea.

Population figures are 2021 built-up-area counts from the Office for National Statistics and Scotland's 2021 Census. The original notebook compiled the figures through City Population. Spotify artist IDs were found through Spotify search. Followers and monthly listeners in this run came from {facts['metric_source']}, dated {facts['snapshot_long']}.

A broader MusicBrainz catalogue has since been collected, but it is not used in this notebook.

The analysis reads saved local files and does not call live APIs. This keeps reruns reproducible.

### 03.01 Analysis setup

The setup cell imports the shared calculation and plotting functions. Custom styling is limited to the exported figures.
            """
        ),
        code(
            """
# Find the repository and import the reusable project code.
from pathlib import Path
import sys

import pandas as pd
from IPython.display import display


def find_project_root() -> Path:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "reference" / "original_shortlist.csv").exists():
            return candidate
    raise FileNotFoundError("Run this notebook from inside the python_uk_bands repository")


PROJECT_ROOT = find_project_root()
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


from python_uk_bands.analysis import (
    build_city_rankings,
    build_threshold_sensitivity,
)
from python_uk_bands.dataset import (
    build_match_review_queue,
    build_quality_summary,
    load_shortlist_dataset,
    validate_shortlist_shape,
)
from python_uk_bands.visuals import (
    apply_chart_style,
    plot_city_band_stack,
    plot_metric_rank_comparison,
    plot_overall_city_monthly_listeners,
    plot_population_rank_shift,
    plot_threshold_coverage,
    plot_top_bands_by_followers,
    plot_top_band_concentration,
    plot_top_three_ratio,
)

apply_chart_style()
            """
        ),
        markdown(
            f"""
### 03.02 Input files

The analysis joins three files:

- `reference/original_shortlist.csv`: {facts['shortlist_rows']} bands, five from each of ten cities.
- `reference/built_up_areas.csv`: 2021 population denominators for comparable urban areas.
- `{metrics_display}`: Spotify IDs, followers and monthly listeners saved on {facts['snapshot_long']}.

The joined dataset has one row per band with its city, Spotify measures and population denominator.
            """
        ),
        code(
            f"""
# Join the shortlist, Spotify metrics and population at one row per band.
METRICS_PATH = {metrics_reference}
CHART_OUTPUT_DIR = {chart_dir_reference}
band_data = load_shortlist_dataset(metrics_path=METRICS_PATH)

preview_columns = [
    "band_name",
    "city",
    "followers",
    "monthly_listeners",
    "population",
    "stats_extracted_at",
]
display(band_data.loc[:, preview_columns].head())
            """
        ),
        markdown(
            """
## 04. Data quality

The joined dataset should contain 50 unique bands, ten cities, five bands per city, one Spotify ID per band and no missing popularity or population values.

Spotify matches were selected automatically. An `exact` name match does not prove that the correct artist was selected. The review table includes non-exact matches and accounts with fewer than 100 followers. Dog Is Dead is a known incorrect match; it falls below the eligibility threshold and does not affect the preferred ranking.
            """
        ),
        code(
            """
# Check the expected shape and show anything that still needs human review.
validate_shortlist_shape(band_data)
quality_summary = build_quality_summary(band_data)
match_review_queue = build_match_review_queue(band_data)

display(quality_summary)
display(match_review_queue)
            """
        ),
        markdown(
            """
## 05. Assumptions and limitations

- A band belongs to the built-up area where it formed or first became established. Some current assignments still need editorial review.
- Dividing global Spotify reach by local population is a normalization device. It does not mean local residents generated those streams or follows.
- The follower threshold removes tiny or mismatched accounts, but it can also remove a real act with strong passive listening and a small follower base.
- Bands are not independent observations. Related acts can emerge from the same scene and share members.
- Spotify measures platform reach. It does not measure musical influence, record sales, live audiences or the health of a local scene.
- The 2021 population denominator and {facts['snapshot_long']} Spotify snapshot refer to different dates.
            """
        ),
        markdown(
            f"""
## 06. Unadjusted Spotify reach

The first comparison sums monthly listeners across all five shortlisted bands in each city. No follower threshold or population adjustment is applied. Every city contributes the same number of bands.
            """
        ),
        code(
            """
# Calculate raw and per-resident totals from the same 50 bands.
BANDS_PER_CITY = int(band_data.groupby("city").size().max())
all_band_city_rankings = build_city_rankings(
    band_data,
    metric="monthly_listeners",
    top_n=BANDS_PER_CITY,
)
all_band_rank_shift = all_band_city_rankings[["city", "total_value", "total_ratio"]].copy()
all_band_rank_shift["raw_rank"] = all_band_rank_shift["total_value"].rank(
    method="min", ascending=False
).astype(int)
all_band_rank_shift["population_adjusted_rank"] = all_band_rank_shift["total_ratio"].rank(
    method="min", ascending=False
).astype(int)

display(
    all_band_rank_shift.sort_values("raw_rank").rename(
        columns={
            "city": "City",
            "total_value": "Monthly listeners",
            "total_ratio": "Monthly listeners / resident",
            "raw_rank": "Raw rank",
            "population_adjusted_rank": "Adjusted rank",
        }
    )
)
            """
        ),
        markdown(
            f"""
### 06.01 City totals

{facts['raw_leader']} ranks first with {facts['raw_leader_total_m']:.1f} million combined monthly listeners. {facts['raw_second_city']} ranks second with {facts['raw_second_total_m']:.1f} million. These totals measure the selected catalogues without accounting for city population.
            """
        ),
        code(
            """
# Plot the unadjusted city totals.
figure_01_path = plot_overall_city_monthly_listeners(
    all_band_city_rankings,
    snapshot_date=band_data["stats_extracted_at"].max().strftime("%d %b %Y"),
    shortlist_size=len(band_data),
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_01_path)
            """
        ),
        markdown(
            """
### 06.02 Band contributions to city totals

The stacked bars show how each of the five selected bands contributes to its city total. Coldplay accounts for the largest share of London's total. The Beatles dominate Liverpool. Manchester's total is distributed more evenly across Oasis, The Smiths, The 1975 and the remaining bands.

Segment numbers correspond to the band key on the right.
            """
        ),
        code(
            """
# Split each city total into its five selected bands.
figure_02_path = plot_city_band_stack(
    band_data,
    snapshot_date=band_data["stats_extracted_at"].max().strftime("%d %b %Y"),
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
### 06.03 Bands ranked by followers

{facts['follower_leader']} has the most followers in the shortlist, with {facts['follower_leader_count']:,}. {facts['follower_runners_up']} rank next. This figure covers the selected 50 bands rather than all British artists on Spotify.
            """
        ),
        code(
            f"""
# Rank the top 20 shortlisted bands by Spotify followers.
highlighted_cities = {FOLLOWER_CHART_HIGHLIGHT_CITIES!r}
figure_03_path = plot_top_bands_by_followers(
    band_data,
    snapshot_date=band_data["stats_extracted_at"].max().strftime("%d %b %Y"),
    highlighted_cities=highlighted_cities,
    top_n=20,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_03_path)
            """
        ),
        markdown(
            f"""
## 07. Effect of population adjustment

The next comparison divides each five-band monthly-listener total by built-up-area population. The bands and Spotify measures remain unchanged.

{facts['largest_rise_city']} moves from rank {facts['largest_rise_from']} to {facts['largest_rise_to']}. {facts['largest_fall_city']} moves from {facts['largest_fall_from']} to {facts['largest_fall_to']}. {facts['adjusted_total_leader']} ranks first after adjustment.

The ratio compares global Spotify reach with city size. It does not estimate listening by local residents.
            """
        ),
        code(
            """
# Show how each city moves when population is added to the denominator.
figure_04_path = plot_population_rank_shift(
    all_band_city_rankings,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_04_path)
            """
        ),
        markdown(
            f"""
## 08. Preferred scoring method

The preferred score includes bands with at least 100,000 followers, selects the three largest eligible bands in each city, sums their monthly listeners and divides the result by built-up-area population.

The threshold limits the influence of very small accounts and the top-three rule requires more than one successful band. Neither rule validates artist identity or corrects omissions from the shortlist.
            """
        ),
        code(
            """
# Apply the follower threshold and calculate the two preferred rankings.
FOLLOWER_THRESHOLD = 100_000
TOP_N = 3

eligible_bands = band_data.loc[band_data["followers"] >= FOLLOWER_THRESHOLD].copy()
monthly_rankings = build_city_rankings(
    eligible_bands,
    metric="monthly_listeners",
    top_n=TOP_N,
)
follower_rankings = build_city_rankings(
    eligible_bands,
    metric="followers",
    top_n=TOP_N,
)

rank_comparison = (
    monthly_rankings[["city", "rank"]]
    .rename(columns={"rank": "monthly_listener_rank"})
    .merge(
        follower_rankings[["city", "rank"]].rename(columns={"rank": "follower_rank"}),
        on="city",
        validate="one_to_one",
    )
)
rank_correlation = rank_comparison["monthly_listener_rank"].corr(
    rank_comparison["follower_rank"]
)

run_summary = pd.DataFrame(
    {
        "metric": ["Shortlisted bands", "Eligible bands", "Cities", "Rank correlation"],
        "value": [
            len(band_data),
            len(eligible_bands),
            len(monthly_rankings),
            f"{rank_correlation:.2f}",
        ],
    }
)
display(run_summary)
            """
        ),
        markdown(
            f"""
### 08.01 Follower-threshold coverage

{facts['complete_city_count']} cities retain all five shortlisted bands. Reduced coverage is {facts['reduced_text']}. Bradford retains only The Cult, so its preferred score does not represent a three-band catalogue.
            """
        ),
        code(
            """
# Show how much of each five-band shortlist survives the threshold.
figure_05_path = plot_threshold_coverage(
    band_data,
    eligible_bands,
    follower_threshold=FOLLOWER_THRESHOLD,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_05_path)
            """
        ),
        markdown(
            f"""
## 09. Population-adjusted city ranking

{facts['leader']}'s top three eligible bands have {facts['leader_top_n_value_m']:.1f} million monthly listeners. The built-up-area population is {facts['leader_population_m']:.3f} million. Dividing these values gives a reach-to-population ratio of {facts['leader_ratio']:.1f}.

The ratio is used to rank cities of different sizes. It is not a per-resident listening rate.
            """
        ),
        code(
            """
# Display the preferred ranking with enough context to audit it.
preferred_ranking_table = monthly_rankings[[
    "rank",
    "city",
    "top_n_ratio",
    "top_band",
    "eligible_bands",
]].rename(
    columns={
        "rank": "Rank",
        "city": "City",
        "top_n_ratio": "Top-three reach / population",
        "top_band": "Leading band",
        "eligible_bands": "Eligible bands",
    }
)

display(preferred_ranking_table)
            """
        ),
        markdown(
            f"""
### 09.01 Top-three monthly-listener ranking

{facts['leader']} ranks first; the top three are {facts['monthly_top']}. Its score is based on {facts['leader_bands']}.
            """
        ),
        code(
            """
# Plot the preferred top-three monthly-listener score.
figure_06_path = plot_top_three_ratio(
    monthly_rankings,
    snapshot_date=band_data["stats_extracted_at"].max().strftime("%d %b %Y"),
    follower_threshold=FOLLOWER_THRESHOLD,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_06_path)
            """
        ),
        markdown(
            f"""
### 09.02 Monthly-listener and follower ranks

{facts['monthly_top']} are the top three cities under monthly listeners. {facts['follower_top']} are the top three under followers. The rank correlation is {facts['correlation']:.2f}. London and Birmingham change position, but the three leading cities remain the same.
            """
        ),
        code(
            """
# Put monthly-listener and follower ranks on the same scale.
figure_07_path = plot_metric_rank_comparison(
    rank_comparison,
    rank_correlation,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_07_path)
            """
        ),
        markdown(
            """
### 09.03 Leading-band concentration

The Beatles account for {facts['liverpool_concentration']:.0%} of Liverpool's eligible monthly listeners. Arctic Monkeys account for {facts['sheffield_concentration']:.0%} of Sheffield's. Manchester is less concentrated: its leading band accounts for {facts['manchester_concentration']:.0%}.

Bradford shows 100% because only The Cult remains above the follower threshold.
            """
        ),
        code(
            """
# Show the leading band's share of each eligible city total.
figure_08_path = plot_top_band_concentration(
    monthly_rankings,
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_08_path)
            """
        ),
        markdown(
            """
## 10. Threshold sensitivity

The table recalculates the preferred ranking with no follower threshold and with thresholds of 100,000, 500,000 and one million.

The leading city is {facts['threshold_leaders'][0]} with no threshold, {facts['threshold_leaders'][100_000]} at 100,000 followers, {facts['threshold_leaders'][500_000]} at 500,000 and {facts['threshold_leaders'][1_000_000]} at one million. This test covers threshold choice only; it cannot account for bands omitted from the shortlist.
            """
        ),
        code(
            """
# Recalculate city rank across four follower thresholds.
sensitivity = build_threshold_sensitivity(
    band_data,
    thresholds=[0, 100_000, 500_000, 1_000_000],
    metric="monthly_listeners",
    top_n=TOP_N,
)
sensitivity_table = (
    sensitivity.pivot(index="city", columns="follower_threshold", values="rank")
    .rename(
        columns={
            0: "No threshold",
            100_000: "100k",
            500_000: "500k",
            1_000_000: "1m",
        }
    )
    .sort_values("100k")
    .reset_index()
    .rename(columns={"city": "City"})
)

display(sensitivity_table.fillna("Not eligible"))
            """
        ),
        markdown(
            f"""
## 11. Conclusions and limitations

{facts['raw_leader']} has the largest unadjusted monthly-listener total in the shortlist. {facts['adjusted_total_leader']} ranks first after adjusting all five selected bands for population. Under the preferred top-three score, the monthly-listener leaders are {facts['monthly_top']}; the follower leaders are {facts['follower_top']}.

The result applies only to the selected 50 bands. The shortlist is subjective, excludes solo artists and does not cover the whole United Kingdom. The Spotify snapshot is dated {facts['snapshot_long']}, the metrics came from {facts['metric_source']} and at least one artist match is incorrect.

A national comparison requires the broader MusicBrainz catalogue, manual review of band eligibility and origin, corrected Spotify identities and refreshed metrics.
            """
        ),
    ]

    notebook = nbf.v4.new_notebook(
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
    return notebook


def build_parser() -> argparse.ArgumentParser:
    """Return safe CLI options for publication and preview builds."""
    parser = argparse.ArgumentParser(description=__doc__)
    metrics_group = parser.add_mutually_exclusive_group()
    metrics_group.add_argument(
        "--metrics-snapshot",
        help="Snapshot timestamp, YYYY-MM-DD date, 'latest', or 'publication'",
    )
    metrics_group.add_argument(
        "--metrics-path",
        type=Path,
        help="Frozen Spotify metrics JSON to use",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Notebook path; current-data inputs default to a timestamped preview",
    )
    parser.add_argument(
        "--chart-dir",
        type=Path,
        help="Chart directory; current-data inputs default to an isolated directory",
    )
    parser.add_argument(
        "--preview-label",
        help="Reader-facing warning label for a non-publication build",
    )
    return parser


def _absolute_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _snapshot_suffix(metrics_path: Path) -> str:
    prefix = "shortlist_spotify_metrics_"
    return metrics_path.stem.removeprefix(prefix)


def main(argv: list[str] | None = None) -> None:
    """Write the archived publication or an isolated snapshot preview."""
    args = build_parser().parse_args(argv)
    if args.metrics_path:
        metrics_path = _absolute_project_path(args.metrics_path)
        is_publication_metrics = (
            metrics_path.resolve() == SHORTLIST_METRICS_PATH.resolve()
        )
        suffix = _snapshot_suffix(metrics_path)
    else:
        selected = resolve_shortlist_snapshot(
            args.metrics_snapshot or "publication"
        )
        metrics_path = selected.metrics_path
        is_publication_metrics = selected.is_publication
        suffix = selected.snapshot_id

    if args.output:
        output_path = _absolute_project_path(args.output)
    elif is_publication_metrics:
        output_path = DEFAULT_OUTPUT_PATH
    else:
        output_path = (
            PROJECT_ROOT
            / "notebooks"
            / "experiments"
            / "03_uk_bands_publication_preview.ipynb"
        )

    if args.chart_dir:
        chart_output_dir = _absolute_project_path(args.chart_dir)
    elif is_publication_metrics:
        chart_output_dir = ARCHIVED_CHART_DIR
    else:
        chart_output_dir = (
            PROJECT_ROOT / "artifacts" / "publication_previews" / suffix
        )

    preview_label = args.preview_label
    if not is_publication_metrics and preview_label is None:
        preview_label = f"Spotify snapshot {suffix}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(
        build_notebook(
            metrics_path=metrics_path,
            chart_output_dir=chart_output_dir,
            preview_label=preview_label,
        ),
        output_path,
    )
    print(output_path)


if __name__ == "__main__":
    main(sys.argv[1:])
