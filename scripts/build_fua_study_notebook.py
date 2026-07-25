#!/usr/bin/env python3
"""Build the shared top-10/top-20 FUA current-reach notebook narrative."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import nbformat as nbf
import pandas as pd
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.scene_depth import build_primary_scene_depth_rankings


FUA_DEFINITION_URL = (
    "https://www.oecd.org/en/data/datasets/"
    "oecd-definition-of-cities-and-functional-urban-areas.html"
)
FUA_DATASET_URL = (
    "https://data-explorer.oecd.org/vis?"
    "df%5Bag%5D=OECD.CFE.EDS&"
    "df%5Bds%5D=dsDisseminateFinalDMZ&"
    "df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en"
)
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


@dataclass(frozen=True)
class FuaStudySnapshot:
    snapshot_id: str
    city_count: int
    metrics_path: Path
    rankings_path: Path
    universe_path: Path


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    return nbf.v4.new_code_cell(source.strip() + "\n")


def _natural_list(values: list[str]) -> str:
    if len(values) < 2:
        return "".join(values)
    return f"{', '.join(values[:-1])} and {values[-1]}"


def _project_reference(path: Path) -> tuple[str, str]:
    relative = path.resolve().relative_to(PROJECT_ROOT)
    return relative.as_posix(), f"PROJECT_ROOT / {relative.as_posix()!r}"


def _city_word(city_count: int) -> str:
    return {10: "ten", 20: "twenty"}[city_count]


def resolve_fua_study_snapshot(
    *,
    city_count: int,
    selector: str,
) -> FuaStudySnapshot:
    prefix = f"fua_top{city_count}_band_metrics_"
    complete: list[str] = []
    for metrics_path in (PROJECT_ROOT / "data" / "processed").glob(
        f"{prefix}*.csv"
    ):
        snapshot_id = metrics_path.stem.removeprefix(prefix)
        rankings_path = (
            PROJECT_ROOT
            / "data"
            / "processed"
            / f"fua_top{city_count}_rankings_{snapshot_id}.csv"
        )
        if re.fullmatch(r"\d{8}T\d{6}Z", snapshot_id) and rankings_path.exists():
            complete.append(snapshot_id)
    complete = sorted(complete)
    if not complete:
        raise FileNotFoundError(
            f"No complete frozen top-{city_count} FUA study inputs exist"
        )

    if selector == "latest":
        snapshot_id = complete[-1]
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", selector):
        prefix_date = selector.replace("-", "")
        matches = [value for value in complete if value.startswith(prefix_date)]
        if not matches:
            raise FileNotFoundError(
                f"No top-{city_count} FUA snapshot exists for {selector}"
            )
        snapshot_id = matches[-1]
    elif selector in complete:
        snapshot_id = selector
    else:
        raise FileNotFoundError(
            f"Unknown top-{city_count} FUA snapshot {selector!r}; "
            f"available: {', '.join(complete)}"
        )

    processed = PROJECT_ROOT / "data" / "processed"
    return FuaStudySnapshot(
        snapshot_id=snapshot_id,
        city_count=city_count,
        metrics_path=processed
        / f"fua_top{city_count}_band_metrics_{snapshot_id}.csv",
        rankings_path=processed
        / f"fua_top{city_count}_rankings_{snapshot_id}.csv",
        universe_path=PROJECT_ROOT / "reference" / "uk_fua_top20_2021.csv",
    )


def build_facts(snapshot: FuaStudySnapshot) -> dict:
    bands = pd.read_csv(snapshot.metrics_path, keep_default_na=False)
    rankings = build_primary_scene_depth_rankings(
        bands,
        metric="monthly_listeners",
        expected_cities=snapshot.city_count,
        bands_per_city=10,
    )
    saved = pd.read_csv(snapshot.rankings_path)
    assert_frame_equal(
        rankings[PRIMARY_RESULT_COLUMNS].sort_values("city").reset_index(
            drop=True
        ),
        saved[PRIMARY_RESULT_COLUMNS].sort_values("city").reset_index(
            drop=True
        ),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    by_city = rankings.set_index("city")
    return {
        "snapshot_date": pd.to_datetime(
            bands["stats_extracted_at_utc"]
        ).max(),
        "raw_top": _natural_list(
            rankings.sort_values("raw_total_rank").head(3)["city"].tolist()
        ),
        "all_ten_top": _natural_list(
            rankings.sort_values("all_ten_rank").head(3)["city"].tolist()
        ),
        "all_ten_top_ten": _natural_list(
            rankings.sort_values("all_ten_rank").head(10)["city"].tolist()
        ),
        "top_excluded_top": _natural_list(
            rankings.sort_values("top_excluded_rank")
            .head(3)["city"]
            .tolist()
        ),
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
        "liverpool_concentration": float(
            by_city.loc["Liverpool", "top_band_concentration"]
        ),
        "sheffield_concentration": float(
            by_city.loc["Sheffield", "top_band_concentration"]
        ),
        "manchester_concentration": float(
            by_city.loc["Manchester", "top_band_concentration"]
        ),
        "low_confidence_rows": int(
            bands["origin_confidence"].eq("low").sum()
        ),
        "review_required_rows": int(
            bands["origin_alignment"].eq("review_required").sum()
        ),
    }


def build_notebook(
    snapshot: FuaStudySnapshot,
    *,
    chart_output_dir: Path,
    experiment: bool,
):
    city_count = snapshot.city_count
    city_word = _city_word(city_count)
    total_bands = city_count * 10
    facts = build_facts(snapshot)
    snapshot_long = facts["snapshot_date"].strftime("%d %B %Y")
    snapshot_short = facts["snapshot_date"].strftime("%d %b %Y")
    metrics_display, metrics_reference = _project_reference(
        snapshot.metrics_path
    )
    rankings_display, rankings_reference = _project_reference(
        snapshot.rankings_path
    )
    universe_display, universe_reference = _project_reference(
        snapshot.universe_path
    )
    chart_display, chart_reference = _project_reference(chart_output_dir)
    experiment_note = (
        "\n> **Experiment:** This notebook mirrors the final top-ten method while "
        "expanding the population-selected universe to twenty FUAs. It does not "
        "replace the final notebook.\n"
        if experiment
        else ""
    )
    scope_label = f"the {city_word} largest UK Functional Urban Areas"
    top_ten_finding = (
        f"- **Primary top ten:** {facts['all_ten_top_ten']}.\n"
        if city_count == 20
        else ""
    )

    cells = [
        markdown(
            f"""
# Current global Spotify reach and scene depth across {scope_label}
{experiment_note}
## tl;dr

This notebook asks two related questions about {scope_label}:

1. Which FUAs have the greatest current global Spotify monthly-listener reach
   across ten selected bands, relative to population?
2. Which results remain strong after reducing the influence of one
   exceptionally popular band?

Before population normalization, {facts['raw_top']} have the largest combined
reach. After dividing those same ten-band totals by FUA population,
{facts['all_ten_top']} lead. The largest selected band supplies
{facts['liverpool_concentration']:.0%} of Liverpool's reach and
{facts['sheffield_concentration']:.0%} of Sheffield's, compared with
{facts['manchester_concentration']:.0%} in Manchester. After each FUA's largest
band is removed, the leading order becomes {facts['top_excluded_top']}.

The primary result is the all-ten population-normalized ranking. Removing the
largest band is a separate scene-depth test.

> **Scope:** “Reach” means current global Spotify monthly listeners captured on
> {snapshot_long}. Conclusions apply to {scope_label}, not every UK city, and
> do not measure historical importance or local listening.
            """
        ),
        markdown(
            f"""
## 01. Study question and design

The unit of analysis is an **OECD/EU Functional Urban Area (FUA)**: an urban
centre plus the surrounding places connected to it through commuting. The
study begins with {scope_label}, ranked by the OECD's 2021 population
observations, then assigns ten reviewed bands to each FUA. This produces a
balanced catalogue of {total_bands} bands.

An act is assigned to the FUA where the band formed. Solo artists are outside
scope. Exactly ten bands per FUA prevents one area from receiving a larger
total merely because more acts were selected.

| Stage | Calculation | Question answered |
|---|---|---|
| Descriptive context | Sum all ten bands | Which selected FUA catalogues have the largest absolute current reach? |
| Primary: all ten | Sum all ten bands, then divide by FUA population | How large is selected current reach relative to area size? |
| Scene depth | Remove the largest band, sum the remaining nine, then divide by FUA population | Does the result survive without its dominant act? |

The raw total provides scale but structurally favours larger areas. The
all-ten population-normalized measure is the headline result. Largest-band
exclusion is a sensitivity test, not a replacement ranking.
            """
        ),
        markdown(
            f"""
## 02. Data and definitions

The analysis uses frozen Spotify snapshot **`{snapshot.snapshot_id}`**, captured
on **{snapshot_long}**. Notebook execution is offline and cannot silently
refresh the values.

### Functional Urban Area universe

`{universe_display}` freezes the 2021 population universe and the official FUA
codes used here.

- [OECD definition of cities and Functional Urban Areas]({FUA_DEFINITION_URL})
- [OECD Data Explorer: Population by age and sex — Cities and FUAs]({FUA_DATASET_URL})

The EU–OECD definition uses population density to identify urban centres and
commuting flows to add economically connected surrounding areas. That makes
the denominator consistent across England, Scotland, Wales and Northern
Ireland.

### Band catalogue and reach metric

`{metrics_display}` contains the {total_bands} reviewed band–FUA assignments,
Spotify identities, FUA population fields, and frozen monthly listeners. Every
FUA contributes exactly ten bands. Monthly listeners are current global
platform reach; they are not listeners living in the FUA.

### Saved result

`{rankings_display}` stores the raw, population-normalized, and largest-band-
excluded rankings. The notebook recomputes them from band-level data and checks
them against the saved file before showing findings.
            """
        ),
        markdown(
            f"""
## 03. Calculation and assumptions

For FUA \\(c\\), let \\(L_{{ic}}\\) be band \\(i\\)'s monthly listeners and
\\(P_c\\) its 2021 OECD FUA population:

- **Raw total:** \\(\\sum_{{i=1}}^{{10}} L_{{ic}}\\)
- **Population-normalized all ten:** \\(\\sum_{{i=1}}^{{10}} L_{{ic}} / P_c\\)
- **Largest excluded:** \\((\\sum L_{{ic}} - \\max L_{{ic}}) / P_c\\)

### Key assumptions

- The population-selected universe supports conclusions about {scope_label},
  not every UK city.
- The balanced catalogue is manually curated, genre-influenced, and not a
  random sample of bands.
- Formation place is the working definition of origin. Some assignments within
  a wider FUA require editorial judgement.
- Spotify monthly listeners measure current global reach, not cultural impact,
  record sales, or local listening.
- FUA population is a size denominator, not an estimate of local audience.
- Largest-band exclusion reduces sensitivity to one extreme but cannot remove
  catalogue-selection bias.

The following cells validate the {total_bands}-by-{city_count} design, FUA
mapping, Spotify identities, capture consistency, population values, and saved
calculations.
            """
        ),
        code(
            f"""
from pathlib import Path
import sys

import pandas as pd
from pandas.testing import assert_frame_equal
from IPython.display import display


def find_project_root() -> Path:
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "reference" / "uk_fua_top20_2021.csv").exists():
            return candidate
    raise FileNotFoundError(
        "Run this notebook from inside the uk-music-cities repository"
    )


PROJECT_ROOT = find_project_root()
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


from python_uk_bands.fua import validate_top_fua_universe
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
EXPECTED_CITIES = {city_count}
BANDS_PER_CITY = 10
METRICS_PATH = {metrics_reference}
SAVED_RANKINGS_PATH = {rankings_reference}
FUA_UNIVERSE_PATH = {universe_reference}
CHART_OUTPUT_DIR = {chart_reference}

band_data = pd.read_csv(METRICS_PATH, keep_default_na=False)
saved_rankings = pd.read_csv(SAVED_RANKINGS_PATH)
fua_universe = pd.read_csv(FUA_UNIVERSE_PATH, keep_default_na=False).head(
    EXPECTED_CITIES
)

validate_scene_depth_dataset(
    band_data,
    expected_cities=EXPECTED_CITIES,
    bands_per_city=BANDS_PER_CITY,
)
validate_top_fua_universe(
    fua_universe,
    expected_rows=EXPECTED_CITIES,
    year=2021,
)
assert len(band_data) == EXPECTED_CITIES * BANDS_PER_CITY
assert band_data["band"].nunique() == len(band_data)
assert band_data["spotify_id"].nunique() == len(band_data)
assert band_data["catalogue_review_ready"].astype(bool).all()
assert band_data["monthly_listeners"].ge(0).all()
assert band_data["stats_extracted_at_utc"].nunique() == 1

observed_population = (
    band_data[
        [
            "uk_population_rank",
            "fua_code",
            "city",
            "population_year",
            "population",
        ]
    ]
    .drop_duplicates()
    .sort_values("uk_population_rank")
    .reset_index(drop=True)
)
expected_population = (
    fua_universe[
        [
            "uk_population_rank",
            "fua_code",
            "study_city_label",
            "population_year",
            "population",
        ]
    ]
    .rename(columns={{"study_city_label": "city"}})
    .reset_index(drop=True)
)
assert_frame_equal(
    observed_population,
    expected_population,
    check_dtype=False,
)

quality_summary = pd.DataFrame(
    {{
        "Check": [
            "Bands",
            "FUAs",
            "Bands per FUA",
            "Unique Spotify identities",
            "Reviewed catalogue rows",
            "Low-confidence origin rows",
        ],
        "Value": [
            len(band_data),
            band_data["city"].nunique(),
            int(band_data.groupby("city").size().min()),
            band_data["spotify_id"].nunique(),
            int(band_data["catalogue_review_ready"].astype(bool).sum()),
            int(band_data["origin_confidence"].eq("low").sum()),
        ],
    }}
)
display(quality_summary)
            """
        ),
        code(
            f"""
rankings = build_primary_scene_depth_rankings(
    band_data,
    metric="monthly_listeners",
    expected_cities=EXPECTED_CITIES,
    bands_per_city=BANDS_PER_CITY,
)
primary_result_columns = {PRIMARY_RESULT_COLUMNS!r}
assert_frame_equal(
    rankings[primary_result_columns].sort_values("city").reset_index(drop=True),
    saved_rankings[primary_result_columns]
    .sort_values("city")
    .reset_index(drop=True),
    check_exact=False,
    rtol=1e-12,
    atol=1e-12,
)
            """
        ),
        markdown(
            """
## 04. From bands to FUA impact

### 04.01 Band contributions to FUA totals

Each equal-length bar contains all ten selected bands for one FUA and totals
100%. Segment 1 is that area's largest current act, segment 2 its second
largest, and so on. The key names every band. This isolates composition and
concentration; the next chart restores absolute totals.
            """
        ),
        code(
            f"""
figure_01_path = plot_ten_band_city_stack(
    band_data,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=1,
    filename="chart_01_fua_band_share_stack.png",
)
display_path(figure_01_path)
            """
        ),
        markdown(
            f"""
### 04.02 Most impactful FUAs before population normalization

With the ten selected bands simply added together, {facts['raw_top']} have the
largest absolute current reach. This is catalogue scale, not the answer to
which area “punches above its weight.”
            """
        ),
        code(
            """
raw_fua_table = rankings[
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
        "city": "FUA",
        "all_ten_value": "Combined current global monthly listeners",
        "population": "2021 OECD FUA population",
        "all_ten_rank": "Population-normalized rank",
    }
)
display(raw_fua_table)
            """
        ),
        code(
            f"""
figure_02_path = plot_raw_city_totals(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=2,
    filename="chart_02_raw_fua_totals.png",
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
### 04.03 Primary result: FUA-population-normalized reach

After the same all-ten totals are divided by 2021 OECD FUA population,
{facts['all_ten_top']} lead. No band has been removed from this primary ranking.
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
        "city": "FUA",
        "all_ten_ratio": "Current global ten-band reach / FUA population",
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
    filename="chart_03_fua_population_normalized_total.png",
    denominator_description="2021 OECD FUA population denominator",
)
display_path(figure_03_path)
            """
        ),
        markdown(
            f"""
## 05. Why test scene depth?

The 100% chart shows whether one act dominates a selected FUA catalogue. The
Beatles supply {facts['liverpool_concentration']:.1%} of Liverpool's total;
Arctic Monkeys supply {facts['sheffield_concentration']:.1%} of Sheffield's;
Manchester's largest selected band supplies
{facts['manchester_concentration']:.1%}.

Those bands remain fully included in the primary result. The additional test
asks whether an FUA still looks strong after its single largest act is removed.
            """
        ),
        markdown(
            f"""
## 06. Scene-depth test: remove the largest band

After each FUA's largest selected band is removed,
{facts['top_excluded_top']} lead. Manchester moves from rank
{facts['manchester_all_rank']} to {facts['manchester_excluded_rank']};
Sheffield moves from {facts['sheffield_all_rank']} to
{facts['sheffield_excluded_rank']}; Liverpool moves from
{facts['liverpool_all_rank']} to {facts['liverpool_excluded_rank']}.

This is the notebook's only alternative ranking. It retains nine bands per FUA.
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
            "city": "FUA",
            "top_excluded_ratio": "Current global other-nine reach / FUA population",
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
impact, the FUA-population-normalized primary result, and the largest-band-
excluded sensitivity.
            """
        ),
        code(
            f"""
figure_04_path = plot_raw_normalized_scene_depth_rank_comparison(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=4,
    filename="chart_04_raw_normalized_scene_depth_fua_ranks.png",
)
display_path(figure_04_path)
            """
        ),
        markdown(
            f"""
## 08. Findings

Within {scope_label} and this balanced {total_bands}-band catalogue:

- **Raw all-ten totals:** {facts['raw_top']} lead before population
  normalization.
- **Primary all-ten result:** {facts['all_ten_top']} have the greatest selected
  current reach relative to FUA population.
{top_ten_finding}
- **Largest band excluded:** {facts['top_excluded_top']} lead the scene-depth
  sensitivity.
- **Concentration:** Liverpool and Sheffield depend more heavily on their
  largest selected act than Manchester does.

The headline remains the all-ten FUA-population-normalized ranking. The
scene-depth test answers a narrower robustness question.
            """
        ),
        markdown(
            f"""
## 09. Limitations

- Conclusions apply to {scope_label}, not every UK city.
- The catalogue is manually curated, excludes solo artists, reflects the
  project's genre lane, and is not a random sample.
- {facts['low_confidence_rows']} assignments are marked low confidence;
  {facts['review_required_rows']} carry the `review_required` alignment label.
- A formation place can sit in the urban centre or wider commuting zone.
  Mapping a music scene onto an FUA therefore involves editorial judgement.
- Monthly listeners are volatile global Spotify reach observed once. They are
  not historical impact or local listening.
- Dividing global reach by FUA population is a size normalization, not a local
  listening rate.
- Largest-band exclusion cannot remove catalogue-selection bias.

The supported conclusion is narrow: the notebook ranks the selected catalogue
relative to a consistent FUA denominator and then shows how much that order
depends on each area's largest selected band.

Charts are saved under `{chart_display}`.
            """
        ),
        markdown(
            f"""
## Appendix A. Why the geography changed

Earlier versions used a mixed set of census built-up areas inherited from the
original shortlist. That was workable for exploration, but it was not a
population-selected universe and did not provide one harmonized geography
across all four UK nations.

The FUA version starts from the official OECD population table. This also
changes the top-ten panel: Bradford is not a separate entry in the OECD FUA
universe, Nottingham ranks eleventh, and Newcastle and Leicester enter the ten
largest FUAs. The previous built-up-area notebook remains preserved in the
project snapshots rather than being silently rewritten.

Source references:

- [OECD FUA definition and boundary resources]({FUA_DEFINITION_URL})
- [OECD population dataset used for the frozen 2021 universe]({FUA_DATASET_URL})
            """
        ),
        markdown(
            """
## Appendix B. Useful dead ends

Google Trends was rejected as the common popularity measure because sampled,
request-normalized results were unstable across batches. MusicBrainz remains
useful for discovery and identity resolution but cannot decide editorial
questions such as formation place or what counts as a band. The earlier
five-band and built-up-area analyses remain part of the audit trail, not part
of this estimator.
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
            "analysis_snapshot_id": snapshot.snapshot_id,
            "fua_city_count": snapshot.city_count,
            "study_status": "experiment" if experiment else "final",
        },
    )


def _project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def default_output_path(city_count: int, snapshot_id: str) -> Path:
    if city_count == 10:
        return (
            PROJECT_ROOT
            / "notebooks"
            / "final"
            / "uk_bands_punching_above_weight.ipynb"
        )
    return (
        PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "08_uk_bands_top20_fua_final_structure.ipynb"
    )


def default_chart_dir(city_count: int, snapshot_id: str) -> Path:
    if city_count == 10:
        return PROJECT_ROOT / "artifacts" / "charts"
    return (
        PROJECT_ROOT
        / "artifacts"
        / "experiments"
        / "top20_fua_final_structure"
        / snapshot_id
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city-count", type=int, choices=(10, 20), required=True)
    parser.add_argument("--snapshot", default="latest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--chart-dir", type=Path)
    parser.add_argument(
        "--experiment",
        action="store_true",
        help="Label the notebook as an experiment.",
    )
    return parser


def main(argv: list[str] | None = None) -> Path:
    args = build_parser().parse_args(argv)
    snapshot = resolve_fua_study_snapshot(
        city_count=args.city_count,
        selector=args.snapshot,
    )
    output_path = (
        _project_path(args.output)
        if args.output
        else default_output_path(args.city_count, snapshot.snapshot_id)
    )
    chart_output_dir = (
        _project_path(args.chart_dir)
        if args.chart_dir
        else default_chart_dir(args.city_count, snapshot.snapshot_id)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(
        build_notebook(
            snapshot,
            chart_output_dir=chart_output_dir,
            experiment=args.experiment or args.city_count == 20,
        ),
        output_path,
    )
    print(output_path)
    return output_path


if __name__ == "__main__":
    main(sys.argv[1:])
