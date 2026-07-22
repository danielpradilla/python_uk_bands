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
from python_uk_bands.scene_depth import build_scene_depth_rankings
from python_uk_bands.scene_depth_snapshots import (
    SceneDepthSnapshot,
    resolve_scene_depth_snapshot,
)


FOLLOWER_THRESHOLD = 100_000
PUBLISHED_TOP_N = 3


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
    ]
    published = build_city_rankings(
        published_eligible,
        metric="monthly_listeners",
        top_n=PUBLISHED_TOP_N,
    )

    all_ten_top = (
        rankings.sort_values("untrimmed_rank").head(3)["city"].tolist()
    )
    top_excluded_top = (
        rankings.sort_values("top_excluded_rank").head(3)["city"].tolist()
    )
    symmetric_top = rankings.sort_values("rank").head(3)["city"].tolist()
    published_top = published.sort_values("rank").head(3)["city"].tolist()
    by_city = rankings.set_index("city")
    london_score = by_city.loc[
        "London", "population_normalized_trimmed_mean"
    ]
    birmingham_score = by_city.loc[
        "Birmingham", "population_normalized_trimmed_mean"
    ]

    return {
        "snapshot_date": pd.to_datetime(bands["stats_extracted_at"]).max(),
        "published_top": _natural_list(published_top),
        "all_ten_top": _natural_list(all_ten_top),
        "top_excluded_top": _natural_list(top_excluded_top),
        "symmetric_top": _natural_list(symmetric_top),
        "same_leading_cluster": set(published_top) == set(all_ten_top),
        "top_only_matches_symmetric": bool(
            rankings["symmetric_vs_top_only_rank_shift"].eq(0).all()
        ),
        "manchester_all_rank": int(by_city.loc["Manchester", "untrimmed_rank"]),
        "manchester_excluded_rank": int(
            by_city.loc["Manchester", "top_excluded_rank"]
        ),
        "sheffield_all_rank": int(by_city.loc["Sheffield", "untrimmed_rank"]),
        "sheffield_excluded_rank": int(
            by_city.loc["Sheffield", "top_excluded_rank"]
        ),
        "liverpool_all_rank": int(by_city.loc["Liverpool", "untrimmed_rank"]),
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
        "london_birmingham_gap": (
            abs(london_score - birmingham_score)
            / max(london_score, birmingham_score)
        ),
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
# Current global Spotify reach and scene depth: ten bands per British city

## tl;dr

The original five-band analysis placed {facts['published_top']} at the top. Expanding the catalogue to ten bands per city preserves the same leading cluster but changes its order: {facts['all_ten_top']} lead when all ten selected bands count toward current global Spotify reach.

That is only the first result. The largest band supplies {facts['liverpool_concentration']:.0%} of Liverpool's selected reach and {facts['sheffield_concentration']:.0%} of Sheffield's, compared with {facts['manchester_concentration']:.0%} in Manchester. Removing each city's largest band changes the leading order to {facts['top_excluded_top']}. Liverpool falls from rank {facts['liverpool_all_rank']} to {facts['liverpool_excluded_rank']}; Sheffield moves from {facts['sheffield_all_rank']} to {facts['sheffield_excluded_rank']}; Manchester rises from {facts['manchester_all_rank']} to {facts['manchester_excluded_rank']}.

A symmetric trim—removing the highest and lowest band, then calculating a population-normalized trimmed mean from the middle eight—produces the same city order as removing only the largest band. The broad result is therefore not a single winner: Manchester and Sheffield look consistently deep, while Liverpool's position is more dependent on the Beatles.

> **Scope caveat:** “Reach” throughout this notebook means current global Spotify monthly-listener reach. It is not a measure of historical or cultural impact, record sales, influence, live audiences or listening by local residents.
            """
        ),
        markdown(
            """
## 01. Why expand the catalogue?

The publication notebook began with five manually selected bands per city. That was enough to test the idea, but not enough to distinguish a broadly successful music scene from a city dominated by one extraordinary act.

This experiment gives every city ten selected bands. It then asks the question in stages:

1. What does the ranking look like when all ten bands count?
2. How much of each city total comes from its largest band?
3. What remains when that headline act is removed?
4. Does a symmetric trimmed mean tell a different story?

The sequence matters. The untrimmed result describes current global Spotify reach across the selected catalogue; the trimmed results test whether that reach extends beyond the largest act.
            """
        ),
        markdown(
            """
## 02. Useful dead ends

There were a few wrong turns before this became a 100-band comparison. They are worth recording because each one exposed a different problem with comparing cities.

### Google Trends

I first tried using search interest as a common measure of popularity. The values looked convenient, but Google Trends samples the underlying searches and normalizes each request to its own peak. Comparing many bands meant splitting them into batches and using anchor acts to connect those batches. Small changes to the anchors or time window could change the apparent city totals. I could make the charts, but I could not defend the comparison, so I archived that route.

### MusicBrainz

MusicBrainz was useful, but not as an automatic answer. It widened the candidate pool and helped connect reviewed acts to Spotify. It did not remove the editorial work: artist type, whether an act counted as a band, where it formed, ambiguous names and the study's genre boundaries still needed review. The broad catalogue became source material rather than the final dataset.

### Spotify metrics and the first 50 bands

The first published version used five bands per city, a follower threshold and a September 2025 SpotScraper snapshot. It proved the analysis could work, but the threshold left some cities with fewer eligible bands and the saved data contained one known artist mismatch. The refreshed workflow freezes public Spotify-page metrics against reviewed artist IDs, and the main study now uses ten bands per city with no follower threshold.

None of that work was wasted. Google Trends showed me what I could not compare. MusicBrainz widened the pool but left a pile of editorial decisions. The 50-band version exposed the uneven coverage and concentration problems that this notebook now tests directly.

The underlying work is preserved in the [Google Trends archive](../archive/google-trends/README.md), the [original analysis scratchpad](../archive/original-analysis/python_uk_bands.ipynb) and the [first published notebook](../archive/published-v1/uk_bands_punching_above_weight.ipynb).
            """
        ),
        markdown(
            f"""
## 03. Data and method

The experiment uses a fixed catalogue of 100 bands: ten bands for each of ten British built-up areas. Spotify followers are not used as an eligibility threshold, so every city contributes the same number of observations.

The selected snapshot is **`{snapshot.snapshot_id}`**, with Spotify metrics dated **{snapshot_long}**. Notebook execution is offline and reads:

- `reference/scene_depth_bands.csv`: the reviewed ten-band-per-city catalogue.
- `{metrics_display}`: frozen band identities, monthly listeners and population.
- `{rankings_display}`: the saved ranking outputs used for reproducibility checks.

All three variants use 2021 built-up-area population as the denominator:

- **All ten:** sum all ten bands' monthly listeners and divide by population.
- **Largest excluded:** remove the largest band, sum the other nine and divide by population.
- **Symmetric trim:** remove the highest and lowest band, average the middle eight and divide that trimmed mean by population.

The last measure is the **population-normalized trimmed mean**. Because every city retains eight bands, its rank is identical to ranking a population-normalized middle-eight total; the mean gives the measure a clearer statistical interpretation.

### Key assumptions

- The catalogue is balanced but still manually curated and genre-influenced.
- Spotify monthly listeners measure current global platform reach. They do not measure historical or cultural impact, and they are not listening by local residents.
- Population is a normalization denominator, not an estimate of each band's local audience.
- Trimming reduces sensitivity to extremes but cannot correct catalogue-selection bias.
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
    build_scene_depth_rankings,
    validate_scene_depth_dataset,
)
from python_uk_bands.scene_depth_visuals import (
    plot_scene_depth_rank_comparison,
    plot_scene_depth_scores,
    plot_ten_band_population_normalized_total,
    plot_top_band_concentration,
    plot_top_excluded_population_normalized_total,
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
# Recalculate every variant from band-level data and verify the frozen result.
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
            """
        ),
        markdown(
            f"""
## 04. First result: current global Spotify reach across all ten bands

With all ten selected bands included, {facts['all_ten_top']} lead. The leading cluster is the same as in the five-band publication, although Manchester and Liverpool exchange position.

This result answers a deliberately broad question: how much current global Spotify monthly-listener reach is represented by the ten selected bands relative to city population? It does not yet distinguish breadth from superstar concentration.
            """
        ),
        code(
            """
all_ten_table = rankings[
    [
        "untrimmed_rank",
        "city",
        "untrimmed_ratio",
        "highest_excluded_bands",
        "top_band_concentration",
    ]
].sort_values("untrimmed_rank").rename(
    columns={
        "untrimmed_rank": "Rank",
        "city": "City",
        "untrimmed_ratio": "Current global ten-band reach / population",
        "highest_excluded_bands": "Largest selected band",
        "top_band_concentration": "Largest-band share",
    }
)
display(all_ten_table)
            """
        ),
        code(
            f"""
figure_01_path = plot_ten_band_population_normalized_total(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=1,
    filename="chart_01_ten_band_population_normalized_total.png",
)
display_path(figure_01_path)
            """
        ),
        markdown(
            """
## 05. Before trimming: where does the reach come from?

A city can rank highly because several bands contribute meaningful current global Spotify reach, or because one act dominates the total. The next chart shows the largest selected band's share before anything is removed.
            """
        ),
        code(
            f"""
figure_02_path = plot_top_band_concentration(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=2,
    filename="chart_02_largest_band_concentration.png",
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
The Beatles supply {facts['liverpool_concentration']:.1%} of Liverpool's selected total. Arctic Monkeys supply {facts['sheffield_concentration']:.1%} of Sheffield's. Manchester is less concentrated: its largest selected band supplies {facts['manchester_concentration']:.1%}.

This is the reason to trim. The question is not whether those bands “count”; clearly they do. The sensitivity test asks whether the city still looks strong without allowing one current superstar to determine most of its position.
            """
        ),
        markdown(
            f"""
## 06. Remove the largest band

After each city's largest selected band is removed, {facts['top_excluded_top']} lead. Manchester rises to first and Sheffield remains second even without Arctic Monkeys. Liverpool falls from third to fifth without the Beatles.

This is the clearest scene-depth test in the notebook: it retains nine bands per city and changes only the observation most capable of overwhelming the total.
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
        "untrimmed_rank",
    ]
].copy()
largest_excluded_table["rank_change"] = (
    largest_excluded_table["untrimmed_rank"]
    - largest_excluded_table["top_excluded_rank"]
)
display(
    largest_excluded_table.sort_values("top_excluded_rank").rename(
        columns={
            "top_excluded_rank": "Rank",
            "city": "City",
            "top_excluded_ratio": "Current global other-nine reach / population",
            "highest_excluded_bands": "Band removed",
            "untrimmed_rank": "All-ten rank",
            "rank_change": "Places gained",
        }
    )
)
            """
        ),
        code(
            f"""
figure_03_path = plot_top_excluded_population_normalized_total(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=3,
    filename="chart_03_largest_band_excluded.png",
)
display_path(figure_03_path)
            """
        ),
        markdown(
            """
## 07. Symmetric trim: remove the highest and lowest

The formal trimmed-mean version removes one observation from each tail. For every city, it averages the middle eight bands and divides that mean by population.

This is a 10% trim at each tail, or 20% of observations removed overall. Removing the lowest band prevents both ends of the selected distribution from determining the mean, but it also discards some evidence about how far down the scene's reach extends.
            """
        ),
        code(
            """
symmetric_trim_table = rankings[
    [
        "rank",
        "city",
        "population_normalized_trimmed_mean",
        "highest_excluded_bands",
        "lowest_excluded_bands",
        "top_excluded_rank",
    ]
].sort_values("rank").rename(
    columns={
        "rank": "Rank",
        "city": "City",
        "population_normalized_trimmed_mean": (
            "Population-normalized trimmed mean"
        ),
        "highest_excluded_bands": "Highest removed",
        "lowest_excluded_bands": "Lowest removed",
        "top_excluded_rank": "Largest-only-excluded rank",
    }
)
display(symmetric_trim_table)
            """
        ),
        code(
            f"""
figure_04_path = plot_scene_depth_scores(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=4,
    filename="chart_04_population_normalized_trimmed_mean.png",
)
display_path(figure_04_path)
            """
        ),
        markdown(
            f"""
The symmetric trim produces {facts['symmetric_top']} at the top—the same complete city order as the largest-band-excluded result. Removing the smallest band therefore changes the scale but not the ranking in this snapshot.

London and Birmingham are effectively tied: their population-normalized trimmed means differ by only {facts['london_birmingham_gap']:.2%}. Their third- and fourth-place order should not be treated as a meaningful separation.
            """
        ),
        markdown(
            """
## 08. How the ranking moves

The final chart puts the three stages on one rank scale. It is a summary of the experiment rather than another scoring method.
            """
        ),
        code(
            f"""
figure_05_path = plot_scene_depth_rank_comparison(
    rankings,
    snapshot_date="{snapshot_short}",
    output_dir=CHART_OUTPUT_DIR,
    number=5,
    filename="chart_05_rank_movement_across_methods.png",
)
display_path(figure_05_path)
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
            ["city", "untrimmed_rank", "top_excluded_rank", "rank"]
        ].rename(columns={"rank": "symmetric_trim_rank"}),
        on="city",
        validate="one_to_one",
    )
    .sort_values("symmetric_trim_rank")
)
display(
    method_comparison.rename(
        columns={
            "city": "City",
            "published_five_band_rank": "Published five-band rank",
            "untrimmed_rank": "All-ten rank",
            "top_excluded_rank": "Largest-excluded rank",
            "symmetric_trim_rank": "Symmetric-trim rank",
        }
    )
)
            """
        ),
        markdown(
            f"""
## 09. What the experiment supports

The ten-band expansion strengthens the original analysis without pretending to remove its subjectivity:

- The five-band and all-ten views identify the same leading cluster: Sheffield, Manchester and Liverpool.
- Manchester has the strongest result once each city's largest selected act is removed.
- Sheffield remains second without Arctic Monkeys, so its result is not simply a one-band anomaly.
- Liverpool is more sensitive to the Beatles and falls to fifth.
- The largest-excluded and symmetric-trim rankings are identical; the lowest-band removal adds no rank information in this snapshot.

The most defensible presentation is therefore to show the all-ten result first, then treat the largest-band-excluded result as the principal scene-depth sensitivity test. The population-normalized trimmed mean is a formal robustness check.

### Limitations

The catalogue remains a manually curated sample, not a census of British bands. It excludes solo artists and reflects the project's genre lane. {facts['review_rows']} origin assignments are medium confidence and flagged for editorial review. Spotify monthly listeners are volatile measures of current global platform reach. They do not measure historical or cultural impact, and dividing them by local population is a normalization device rather than a local listening rate.

The notebook supports a claim about the selected catalogue: Manchester and Sheffield have comparatively strong current global Spotify reach beyond their largest act, while Liverpool's position is more superstar-dependent. It does not establish a definitive ranking of British music scenes or musical impact.

Charts are saved under `{chart_display}`.
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
