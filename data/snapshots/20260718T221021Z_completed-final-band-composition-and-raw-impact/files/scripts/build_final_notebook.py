#!/usr/bin/env python3
"""Build the canonical 100-band current-global-reach analysis notebook."""

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
    / "final"
    / "uk_bands_punching_above_weight.ipynb"
)
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.analysis import build_city_rankings
from python_uk_bands.dataset import load_shortlist_dataset
from python_uk_bands.scene_depth import build_primary_scene_depth_rankings
from python_uk_bands.scene_depth_snapshots import (
    SceneDepthSnapshot,
    resolve_scene_depth_snapshot,
)


FOLLOWER_THRESHOLD = 100_000
PUBLISHED_TOP_N = 3
PRIMARY_RESULT_COLUMNS = [
    "city",
    "population",
    "input_bands",
    "highest_excluded_bands",
    "all_ten_value",
    "all_ten_ratio",
    "top_excluded_value",
    "top_excluded_ratio",
    "top_band_concentration",
    "metric",
    "raw_total_rank",
    "all_ten_rank",
    "top_excluded_rank",
]


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    return nbf.v4.new_code_cell(source.strip() + "\n")


def _natural_list(values: list[str]) -> str:
    if len(values) < 2:
        return "".join(values)
    return f"{', '.join(values[:-1])} and {values[-1]}"


def _notebook_path_reference(path: Path) -> tuple[str, str]:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return str(path), f"Path({str(path)!r})"
    return relative.as_posix(), f"PROJECT_ROOT / {relative.as_posix()!r}"


def build_facts(snapshot: SceneDepthSnapshot) -> dict:
    bands = pd.read_csv(snapshot.metrics_path)
    rankings = build_primary_scene_depth_rankings(
        bands,
        metric="monthly_listeners",
        expected_cities=10,
        bands_per_city=10,
    )
    saved = pd.read_csv(snapshot.rankings_path)
    saved_primary = saved.rename(
        columns={
            "untrimmed_value": "all_ten_value",
            "untrimmed_ratio": "all_ten_ratio",
            "untrimmed_rank": "all_ten_rank",
        }
    )
    saved_primary["raw_total_rank"] = (
        saved_primary["all_ten_value"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    assert_frame_equal(
        rankings[PRIMARY_RESULT_COLUMNS].sort_values("city").reset_index(
            drop=True
        ),
        saved_primary[PRIMARY_RESULT_COLUMNS].sort_values("city").reset_index(
            drop=True
        ),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )

    published_bands = load_shortlist_dataset()
    published_eligible = published_bands.loc[
        published_bands["followers"] >= FOLLOWER_THRESHOLD
    ]
    published = build_city_rankings(
        published_eligible,
        metric="monthly_listeners",
        top_n=PUBLISHED_TOP_N,
    )

    all_ten_top = (
        rankings.sort_values("all_ten_rank").head(3)["city"].tolist()
    )
    raw_top = (
        rankings.sort_values("raw_total_rank").head(3)["city"].tolist()
    )
    top_excluded_top = (
        rankings.sort_values("top_excluded_rank").head(3)["city"].tolist()
    )
    published_top = published.sort_values("rank").head(3)["city"].tolist()
    by_city = rankings.set_index("city")

    return {
        "snapshot_date": pd.to_datetime(bands["stats_extracted_at"]).max(),
        "published_top": _natural_list(published_top),
        "raw_top": _natural_list(raw_top),
        "all_ten_top": _natural_list(all_ten_top),
        "top_excluded_top": _natural_list(top_excluded_top),
        "manchester_all_rank": int(by_city.loc["Manchester", "all_ten_rank"]),
        "manchester_excluded_rank": int(
            by_city.loc["Manchester", "top_excluded_rank"]
        ),
        "sheffield_all_rank": int(by_city.loc["Sheffield", "all_ten_rank"]),
        "sheffield_excluded_rank": int(
            by_city.loc["Sheffield", "top_excluded_rank"]
        ),
        "liverpool_all_rank": int(by_city.loc["Liverpool", "all_ten_rank"]),
        "liverpool_excluded_rank": int(
            by_city.loc["Liverpool", "top_excluded_rank"]
        ),
        "liverpool_concentration": by_city.loc[
            "Liverpool", "top_band_concentration"
        ],
        "sheffield_concentration": by_city.loc[
            "Sheffield", "top_band_concentration"
        ],
        "manchester_concentration": by_city.loc[
            "Manchester", "top_band_concentration"
        ],
        "medium_origin_rows": int(bands["origin_confidence"].eq("medium").sum()),
        "review_rows": int(bands["editorial_review_flag"].sum()),
    }


def build_notebook(
    snapshot: SceneDepthSnapshot,
    *,
    chart_output_dir: Path,
):
    facts = build_facts(snapshot)
    snapshot_long = facts["snapshot_date"].strftime("%d %B %Y")
    snapshot_short = facts["snapshot_date"].strftime("%d %b %Y")
    metrics_display, metrics_reference = _notebook_path_reference(
        snapshot.metrics_path
    )
    rankings_display, rankings_reference = _notebook_path_reference(
        snapshot.rankings_path
    )
    chart_display, chart_reference = _notebook_path_reference(chart_output_dir)

    cells = [
        markdown(
            f"""
# Current global Spotify reach and scene depth: ten bands per British built-up area

## tl;dr

This notebook asks two related questions about a fixed panel of ten British
built-up areas:

1. Which areas have the greatest current global Spotify monthly-listener reach
   across ten selected bands, relative to population?
2. Which results remain strong after reducing the influence of a single
   exceptionally popular band?

Before population normalization, {facts['raw_top']} have the largest combined
reach across the selected catalogue. After dividing the same ten-band totals
by population, {facts['all_ten_top']} lead. The largest selected band supplies
{facts['liverpool_concentration']:.0%} of Liverpool's reach and
{facts['sheffield_concentration']:.0%} of Sheffield's, compared with
{facts['manchester_concentration']:.0%} in Manchester. After each area's
largest band is removed, the leading order becomes {facts['top_excluded_top']}.

The primary result is the all-ten population-normalized ranking. Removing the
largest band is a separate scene-depth test: Manchester and Sheffield retain
comparatively broad reach across the selected catalogue, while Liverpool's
position is more dependent on the Beatles.

> **Scope:** “Reach” means current global Spotify monthly listeners captured on
> {snapshot_long}. It is not historical or cultural impact, record sales,
> influence, live audiences, or listening by local residents.
            """
        ),
        markdown(
            """
## 01. Study question and design

The unit of analysis is a **built-up area**. The study uses a fixed panel of ten
areas and a balanced catalogue of ten bands per area, giving 100 bands in
total. The panel is inherited from the project's original shortlist; it is not
presented as the ten largest urban areas or as a census of every British city.

An act is assigned to the area where the band formed, not to the birthplace of
an individual member. Solo artists are outside scope. The catalogue combines
the reviewed original shortlist with manually reviewed additions and
replacements. MusicBrainz helped with candidate discovery and identity
resolution, but origin evidence and editorial flags remain attached to every
row.

Using exactly ten bands per area prevents one area from receiving a larger
total merely because more acts were selected. The notebook first shows the
unnormalized scale, then one primary result and one sensitivity test:

| Stage | Calculation | Question answered |
|---|---|---|
| Descriptive context | Sum all ten bands | Which selected city catalogues have the largest absolute current reach? |
| Primary: all ten | Sum all ten bands, then divide by population | How large is the selected catalogue's current reach relative to area size? |
| Scene depth | Remove the largest band, sum the remaining nine, then divide by population | Does the result survive without its dominant act? |

The raw total provides scale but structurally favours larger cities. The
all-ten population-normalized measure is the headline result. The
largest-band-excluded measure is reported afterwards as a scene-depth
sensitivity test, not as a replacement ranking.
            """
        ),
        markdown(
            f"""
## 02. Data and definitions

The analysis uses snapshot **`{snapshot.snapshot_id}`**, captured on
**{snapshot_long}**. Notebook execution is offline: it reads frozen local files
and cannot silently refresh the Spotify values.

### Band catalogue

- `reference/scene_depth_bands.csv` contains the 100 reviewed band–origin
  assignments.
- Every area contributes exactly ten bands.
- There is no follower threshold.
- Spotify artist IDs and names are checked before metrics enter the analysis.
- Origin evidence, confidence, selection source, and review flags remain in the
  catalogue for audit.

### Reach metric

`{metrics_display}` contains the frozen Spotify artist identities and monthly
listeners. Monthly listeners are a current, global platform-reach measure. A
listener can count toward a band's total regardless of where that listener
lives.

### Population denominator

Population comes from `reference/built_up_areas.csv`, using 2021 built-up-area
figures from ONS for England and the 2021 Scotland Census for Glasgow. Dividing
global reach by local population is a size normalization; it is **not** a local
listening rate.

### Saved result

`{rankings_display}` stores the calculated city rankings. The notebook
recomputes every measure from band-level data and checks the result against this
saved file before displaying any findings.
            """
        ),
        markdown(
            f"""
## 03. Calculation and assumptions

For area \\(c\\), let \\(L_{{ic}}\\) be band \\(i\\)'s monthly listeners and \\(P_c\\)
the 2021 built-up-area population:

- **Raw total:** \\(\\sum_{{i=1}}^{{10}} L_{{ic}}\\)
- **Population-normalized all ten:** \\(\\sum_{{i=1}}^{{10}} L_{{ic}} / P_c\\)
- **Largest excluded:** \\((\\sum L_{{ic}} - \\max L_{{ic}}) / P_c\\)

The raw and primary formulas use exactly the same ten bands; only the
population denominator changes. The third formula removes only the observation
most capable of overwhelming the total while retaining nine bands per area.

### Key assumptions

- The fixed city panel is analytically useful but is not a complete or
  population-selected universe of British cities.
- The balanced catalogue is manually curated, genre-influenced, and not a
  random sample of bands.
- Formation place is a defensible working definition of origin, but some bands
  have ambiguous or multi-place histories.
- Spotify monthly listeners measure current global platform reach. They do not measure historical or cultural impact, and they are not listening by local residents.
- Population is a normalization denominator, not an estimate of each band's local audience.
- Largest-band exclusion reduces sensitivity to one extreme but cannot correct
  catalogue-selection bias.

The following cells validate the 100-by-10 design, identity matches, snapshot
consistency, population values, and saved calculations before the results are
shown.
            """
        ),
        code(
            """
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
    build_primary_scene_depth_rankings,
    validate_scene_depth_dataset,
)
from python_uk_bands.scene_depth_visuals import (
    plot_raw_city_totals,
    plot_raw_normalized_scene_depth_rank_comparison,
    plot_ten_band_city_stack,
    plot_ten_band_population_normalized_total,
)
from python_uk_bands.visuals import apply_chart_style

apply_chart_style()
            """
        ),
        code(
            f"""
SNAPSHOT_ID = "{snapshot.snapshot_id}"
CATALOG_PATH = PROJECT_ROOT / "reference" / "scene_depth_bands.csv"
METRICS_PATH = {metrics_reference}
SAVED_RANKINGS_PATH = {rankings_reference}
CHART_OUTPUT_DIR = {chart_reference}

catalog = pd.read_csv(CATALOG_PATH, keep_default_na=False)
band_data = pd.read_csv(METRICS_PATH)
saved_rankings = pd.read_csv(SAVED_RANKINGS_PATH)

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
    {{
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
    }}
)
display(quality_summary)
            """
        ),
        code(
            """
# Recalculate the two published metrics from band-level data and verify the
# corresponding columns against the complete frozen pipeline result.
rankings = build_primary_scene_depth_rankings(
    band_data,
    metric="monthly_listeners",
    expected_cities=10,
    bands_per_city=10,
)
primary_result_columns = [
    "city",
    "population",
    "input_bands",
    "highest_excluded_bands",
    "all_ten_value",
    "all_ten_ratio",
    "top_excluded_value",
    "top_excluded_ratio",
    "top_band_concentration",
    "metric",
    "raw_total_rank",
    "all_ten_rank",
    "top_excluded_rank",
]
saved_primary_rankings = saved_rankings.rename(
    columns={
        "untrimmed_value": "all_ten_value",
        "untrimmed_ratio": "all_ten_ratio",
        "untrimmed_rank": "all_ten_rank",
    }
)
saved_primary_rankings["raw_total_rank"] = (
    saved_primary_rankings["all_ten_value"]
    .rank(method="min", ascending=False)
    .astype(int)
)
assert_frame_equal(
    rankings[primary_result_columns].sort_values("city").reset_index(drop=True),
    saved_primary_rankings[primary_result_columns]
    .sort_values("city")
    .reset_index(drop=True),
    check_exact=False,
    rtol=1e-12,
    atol=1e-12,
)
            """
        ),
        markdown(
            f"""
## 04. From bands to city impact

The analysis starts at band level, then aggregates those same bands into raw
city totals before applying the population denominator.

### 04.01 Band contributions to city totals

Each horizontal bar contains all ten selected bands for one city. Segment 1 is
that city's largest current act, segment 2 its second largest, and so on. The
two-line key names every band.
            """
        ),
        code(
            f"""
figure_01_path = plot_ten_band_city_stack(
    band_data,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=1,
    filename="chart_01_city_band_stack.png",
)
display_path(figure_01_path)
            """
        ),
        markdown(
            f"""
### 04.02 Most impactful cities before population normalization

With the ten selected bands simply added together, {facts['raw_top']} have the
largest absolute current reach. This view describes catalogue scale without
accounting for population; it is context for the primary result rather than
the study's answer to “punching above weight.”
            """
        ),
        code(
            """
raw_city_table = rankings[
    [
        "raw_total_rank",
        "city",
        "all_ten_value",
        "population",
        "all_ten_rank",
    ]
].sort_values("raw_total_rank").rename(
    columns={
        "raw_total_rank": "Raw rank",
        "city": "City",
        "all_ten_value": "Combined current global monthly listeners",
        "population": "Built-up-area population",
        "all_ten_rank": "Population-normalized rank",
    }
)
display(raw_city_table)
            """
        ),
        code(
            f"""
figure_02_path = plot_raw_city_totals(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=2,
    filename="chart_02_raw_city_totals.png",
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
### 04.03 Primary result: population-normalized reach

After the same all-ten totals are divided by built-up-area population,
{facts['all_ten_top']} lead.

This is the study's primary result: how much current global Spotify
monthly-listener reach is represented by all ten selected bands relative to
city population. No band has been removed from this ranking.
            """
        ),
        code(
            """
all_ten_table = rankings[
    [
        "all_ten_rank",
        "city",
        "all_ten_ratio",
        "highest_excluded_bands",
        "top_band_concentration",
    ]
].sort_values("all_ten_rank").rename(
    columns={
        "all_ten_rank": "Rank",
        "city": "City",
        "all_ten_ratio": "Current global ten-band reach / population",
        "highest_excluded_bands": "Largest selected band",
        "top_band_concentration": "Largest-band share",
    }
)
display(all_ten_table)
            """
        ),
        code(
            f"""
figure_03_path = plot_ten_band_population_normalized_total(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=3,
    filename="chart_03_population_normalized_total.png",
)
display_path(figure_03_path)
            """
        ),
        markdown(
            f"""
## 05. Why test scene depth?

A city can rank highly because several bands contribute meaningful current
global Spotify reach, or because one act dominates the total. The stacked chart
makes that concentration visible before anything is removed.

The Beatles supply {facts['liverpool_concentration']:.1%} of Liverpool's
selected total. Arctic Monkeys supply
{facts['sheffield_concentration']:.1%} of Sheffield's. Manchester is less
concentrated: its largest selected band supplies
{facts['manchester_concentration']:.1%}.

This motivates the scene-depth test. The question is not whether those bands
“count”; clearly they do in the primary result. The additional test asks
whether the city still looks strong without allowing one current superstar to
determine most of its position.
            """
        ),
        markdown(
            f"""
## 06. Scene-depth test: remove the largest band

After each area's largest selected band is removed,
{facts['top_excluded_top']} lead. Manchester moves from rank
{facts['manchester_all_rank']} to {facts['manchester_excluded_rank']};
Sheffield moves from {facts['sheffield_all_rank']} to
{facts['sheffield_excluded_rank']} even without Arctic Monkeys; Liverpool moves
from {facts['liverpool_all_rank']} to {facts['liverpool_excluded_rank']} without
the Beatles.

This is the notebook's only alternative ranking. It retains nine bands per city
and changes only the observation most capable of overwhelming the total.
            """
        ),
        code(
            """
largest_excluded_table = rankings[
    [
        "top_excluded_rank",
        "city",
        "top_excluded_ratio",
        "highest_excluded_bands",
        "all_ten_rank",
    ]
].copy()
largest_excluded_table["rank_change"] = (
    largest_excluded_table["all_ten_rank"]
    - largest_excluded_table["top_excluded_rank"]
)
display(
    largest_excluded_table.sort_values("top_excluded_rank").rename(
        columns={
            "top_excluded_rank": "Rank",
            "city": "City",
            "top_excluded_ratio": "Current global other-nine reach / population",
            "highest_excluded_bands": "Band removed",
            "all_ten_rank": "All-ten rank",
            "rank_change": "Places gained",
        }
    )
)
            """
        ),
        markdown(
            """
## 07. Raw, normalized and scene-depth rankings

The final chart puts the three views on one rank scale: absolute catalogue
impact, the population-normalized primary result, and the single scene-depth
sensitivity. It summarizes the methodological progression rather than adding
another scoring method.
            """
        ),
        code(
            f"""
figure_04_path = plot_raw_normalized_scene_depth_rank_comparison(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=4,
    filename="chart_04_raw_normalized_scene_depth_ranks.png",
)
display_path(figure_04_path)
            """
        ),
        markdown(
            f"""
## 08. Findings

Within this fixed ten-area, 100-band catalogue:

- **Raw all-ten totals:** {facts['raw_top']} have the largest absolute selected
  reach before population normalization.
- **Primary all-ten result:** {facts['all_ten_top']} have the greatest selected
  reach relative to population.
- **Superstar concentration:** the largest band supplies
  {facts['liverpool_concentration']:.1%} of Liverpool's selected reach,
  {facts['sheffield_concentration']:.1%} of Sheffield's, and
  {facts['manchester_concentration']:.1%} of Manchester's.
- **Largest band excluded:** Manchester ranks
  {facts['manchester_excluded_rank']}, Sheffield
  {facts['sheffield_excluded_rank']}, and Liverpool
  {facts['liverpool_excluded_rank']}.

The primary and sensitivity results answer different questions. The headline
finding remains the all-ten population-normalized ranking. The scene-depth test
adds that Liverpool's relative position is more dependent on one band, while
Manchester and Sheffield remain strong after their dominant acts are removed.
            """
        ),
        markdown(
            f"""

## 09. Limitations

- The ten built-up areas form a fixed project panel, not a population-selected
  universe of British cities.
- The catalogue is manually curated, excludes solo artists, reflects the
  project's genre lane, and is not a random sample. Largest-band exclusion
  cannot remove this selection bias.
- {facts['medium_origin_rows']} origin assignments are medium confidence, and
  {facts['review_rows']} rows remain flagged for editorial review.
- Monthly listeners are volatile global Spotify reach, observed on one
  snapshot date. They do not measure historical impact or local listening.
- Dividing by built-up-area population is a normalization device. It does not
  imply that the listeners live in that area.
- The raw city-total view describes absolute reach in this selected catalogue;
  it does not account for city size and is not the headline ranking.
- The largest-band test describes sensitivity within ten selected bands. A
  different credible catalogue could produce a different order.

The supported conclusion is deliberately narrow: **the primary result ranks
the full selected catalogue relative to population; the additional
largest-band test shows that Manchester and Sheffield retain comparatively
strong reach beyond their largest act, while Liverpool's rank is more
superstar-dependent.** This is not a definitive ranking of British music
scenes or musical importance.

Charts are saved under `{chart_display}`.
            """
        ),
        markdown(
            """

## Appendix A. Relationship to the earlier five-band publication

The earlier publication is useful as project history, not as part of the main
estimator. It used five bands per area, a follower threshold, and an older data
snapshot. The table below keeps that result visible without asking the reader
to understand it before the current method.
            """
        ),
        code(
            """
# Keep the original five-band result visible as context, not as a direct equivalent.
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

method_comparison = (
    published_rankings[["city", "rank"]]
    .rename(columns={"rank": "published_five_band_rank"})
    .merge(
        rankings[
            [
                "city",
                "raw_total_rank",
                "all_ten_rank",
                "top_excluded_rank",
            ]
        ],
        on="city",
        validate="one_to_one",
    )
    .sort_values("all_ten_rank")
)
display(
    method_comparison.rename(
        columns={
            "city": "City",
            "published_five_band_rank": "Published five-band rank",
            "raw_total_rank": "Raw all-ten rank",
            "all_ten_rank": "All-ten rank",
            "top_excluded_rank": "Largest-excluded rank",
        }
    )
)
            """
        ),
        markdown(
            f"""
The five-band and all-ten views happen to identify the same leading cluster:
{facts['published_top']}. Their ranks should not be interpreted as a clean
before-and-after comparison because the catalogue, eligibility rule, and
snapshot all changed.
            """
        ),
        markdown(
            """

## Appendix B. Useful dead ends

These routes shaped the final method, but they are process history rather than
onboarding material.

### Google Trends

Google Trends looked like a common popularity measure, but each request is
sampled and normalized to its own peak. Comparing many bands required batches
and anchor acts; changing the anchors or time window could change the apparent
city totals. The charts were possible, but the cross-band comparison was not
defensible.

### MusicBrainz as an automatic catalogue

MusicBrainz widened the candidate pool and helped resolve identities. It could
not decide the study's editorial questions: what counts as a band, where an act
formed, how ambiguous names should be handled, or where the genre boundary
sits. It became discovery and evidence infrastructure rather than an automatic
sampling frame.

### The first 50-band design

The earlier five-band-per-area version used a follower threshold and an older
Spotify snapshot. The threshold created uneven eligibility, and the saved data
contained one known artist mismatch. Those problems motivated reviewed Spotify
IDs, a balanced ten-band catalogue, no follower threshold, and the explicit
concentration tests used here.

The underlying work remains preserved in the
[Google Trends archive](../archive/google-trends/README.md), the
[original scratchpad](../archive/original-analysis/python_uk_bands.ipynb), and
the [first published notebook](../archive/published-v1/uk_bands_punching_above_weight.ipynb).
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        default="latest",
        help="Scene-depth snapshot timestamp, YYYY-MM-DD date, or 'latest'",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--chart-dir", type=Path)
    return parser


def _absolute_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    snapshot = resolve_scene_depth_snapshot(args.snapshot)
    output_path = (
        _absolute_project_path(args.output)
        if args.output
        else DEFAULT_OUTPUT_PATH
    )
    chart_output_dir = (
        _absolute_project_path(args.chart_dir)
        if args.chart_dir
        else PROJECT_ROOT / "artifacts" / "charts"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(
        build_notebook(snapshot, chart_output_dir=chart_output_dir),
        output_path,
    )
    print(output_path)


if __name__ == "__main__":
    main(sys.argv[1:])
