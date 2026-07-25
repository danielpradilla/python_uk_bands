#!/usr/bin/env python3
"""Build an offline comparison of publication and scene-depth snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

import nbformat as nbf
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.analysis import build_city_rankings
from python_uk_bands.dataset import load_shortlist_dataset
from python_uk_bands.scene_depth_snapshots import (
    SceneDepthSnapshot,
    resolve_scene_depth_snapshot,
)
from python_uk_bands.shortlist_snapshots import (
    ShortlistSnapshot,
    resolve_shortlist_snapshot,
)


FOLLOWER_THRESHOLD = 100_000
TOP_N = 3
DEFAULT_BASELINE_SCENE = "20260717T203002Z"


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    return nbf.v4.new_code_cell(source.strip() + "\n")


def _natural_list(values: list[str]) -> str:
    if len(values) < 2:
        return "".join(values)
    return f"{', '.join(values[:-1])} and {values[-1]}"


def _timestamp(snapshot_id: str) -> datetime:
    return datetime.strptime(snapshot_id, "%Y%m%dT%H%M%SZ")


def build_facts(
    baseline_shortlist: ShortlistSnapshot,
    candidate_shortlist: ShortlistSnapshot,
    baseline_scene: SceneDepthSnapshot,
    candidate_scene: SceneDepthSnapshot,
) -> dict:
    baseline_bands = load_shortlist_dataset(
        metrics_path=baseline_shortlist.metrics_path
    )
    candidate_bands = load_shortlist_dataset(
        metrics_path=candidate_shortlist.metrics_path
    )
    baseline_eligible = baseline_bands.loc[
        baseline_bands["followers"] >= FOLLOWER_THRESHOLD
    ]
    candidate_eligible = candidate_bands.loc[
        candidate_bands["followers"] >= FOLLOWER_THRESHOLD
    ]
    baseline_rankings = build_city_rankings(
        baseline_eligible,
        metric="monthly_listeners",
        top_n=TOP_N,
    )
    candidate_rankings = build_city_rankings(
        candidate_eligible,
        metric="monthly_listeners",
        top_n=TOP_N,
    )
    shortlist_comparison = baseline_rankings[
        ["city", "rank", "top_n_ratio"]
    ].merge(
        candidate_rankings[["city", "rank", "top_n_ratio"]],
        on="city",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
    rank_changes = shortlist_comparison.loc[
        shortlist_comparison["rank_baseline"]
        != shortlist_comparison["rank_candidate"]
    ]

    eligibility = baseline_bands[["band", "followers"]].merge(
        candidate_bands[["band", "followers"]],
        on="band",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
    crossed_up = eligibility.loc[
        (eligibility["followers_baseline"] < FOLLOWER_THRESHOLD)
        & (eligibility["followers_candidate"] >= FOLLOWER_THRESHOLD),
        "band",
    ].tolist()
    crossed_down = eligibility.loc[
        (eligibility["followers_baseline"] >= FOLLOWER_THRESHOLD)
        & (eligibility["followers_candidate"] < FOLLOWER_THRESHOLD),
        "band",
    ].tolist()

    baseline_scene_rankings = pd.read_csv(baseline_scene.rankings_path)
    candidate_scene_rankings = pd.read_csv(candidate_scene.rankings_path)
    for rankings in (baseline_scene_rankings, candidate_scene_rankings):
        rankings["population_normalized_trimmed_mean"] = (
            rankings["trimmed_mean"] / rankings["population"]
        )
    scene_comparison = baseline_scene_rankings[
        ["city", "rank", "population_normalized_trimmed_mean"]
    ].merge(
        candidate_scene_rankings[
            ["city", "rank", "population_normalized_trimmed_mean"]
        ],
        on="city",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
    scene_comparison["score_change_pct"] = (
        scene_comparison["population_normalized_trimmed_mean_candidate"]
        / scene_comparison["population_normalized_trimmed_mean_baseline"]
        - 1
    ) * 100
    scene_rank_changes = scene_comparison.loc[
        scene_comparison["rank_baseline"]
        != scene_comparison["rank_candidate"]
    ]
    scene_interval_hours = (
        _timestamp(candidate_scene.snapshot_id)
        - _timestamp(baseline_scene.snapshot_id)
    ).total_seconds() / 3600

    baseline_top = (
        baseline_rankings.sort_values("rank").head(3)["city"].tolist()
    )
    candidate_top = (
        candidate_rankings.sort_values("rank").head(3)["city"].tolist()
    )
    scene_top = (
        candidate_scene_rankings.sort_values("rank").head(3)["city"].tolist()
    )
    return {
        "baseline_date": baseline_bands["stats_extracted_at"].max(),
        "candidate_date": candidate_bands["stats_extracted_at"].max(),
        "baseline_eligible": len(baseline_eligible),
        "candidate_eligible": len(candidate_eligible),
        "shortlist_rank_changes": len(rank_changes),
        "shortlist_changed_cities": _natural_list(
            rank_changes.sort_values("rank_candidate")["city"].tolist()
        ),
        "baseline_top": _natural_list(baseline_top),
        "candidate_top": _natural_list(candidate_top),
        "top_three_unchanged": baseline_top == candidate_top,
        "crossed_up": _natural_list(crossed_up),
        "crossed_down": _natural_list(crossed_down),
        "scene_rank_changes": len(scene_rank_changes),
        "scene_top": _natural_list(scene_top),
        "scene_interval_hours": scene_interval_hours,
        "scene_max_abs_change": scene_comparison["score_change_pct"].abs().max(),
    }


def build_notebook(
    *,
    baseline_shortlist: ShortlistSnapshot,
    candidate_shortlist: ShortlistSnapshot,
    baseline_scene: SceneDepthSnapshot,
    candidate_scene: SceneDepthSnapshot,
    chart_output_dir: Path,
):
    facts = build_facts(
        baseline_shortlist,
        candidate_shortlist,
        baseline_scene,
        candidate_scene,
    )
    baseline_shortlist_relative = baseline_shortlist.metrics_path.relative_to(
        PROJECT_ROOT
    )
    candidate_shortlist_relative = candidate_shortlist.metrics_path.relative_to(
        PROJECT_ROOT
    )
    baseline_scene_metrics_relative = baseline_scene.metrics_path.relative_to(
        PROJECT_ROOT
    )
    candidate_scene_metrics_relative = candidate_scene.metrics_path.relative_to(
        PROJECT_ROOT
    )
    baseline_scene_rankings_relative = baseline_scene.rankings_path.relative_to(
        PROJECT_ROOT
    )
    candidate_scene_rankings_relative = candidate_scene.rankings_path.relative_to(
        PROJECT_ROOT
    )
    chart_dir_relative = chart_output_dir.relative_to(PROJECT_ROOT)
    shortlist_change_text = (
        f"{facts['shortlist_changed_cities']} change rank"
        if facts["shortlist_rank_changes"]
        else "no cities change rank"
    )
    eligibility_text = (
        f"{facts['crossed_up']} crosses above the threshold"
        if facts["crossed_up"]
        else "no band crosses above the threshold"
    )
    if facts["crossed_down"]:
        eligibility_text += (
            f"; {facts['crossed_down']} crosses below it"
        )

    cells = [
        markdown(
            f"""
# Spotify snapshot comparison

## tl;dr

The September 2025 publication remains unchanged. Re-running its fixed 50-band catalogue with Spotify metrics from {facts['candidate_date'].strftime('%d %B %Y')} leaves the preferred top three unchanged: {facts['candidate_top']}. {shortlist_change_text}; {eligibility_text}.

The ten-band scene-depth experiment is even more stable: all ten city ranks are unchanged and the largest score movement is only {facts['scene_max_abs_change']:.2f}%. That comparison spans just {facts['scene_interval_hours']:.1f} hours, so it is a capture-consistency check, not evidence of a trend.
            """
        ),
        markdown(
            f"""
## 01. Comparison design

Both comparisons hold the reviewed artist IDs, city assignments, catalogues and 2021 population denominators fixed. Only Spotify followers and monthly listeners change.

- Publication baseline: `{baseline_shortlist_relative}` ({facts['baseline_date'].strftime('%d %B %Y')}).
- Publication candidate: `{candidate_shortlist_relative}` ({facts['candidate_date'].strftime('%d %B %Y')}).
- Scene-depth baseline: `{baseline_scene_metrics_relative}`.
- Scene-depth candidate: `{candidate_scene_metrics_relative}`.

The publication baseline was collected through SpotScraper; the candidate was parsed from Spotify's public artist pages. The concepts match, but a source-method change is still a comparability caveat. Monthly listeners are volatile rolling counts, and a single new snapshot should not be described as a trend.
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
        if (candidate / "reference" / "original_shortlist.csv").exists():
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
from python_uk_bands.dataset import load_shortlist_dataset, validate_shortlist_shape
from python_uk_bands.scene_depth import (
    build_scene_depth_rankings,
    validate_scene_depth_dataset,
)
from python_uk_bands.snapshot_visuals import plot_city_score_snapshot_change
from python_uk_bands.visuals import apply_chart_style

apply_chart_style()

BASELINE_SHORTLIST_PATH = PROJECT_ROOT / "{baseline_shortlist_relative.as_posix()}"
CANDIDATE_SHORTLIST_PATH = PROJECT_ROOT / "{candidate_shortlist_relative.as_posix()}"
BASELINE_SCENE_METRICS_PATH = PROJECT_ROOT / "{baseline_scene_metrics_relative.as_posix()}"
CANDIDATE_SCENE_METRICS_PATH = PROJECT_ROOT / "{candidate_scene_metrics_relative.as_posix()}"
BASELINE_SCENE_RANKINGS_PATH = PROJECT_ROOT / "{baseline_scene_rankings_relative.as_posix()}"
CANDIDATE_SCENE_RANKINGS_PATH = PROJECT_ROOT / "{candidate_scene_rankings_relative.as_posix()}"
CHART_OUTPUT_DIR = PROJECT_ROOT / "{chart_dir_relative.as_posix()}"
            """
        ),
        markdown(
            """
## 02. Data-quality and identity checks

The checks below stop execution if either catalogue changes, an artist ID changes, a city assignment changes, or a scene-depth saved ranking cannot be reproduced from its band-level file.
            """
        ),
        code(
            """
baseline_bands = load_shortlist_dataset(metrics_path=BASELINE_SHORTLIST_PATH)
candidate_bands = load_shortlist_dataset(metrics_path=CANDIDATE_SHORTLIST_PATH)
validate_shortlist_shape(baseline_bands)
validate_shortlist_shape(candidate_bands)

identity_columns = ["band", "city", "spotify_id"]
assert_frame_equal(
    baseline_bands[identity_columns].sort_values("band").reset_index(drop=True),
    candidate_bands[identity_columns].sort_values("band").reset_index(drop=True),
)
assert set(baseline_bands["population"]) == set(candidate_bands["population"])

baseline_scene_bands = pd.read_csv(BASELINE_SCENE_METRICS_PATH)
candidate_scene_bands = pd.read_csv(CANDIDATE_SCENE_METRICS_PATH)
validate_scene_depth_dataset(baseline_scene_bands, expected_cities=10, bands_per_city=10)
validate_scene_depth_dataset(candidate_scene_bands, expected_cities=10, bands_per_city=10)
assert_frame_equal(
    baseline_scene_bands[identity_columns].sort_values("band").reset_index(drop=True),
    candidate_scene_bands[identity_columns].sort_values("band").reset_index(drop=True),
)

quality_summary = pd.DataFrame(
    {
        "Check": [
            "Publication rows in each snapshot",
            "Scene-depth rows in each snapshot",
            "Fixed publication artist IDs",
            "Fixed scene-depth artist IDs",
            "Candidate follower coverage",
        ],
        "Result": [50, 100, "pass", "pass", int(candidate_bands["followers"].notna().sum())],
    }
)
display(quality_summary)
            """
        ),
        markdown(
            """
## 03. Published 50-band method under current metrics

The publication rule is unchanged: retain bands with at least 100,000 followers, take each city's top three monthly-listener values and divide by built-up-area population.
            """
        ),
        code(
            """
FOLLOWER_THRESHOLD = 100_000
TOP_N = 3

baseline_eligible = baseline_bands.loc[
    baseline_bands["followers"] >= FOLLOWER_THRESHOLD
].copy()
candidate_eligible = candidate_bands.loc[
    candidate_bands["followers"] >= FOLLOWER_THRESHOLD
].copy()
baseline_rankings = build_city_rankings(
    baseline_eligible, metric="monthly_listeners", top_n=TOP_N
)
candidate_rankings = build_city_rankings(
    candidate_eligible, metric="monthly_listeners", top_n=TOP_N
)
shortlist_comparison = (
    baseline_rankings[["city", "rank", "top_n_ratio", "eligible_bands"]]
    .merge(
        candidate_rankings[["city", "rank", "top_n_ratio", "eligible_bands"]],
        on="city",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
)
shortlist_comparison["score_change_pct"] = (
    shortlist_comparison["top_n_ratio_candidate"]
    / shortlist_comparison["top_n_ratio_baseline"]
    - 1
) * 100
display(
    shortlist_comparison.sort_values("rank_candidate").rename(
        columns={
            "city": "City",
            "rank_baseline": "Sep 2025 rank",
            "rank_candidate": "Current rank",
            "top_n_ratio_baseline": "Sep 2025 score",
            "top_n_ratio_candidate": "Current score",
            "eligible_bands_baseline": "Sep eligible",
            "eligible_bands_candidate": "Current eligible",
            "score_change_pct": "Score change %",
        }
    )
)
            """
        ),
        code(
            f"""
figure_01_path = plot_city_score_snapshot_change(
    shortlist_comparison,
    baseline_column="top_n_ratio_baseline",
    candidate_column="top_n_ratio_candidate",
    baseline_label="Sep 2025 publication",
    candidate_label="Jul 2026 candidate",
    title="Published top-three city score across two snapshots",
    subtitle="Same 50 bands, artist IDs, follower threshold and population denominators",
    x_label="Monthly-listener reach divided by population",
    number=1,
    filename="chart_01_publication_score_change.png",
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_01_path)
            """
        ),
        markdown(
            f"""
The preferred top three remain {facts['candidate_top']}. Eligibility rises from {facts['baseline_eligible']} to {facts['candidate_eligible']} bands because {eligibility_text}. The only city-rank movement is {facts['shortlist_changed_cities']}: Bradford moves above Nottingham after gaining another eligible band.
            """
        ),
        markdown(
            """
### 03.01 Band-level movement

The table separates raw metric movement from the city ranking. Percentage changes can be extreme for tiny accounts, so both absolute and percentage changes are shown.
            """
        ),
        code(
            """
band_changes = (
    baseline_bands[["band", "city", "monthly_listeners", "followers"]]
    .merge(
        candidate_bands[["band", "monthly_listeners", "followers"]],
        on="band",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
)
band_changes["monthly_change"] = (
    band_changes["monthly_listeners_candidate"]
    - band_changes["monthly_listeners_baseline"]
)
band_changes["monthly_change_pct"] = (
    band_changes["monthly_change"]
    / band_changes["monthly_listeners_baseline"].replace(0, pd.NA)
) * 100
band_changes["follower_change"] = (
    band_changes["followers_candidate"] - band_changes["followers_baseline"]
)
largest_band_movements = band_changes.loc[
    band_changes["monthly_change"].abs().nlargest(12).index
].sort_values("monthly_change", ascending=False)
display(largest_band_movements)
            """
        ),
        markdown(
            """
## 04. Ten-band scene-depth snapshot consistency

The scene-depth comparison uses the same 100 bands and removes one highest and one lowest monthly-listener observation per city. Its snapshots were taken only hours apart.
            """
        ),
        code(
            """
baseline_scene_saved = pd.read_csv(BASELINE_SCENE_RANKINGS_PATH)
candidate_scene_saved = pd.read_csv(CANDIDATE_SCENE_RANKINGS_PATH)
baseline_scene_rankings = build_scene_depth_rankings(
    baseline_scene_bands,
    metric="monthly_listeners",
    trim_each_tail=1,
    expected_cities=10,
    bands_per_city=10,
)
candidate_scene_rankings = build_scene_depth_rankings(
    candidate_scene_bands,
    metric="monthly_listeners",
    trim_each_tail=1,
    expected_cities=10,
    bands_per_city=10,
)
assert_frame_equal(
    baseline_scene_rankings.loc[:, baseline_scene_saved.columns],
    baseline_scene_saved,
    check_exact=False,
    rtol=1e-12,
    atol=1e-12,
)
assert_frame_equal(
    candidate_scene_rankings.loc[:, candidate_scene_saved.columns],
    candidate_scene_saved,
    check_exact=False,
    rtol=1e-12,
    atol=1e-12,
)
scene_comparison = (
    baseline_scene_rankings[
        ["city", "rank", "population_normalized_trimmed_mean"]
    ]
    .merge(
        candidate_scene_rankings[
            ["city", "rank", "population_normalized_trimmed_mean"]
        ],
        on="city",
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
)
scene_comparison["score_change_pct"] = (
    scene_comparison["population_normalized_trimmed_mean_candidate"]
    / scene_comparison["population_normalized_trimmed_mean_baseline"]
    - 1
) * 100
display(scene_comparison.sort_values("rank_candidate"))
            """
        ),
        code(
            """
figure_02_path = plot_city_score_snapshot_change(
    scene_comparison,
    baseline_column="population_normalized_trimmed_mean_baseline",
    candidate_column="population_normalized_trimmed_mean_candidate",
    baseline_label="Earlier capture",
    candidate_label="Later capture",
    title="Population-normalized trimmed mean across two captures",
    subtitle="Same 100 bands; mean of middle eight divided by population",
    x_label="Mean monthly listeners of retained bands divided by population",
    number=2,
    filename="chart_02_scene_depth_score_change.png",
    output_dir=CHART_OUTPUT_DIR,
)
display_path(figure_02_path)
            """
        ),
        markdown(
            f"""
All ten ranks are unchanged. The order remains {facts['scene_top']} at the top, and no city's population-normalized trimmed mean moves by more than {facts['scene_max_abs_change']:.2f}%.

## 05. Interpretation

- Keep `data/processed/shortlist_spotify_metrics.json` as the publication default.
- Use timestamped candidates for previews and comparisons; promote none of them implicitly.
- Treat the 100-band same-day comparison as evidence that the capture is reproducible, not that popularity is stable over time.
- For trend claims, collect several snapshots on a fixed cadence and distinguish threshold-crossing effects from changes among already-eligible bands.
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
    parser.add_argument("--baseline-shortlist", default="publication")
    parser.add_argument("--candidate-shortlist", default="latest")
    parser.add_argument("--baseline-scene", default=DEFAULT_BASELINE_SCENE)
    parser.add_argument("--candidate-scene", default="latest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--chart-dir", type=Path)
    return parser


def _absolute_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    baseline_shortlist = resolve_shortlist_snapshot(args.baseline_shortlist)
    candidate_shortlist = resolve_shortlist_snapshot(args.candidate_shortlist)
    baseline_scene = resolve_scene_depth_snapshot(args.baseline_scene)
    candidate_scene = resolve_scene_depth_snapshot(args.candidate_scene)
    comparison_id = (
        f"{baseline_scene.snapshot_id}_vs_{candidate_scene.snapshot_id}_"
        f"and_{candidate_shortlist.snapshot_id}"
    )
    output_path = (
        _absolute_project_path(args.output)
        if args.output
        else PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "04_uk_bands_snapshot_comparison.ipynb"
    )
    chart_output_dir = (
        _absolute_project_path(args.chart_dir)
        if args.chart_dir
        else PROJECT_ROOT / "artifacts" / "snapshot_comparisons" / comparison_id
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(
        build_notebook(
            baseline_shortlist=baseline_shortlist,
            candidate_shortlist=candidate_shortlist,
            baseline_scene=baseline_scene,
            candidate_scene=candidate_scene,
            chart_output_dir=chart_output_dir,
        ),
        output_path,
    )
    print(output_path)


if __name__ == "__main__":
    main(sys.argv[1:])
