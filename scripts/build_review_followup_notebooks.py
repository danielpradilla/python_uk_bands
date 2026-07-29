#!/usr/bin/env python3
"""Build experiments 16-18 proposed by the statistical study review."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.review_experiments import (  # noqa: E402
    build_specification_multiverse,
    build_top1000_scene_depth,
    build_top20_generation_analysis,
)


NOTEBOOK_DIR = PROJECT_ROOT / "notebooks/experiments"
SNAPSHOT_ID = "20260718T204522Z"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing notebooks",
    )
    return parser


def _setup_cell(artifact_dir: str) -> str:
    return f'''from pathlib import Path
import json
import sys

import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = Path.cwd().resolve()
if not (ROOT / "src/python_uk_bands").exists():
    ROOT = next(
        parent for parent in Path.cwd().resolve().parents
        if (parent / "src/python_uk_bands").exists()
    )
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ARTIFACT_DIR = ROOT / "{artifact_dir}"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)'''


def _notebook_metadata(experiment_id: str, title: str) -> dict[str, object]:
    return {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3"},
        "experiment": {
            "id": experiment_id,
            "title": title,
            "spotify_snapshot": SNAPSHOT_ID,
            "population_year": 2021,
            "generated_by": "scripts/build_review_followup_notebooks.py",
        },
    }


def _build_multiverse_notebook() -> nbf.NotebookNode:
    ranked, stability, catalogue = build_specification_multiverse(PROJECT_ROOT)
    crawley = stability.set_index("study_city_label").loc["Crawley"]
    sheffield = stability.set_index("study_city_label").loc["Sheffield"]
    london = stability.set_index("study_city_label").loc["London"]
    title = "Specification multiverse: how much do city rankings move?"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

Across **{len(catalogue)} defensible specifications**, the league table moves
materially. Crawley finishes in the top five in
**{int(crawley['top_finishes'])}/{int(crawley['specifications'])}** applicable
specifications but ranges from rank **{int(crawley['best_rank'])}** to
**{int(crawley['worst_rank'])}**. Sheffield finishes top five in
**{int(sheffield['top_finishes'])}/{int(sheffield['specifications'])}** and
ranges from **{int(sheffield['best_rank'])}** to
**{int(sheffield['worst_rank'])}**; London ranges from
**{int(london['best_rank'])}** to **{int(london['worst_rank'])}**. These are
specification ranges, not sampling confidence intervals."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The study review recommends replacing a single exact rank with a multiverse of
defensible design choices. This experiment combines:

- balanced city-first catalogues covering 10 and 20 FUAs;
- popularity-first catalogues of 100, 200 and 1,000 bands;
- monthly listeners, followers and selected-band counts;
- raw totals, per-capita scores, largest-band exclusion and output quotients;
- strict and reviewed-extended FUA mappings; and
- negative-binomial count residuals and log–log follower residuals.

### Key Assumptions

Each specification receives equal descriptive weight. A city is summarized
only across specifications in which it is eligible. The resulting rank range
measures design sensitivity; it is not a probability interval and does not
make the editorial catalogues random samples."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nLoad the frozen experiment inputs and rebuild every rank."
        ),
        nbf.v4.new_code_cell(_setup_cell(
            f"artifacts/experiments/specification_multiverse/{SNAPSHOT_ID}"
        )),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_experiments import (
    build_specification_multiverse,
    plot_rank_intervals,
    plot_top_finish_share,
)

ranked, stability, specification_catalogue = build_specification_multiverse(ROOT)

assert specification_catalogue["specification"].nunique() == 32
assert not ranked.duplicated(["specification", "study_city_label"]).any()
assert ranked["rank"].ge(1).all()
assert stability["top_finish_share"].between(0, 1).all()

ranked.to_csv(ARTIFACT_DIR / "ranked_specifications.csv", index=False)
stability.to_csv(ARTIFACT_DIR / "rank_stability.csv", index=False)
specification_catalogue.to_csv(
    ARTIFACT_DIR / "specification_catalogue.csv", index=False
)

display(Markdown(
    f"**{len(specification_catalogue)} specifications · "
    f"{ranked['study_city_label'].nunique()} FUAs appear at least once · "
    f"{len(ranked):,} city-specification ranks**"
))
display(specification_catalogue.groupby("family", as_index=False).agg(
    specifications=("specification", "nunique"),
    minimum_eligible_cities=("eligible_cities", "min"),
    maximum_eligible_cities=("eligible_cities", "max"),
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. Which cities remain near the top most often?"
        ),
        nbf.v4.new_code_cell(
            '''top_stability = stability.head(15)[[
    "study_city_label",
    "specifications",
    "best_rank",
    "median_rank",
    "worst_rank",
    "top_finishes",
    "top_finish_share",
]].copy()
display(top_stability.style.hide(axis="index").format({
    "median_rank": "{:.1f}",
    "top_finish_share": "{:.0%}",
}))'''
        ),
        nbf.v4.new_code_cell(
            '''interval_path = plot_rank_intervals(
    stability,
    output_path=ARTIFACT_DIR / "chart_01_rank_intervals.png",
)
display(Image(filename=str(interval_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. How frequently does each city finish in the top five?"
        ),
        nbf.v4.new_code_cell(
            '''frequency_path = plot_top_finish_share(
    stability,
    output_path=ARTIFACT_DIR / "chart_02_top_five_frequency.png",
)
display(Image(filename=str(frequency_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- The ranking depends strongly on catalogue construction, geography, audience
  metric and scoring rule.
- Crawley's frequent high finish is paired with a rank range extending well
  outside the top five, consistent with one-band and denominator sensitivity.
- Sheffield combines a high top-five frequency with exposure to every balanced
  and popularity-first specification, but it still does not have one exact,
  design-independent rank.
- Publication should show rank ranges or top-five frequencies alongside any
  single preferred specification."""
        ),
    ]
    return nbf.v4.new_notebook(
        cells=cells,
        metadata=_notebook_metadata("16", title),
    )


def _build_scene_depth_notebook() -> nbf.NotebookNode:
    depth, mapped, coverage = build_top1000_scene_depth(PROJECT_ROOT)
    indexed = depth.set_index("study_city_label")
    london = indexed.loc["London"]
    glasgow = indexed.loc["Glasgow"]
    manchester = indexed.loc["Manchester"]
    crawley = indexed.loc["Crawley"]
    sheffield = indexed.loc["Sheffield"]
    title = "Scene depth: breadth, concentration and follower output"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

In the mapped top-1,000 catalogue, London has the broadest follower base with
an effective-band count of **{london['effective_band_count']:.1f}**, followed
by Glasgow (**{glasgow['effective_band_count']:.1f}**) and Manchester
(**{manchester['effective_band_count']:.1f}**). Crawley has the highest
follower output quotient (**{crawley['follower_output_quotient']:.2f}×**) but
an effective-band count of **{crawley['effective_band_count']:.1f}**. Sheffield
combines a **{sheffield['follower_output_quotient']:.2f}×** quotient with
**{sheffield['effective_band_count']:.1f}** effective bands, while its largest
band supplies **{sheffield['largest_band_share']:.0%}** of mapped followers."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

Counting selected bands does not describe how follower attention is
distributed. This experiment calculates, for each mapped FUA:

- inverse Herfindahl effective-band count;
- largest-band and top-three follower shares;
- median mapped-band followers; and
- the number of mapped bands above 100,000 followers.

It then compares scene breadth with the follower output quotient already used
in the top-1,000 output-share experiment.

### Key Assumptions

The measures describe the selected popularity-first catalogue, not every band
formed in an FUA. Spotify followers are accumulated platform audiences rather
than local participation or historical influence."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nBuild the metrics from the frozen top-1,000 selection "
            "and reviewed FUA map."
        ),
        nbf.v4.new_code_cell(_setup_cell(
            f"artifacts/experiments/scene_depth_concentration/{SNAPSHOT_ID}"
        )),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_experiments import (
    build_top1000_scene_depth,
    plot_depth_vs_output,
    plot_effective_band_ranking,
)

depth, mapped_bands, coverage = build_top1000_scene_depth(ROOT)

assert len(mapped_bands) == coverage["mapped_bands"]
assert depth["effective_band_count"].le(depth["band_count"] + 1e-9).all()
assert depth["largest_band_share"].between(0, 1).all()
assert depth["top_three_share"].between(0, 1).all()

depth.to_csv(ARTIFACT_DIR / "scene_depth_metrics.csv", index=False)
mapped_bands.to_csv(ARTIFACT_DIR / "mapped_band_inputs.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(coverage, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{coverage['mapped_bands']} mapped bands · "
    f"{len(depth)} positive-output FUAs · "
    f"{coverage['mapped_follower_share']:.1%} of selected followers mapped**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. Which FUAs have the broadest follower distributions?"
        ),
        nbf.v4.new_code_cell(
            '''display(depth.head(20)[[
    "study_city_label",
    "band_count",
    "effective_band_count",
    "largest_band_share",
    "top_three_share",
    "bands_above_threshold",
    "follower_output_quotient",
]].style.hide(axis="index").format({
    "effective_band_count": "{:.2f}",
    "largest_band_share": "{:.1%}",
    "top_three_share": "{:.1%}",
    "follower_output_quotient": "{:.2f}×",
}))'''
        ),
        nbf.v4.new_code_cell(
            '''ranking_path = plot_effective_band_ranking(
    depth,
    output_path=ARTIFACT_DIR / "chart_01_effective_band_ranking.png",
)
display(Image(filename=str(ranking_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Does high population-adjusted output imply a broad scene?"
        ),
        nbf.v4.new_code_cell(
            '''label_cities = (
    set(depth.head(5)["study_city_label"])
    | set(depth.nlargest(5, "follower_output_quotient")["study_city_label"])
)
relationship_path = plot_depth_vs_output(
    depth,
    output_path=ARTIFACT_DIR / "chart_02_depth_vs_output.png",
    label_cities=sorted(label_cities),
)
display(Image(filename=str(relationship_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Output and depth answer different questions: a city can have an exceptional
  population-adjusted audience while depending on one dominant band.
- London, Glasgow and Manchester have the broadest follower distributions in
  this selected catalogue.
- Crawley, Hastings and Exeter illustrate why a high output quotient should not
  be described as scene depth.
- Effective-band count, concentration and threshold counts should accompany
  future normalized rankings."""
        ),
    ]
    return nbf.v4.new_notebook(
        cells=cells,
        metadata=_notebook_metadata("17", title),
    )


def _build_generations_notebook() -> nbf.NotebookNode:
    bands, coverage, decade_summary, overall = build_top20_generation_analysis(
        PROJECT_ROOT
    )
    title = "Generations of music cities: a formation-year coverage experiment"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

The frozen MusicBrainz captures provide formation years for
**{overall['bands_with_year']}/{overall['selected_bands']} bands
({overall['formation_year_coverage']:.0%})** in the balanced top-20 catalogue.
Only **{overall['cities_with_complete_years']} of {overall['cities']} FUAs**
have complete coverage, while **{overall['cities_with_no_years']}** have none.
The observed years span **{overall['earliest_observed_year']}–
{overall['latest_observed_year']}**. This is enough to inspect the available
cohorts, but not enough to rank cities by generation without severe coverage
bias."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The study review proposes comparing generations of music cities by band
formation decade. This first experiment extracts formation years only from
the repository's frozen MusicBrainz search and resolution captures. It joins
by MusicBrainz ID first and uses exact-name fallback only within the dedicated
top-20 resolution capture.

### Key Assumptions

Formation year is treated as a band-level cohort marker. Current Spotify
followers and listeners are not interpreted as audience at the time of
formation. Missing years are not treated as zero bands, and no city ranking is
reported because completeness differs sharply by FUA."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nAttach frozen formation years and measure coverage "
            "before examining decades."
        ),
        nbf.v4.new_code_cell(_setup_cell(
            f"artifacts/experiments/generations_by_decade/{SNAPSHOT_ID}"
        )),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_experiments import (
    build_top20_generation_analysis,
    plot_decade_heatmap,
    plot_formation_year_coverage,
)

bands, formation_coverage, decade_summary, overall = (
    build_top20_generation_analysis(ROOT)
)

assert len(bands) == 200
assert formation_coverage["selected_bands"].eq(10).all()
assert formation_coverage["formation_year_coverage"].between(0, 1).all()
assert int(formation_coverage["bands_with_year"].sum()) == overall["bands_with_year"]

bands.to_csv(ARTIFACT_DIR / "band_formation_year_audit.csv", index=False)
formation_coverage.to_csv(
    ARTIFACT_DIR / "formation_year_coverage.csv", index=False
)
decade_summary.to_csv(ARTIFACT_DIR / "formation_decade_summary.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(overall, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{overall['bands_with_year']}/{overall['selected_bands']} formation "
    f"years observed ({overall['formation_year_coverage']:.0%}) · "
    f"{overall['cities_with_complete_years']} complete FUAs · "
    f"{overall['cities_with_no_years']} FUAs with no observed years**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. Is coverage adequate for a city comparison?"
        ),
        nbf.v4.new_code_cell(
            '''display(formation_coverage.style.hide(axis="index").format({
    "formation_year_coverage": "{:.0%}",
}))

coverage_path = plot_formation_year_coverage(
    formation_coverage,
    output_path=ARTIFACT_DIR / "chart_01_formation_year_coverage.png",
)
display(Image(filename=str(coverage_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. What formation decades are visible in the available data?"
        ),
        nbf.v4.new_code_cell(
            '''heatmap_path = plot_decade_heatmap(
    bands,
    formation_coverage,
    output_path=ARTIFACT_DIR / "chart_02_observed_formation_decades.png",
)
display(Image(filename=str(heatmap_path)))

display(decade_summary.sort_values(
    ["formation_decade", "followers"], ascending=[True, False]
).head(30).style.hide(axis="index").format({
    "followers": "{:,.0f}",
    "monthly_listeners": "{:,.0f}",
}))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- The repository does not yet support a defensible generational city ranking.
- Coverage is complete for Glasgow, Leeds, Manchester and Sheffield, but zero
  for Edinburgh and Newcastle and only 20% for several other FUAs.
- The observed-decade heatmap is descriptive evidence about the captured
  records, not evidence that blank city-decades produced no bands.
- The next data step is a reviewed `formed_year` field for all 200 bands,
  followed by period-appropriate population denominators."""
        ),
    ]
    return nbf.v4.new_notebook(
        cells=cells,
        metadata=_notebook_metadata("18", title),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    notebooks = {
        NOTEBOOK_DIR / "16_uk_bands_specification_multiverse.ipynb": (
            _build_multiverse_notebook()
        ),
        NOTEBOOK_DIR / "17_uk_bands_scene_depth_and_concentration.ipynb": (
            _build_scene_depth_notebook()
        ),
        NOTEBOOK_DIR / "18_uk_bands_generations_by_decade.ipynb": (
            _build_generations_notebook()
        ),
    }
    existing = [path for path in notebooks if path.exists()]
    if existing and not args.force:
        raise FileExistsError(
            "Notebooks already exist; pass --force: "
            + ", ".join(str(path) for path in existing)
        )
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for path, notebook in notebooks.items():
        nbf.write(notebook, path)
        print(path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
