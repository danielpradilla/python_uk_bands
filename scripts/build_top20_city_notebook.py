#!/usr/bin/env python3
"""Build a dated reader-facing notebook for the top-20 city-first study."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _snapshot_id(path: Path) -> str:
    match = re.search(r"_(\d{8}T\d{6}Z)\.csv$", path.name)
    if not match:
        raise ValueError(f"Rankings path has no UTC snapshot ID: {path}")
    return match.group(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--band-metrics", required=True, type=Path)
    parser.add_argument("--rankings", required=True, type=Path)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the same dated notebook if it already exists",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    snapshot_id = _snapshot_id(args.rankings)
    output_path = (
        PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "snapshots"
        / f"uk_bands_top20_city_first_{snapshot_id}.ipynb"
    )
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"Dated notebook already exists; use --force: {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    catalog_path = args.catalog.resolve().relative_to(PROJECT_ROOT)
    band_metrics_path = args.band_metrics.resolve().relative_to(PROJECT_ROOT)
    rankings_path = args.rankings.resolve().relative_to(PROJECT_ROOT)
    artifact_dir = Path("artifacts") / "top20_city_first" / snapshot_id

    nb = nbf.v4.new_notebook()
    nb.metadata.update(
        {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "analysis_snapshot_id": snapshot_id,
        }
    )
    cells = []
    cells.append(
        nbf.v4.new_markdown_cell(
            """# Which of the twenty largest UK urban areas has the deepest band scene?

This is a separate **city-first experiment**. It does not alter the published
notebook. The study begins with the twenty largest UK Functional Urban Areas
(FUAs), curates ten bands for each, measures their current global Spotify
monthly-listener reach, and normalizes the result by FUA population.

The narrative shows the top ten, while every calculation and table retains all
twenty urban areas. Conclusions apply to **the twenty largest UK urban areas**,
not every UK city."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f"""from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import Markdown, display

ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path.cwd().parents)
        if (candidate / "reference/uk_fua_top20_2021.csv").exists()
    ),
    None,
)
if ROOT is None:
    raise FileNotFoundError(
        "Could not locate the repository root containing reference/uk_fua_top20_2021.csv"
    )
SNAPSHOT_ID = "{snapshot_id}"
CATALOG_PATH = ROOT / "{catalog_path.as_posix()}"
BAND_METRICS_PATH = ROOT / "{band_metrics_path.as_posix()}"
RANKINGS_PATH = ROOT / "{rankings_path.as_posix()}"
ARTIFACT_DIR = ROOT / "{artifact_dir.as_posix()}"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

catalog = pd.read_csv(CATALOG_PATH, keep_default_na=False)
bands = pd.read_csv(BAND_METRICS_PATH, keep_default_na=False)
rankings = pd.read_csv(RANKINGS_PATH, keep_default_na=False)

assert len(catalog) == 200
assert len(bands) == 200
assert len(rankings) == 20
assert catalog.groupby("study_city_label").size().eq(10).all()
assert catalog["catalogue_review_ready"].all()
assert bands["monthly_listeners"].notna().all()

captured_at = bands["stats_extracted_at_utc"].iloc[0]
display(Markdown(
    f"**Frozen Spotify snapshot:** `{{SNAPSHOT_ID}}` "
    f"({{captured_at}}) · **200 bands** · **20 FUAs** · "
    "**10 reviewed bands per FUA**"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 1. Study design and data lineage

Population selection comes first: OECD/EU Functional Urban Areas are ranked
using the OECD's 2021 population observations. This gives one harmonized
geography across England, Scotland, Wales and Northern Ireland.

For each selected FUA, ten bands were manually reviewed for origin and Spotify
identity. Places within the wider FUA—such as Abingdon for Oxford or Stockton
for Middlesbrough—can count when their FUA membership is part of the reviewed
mapping.

Spotify values are a dated snapshot from Spotify's read-only web-player artist
overview. That endpoint is undocumented, so the raw responses are retained and
the notebook itself performs no network calls."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """lineage = pd.DataFrame(
    [
        {
            "stage": "Urban-area universe",
            "frozen input": "reference/uk_fua_top20_2021.csv",
            "definition": "Top 20 UK OECD/EU Functional Urban Areas",
        },
        {
            "stage": "Band catalogue",
            "frozen input": str(CATALOG_PATH.relative_to(ROOT)),
            "definition": "10 origin- and identity-reviewed bands per FUA",
        },
        {
            "stage": "Reach snapshot",
            "frozen input": str(BAND_METRICS_PATH.relative_to(ROOT)),
            "definition": "Spotify global monthly listeners at one UTC capture",
        },
        {
            "stage": "Ranking output",
            "frozen input": str(RANKINGS_PATH.relative_to(ROOT)),
            "definition": "Untrimmed and symmetric 10% per-tail results",
        },
    ]
)
display(lineage.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 2. The population-selected universe

The population column below is the denominator used by the study. All twenty
areas remain visible here even though later narrative charts show the top ten."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """universe = (
    catalog[
        [
            "uk_population_rank",
            "study_city_label",
            "official_fua_name",
            "population",
            "population_year",
            "fua_code",
        ]
    ]
    .drop_duplicates()
    .sort_values("uk_population_rank")
)
display(
    universe.style
    .hide(axis="index")
    .format({"population": "{:,.0f}", "population_year": "{:.0f}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 3. Baseline: all ten selected bands

The baseline adds the ten bands' monthly listeners and divides that total by
FUA population. This measures selected global Spotify reach per resident; it
does not measure local listening."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """baseline = rankings.sort_values("untrimmed_rank").copy()
baseline_table = baseline[
    [
        "untrimmed_rank",
        "city",
        "population",
        "untrimmed_value",
        "untrimmed_listeners_per_million_residents",
        "highest_excluded_bands",
        "top_band_concentration",
    ]
].rename(
    columns={
        "untrimmed_rank": "rank",
        "city": "urban area",
        "untrimmed_value": "ten-band listeners",
        "untrimmed_listeners_per_million_residents": "listeners per million residents",
        "highest_excluded_bands": "largest selected band",
        "top_band_concentration": "largest-band share",
    }
)
display(
    baseline_table.style
    .hide(axis="index")
    .format(
        {
            "population": "{:,.0f}",
            "ten-band listeners": "{:,.0f}",
            "listeners per million residents": "{:,.0f}",
            "largest-band share": "{:.1%}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """top10 = baseline.head(10).sort_values(
    "untrimmed_listeners_per_million_residents"
)
top3 = set(baseline.head(3)["city"])
colors = ["#e45756" if city in top3 else "#a7a9ac" for city in top10["city"]]

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(
    top10["city"],
    top10["untrimmed_listeners_per_million_residents"],
    color=colors,
)
ax.set_title("Global Spotify monthly listeners per million residents")
ax.set_xlabel("Ten selected bands, untrimmed")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="x", alpha=0.2)
fig.tight_layout()
chart_path = ARTIFACT_DIR / "01_untrimmed_top10.png"
fig.savefig(chart_path, dpi=160, bbox_inches="tight")
plt.show()
print(chart_path.relative_to(ROOT))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 4. Scene-depth test: remove one band from each tail

For each FUA, the highest- and lowest-listener band are removed. The remaining
eight bands form a **10% trimmed mean at each tail** (20% removed in total).
That mean is divided by population, yielding the
**population-normalized trimmed mean**.

Because every FUA retains exactly eight bands, ranking the normalized trimmed
mean is identical to ranking the normalized trimmed total. The mean is kept
because it is the clearest description of the estimator."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """trimmed = rankings.sort_values("rank").copy()
trimmed_table = trimmed[
    [
        "rank",
        "city",
        "population_normalized_trimmed_mean_per_million",
        "highest_excluded_bands",
        "lowest_excluded_bands",
        "untrimmed_rank",
        "rank_shift_after_trim",
    ]
].rename(
    columns={
        "city": "urban area",
        "population_normalized_trimmed_mean_per_million": (
            "trimmed mean per million residents"
        ),
        "highest_excluded_bands": "highest removed",
        "lowest_excluded_bands": "lowest removed",
        "untrimmed_rank": "baseline rank",
        "rank_shift_after_trim": "rank improvement",
    }
)
display(
    trimmed_table.style
    .hide(axis="index")
    .format({"trimmed mean per million residents": "{:,.0f}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """top10_trimmed = trimmed.head(10).sort_values(
    "population_normalized_trimmed_mean_per_million"
)
top3_trimmed = set(trimmed.head(3)["city"])
colors = [
    "#4c78a8" if city in top3_trimmed else "#a7a9ac"
    for city in top10_trimmed["city"]
]

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(
    top10_trimmed["city"],
    top10_trimmed["population_normalized_trimmed_mean_per_million"],
    color=colors,
)
ax.set_title("Population-normalized trimmed mean")
ax.set_xlabel("Mean monthly listeners among the middle eight bands, per million residents")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.grid(axis="x", alpha=0.2)
fig.tight_layout()
chart_path = ARTIFACT_DIR / "02_trimmed_top10.png"
fig.savefig(chart_path, dpi=160, bbox_inches="tight")
plt.show()
print(chart_path.relative_to(ROOT))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 5. What changes after trimming?

Rank movement distinguishes a scene supported by several acts from one whose
baseline is especially dependent on a single giant band."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """comparison = rankings[
    [
        "city",
        "untrimmed_rank",
        "rank",
        "rank_shift_after_trim",
        "highest_excluded_bands",
        "top_band_concentration",
    ]
].sort_values(["rank", "city"]).rename(
    columns={
        "city": "urban area",
        "untrimmed_rank": "baseline rank",
        "rank": "trimmed rank",
        "rank_shift_after_trim": "rank improvement",
        "highest_excluded_bands": "highest removed",
        "top_band_concentration": "largest-band share",
    }
)
rank_correlation = rankings["untrimmed_rank"].corr(rankings["rank"])
display(Markdown(f"**Baseline–trimmed rank correlation: {{rank_correlation:.3f}}.**"))
display(
    comparison.style
    .hide(axis="index")
    .format({"largest-band share": "{:.1%}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 6. Reading the result

- **Oxford ranks first in both specifications.** Radiohead accounts for a
  large share of the ten-band total, but Oxford still leads after Radiohead
  and its smallest selected band are removed. In this catalogue, the result is
  supported by the middle of the Oxford distribution—not just its largest act.
- **Sheffield remains second.** Removing Arctic Monkeys does not erase the
  strength of its other selected bands.
- **Manchester moves from fourth to third**, while **Liverpool drops from
  third to sixth** after the Beatles are removed.
- The overall rank correlation is high, so trimming changes the interpretation
  of a few highly concentrated cities more than it changes the whole ordering."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 7. Audit the selected bands

This table retains the full 200-band catalogue, origin evidence, Spotify
identity and current metric. It is deliberately long: the narrative can show
ten results without hiding the study's complete selection."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """audit = bands[
    [
        "uk_population_rank",
        "study_city_label",
        "band_name",
        "claimed_formation_place",
        "origin_review_status",
        "origin_evidence_url",
        "spotify_id",
        "spotify_name",
        "monthly_listeners",
    ]
].sort_values(["uk_population_rank", "monthly_listeners"], ascending=[True, False])
display(
    audit.style
    .hide(axis="index")
    .format({"monthly_listeners": "{:,.0f}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 8. Limitations and publication status

This completed experiment is reproducible from frozen local files, but it
remains an exploratory ranking:

- Ten manually curated bands are not a census of each area's music.
- The catalogue excludes solo artists and can reflect genre and documentation
  bias, especially in the smaller scenes.
- Some acts are assigned through the wider Functional Urban Area rather than
  the named core city. Those mappings are reviewed but not generated from an
  automated OECD municipality correspondence table.
- Monthly listeners are a volatile 28-day reach measure, not historical
  influence, sales, local audience, quality or cultural importance.
- Spotify's web-player endpoint is undocumented. The raw response snapshot is
  retained, but future refreshes may require a different collector.
- A symmetric trim reduces sensitivity to both a blockbuster and a tiny act,
  but it does not remove catalogue-selection bias.

The result should therefore be described as applying to **the selected bands
from the twenty largest UK urban areas at this snapshot**, not to every band,
every city, or UK music history as a whole."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """assert set(baseline["city"]) == set(trimmed["city"])
assert rankings["input_bands"].eq(10).all()
assert rankings["retained_bands"].eq(8).all()
assert rankings["trim_fraction_each_tail"].eq(0.1).all()
assert rankings["population_normalized_trimmed_mean"].notna().all()
print("Validation passed: frozen 20-city analysis is complete and internally balanced.")"""
        )
    )
    nb.cells = cells
    nbf.write(nb, output_path)
    print(output_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
