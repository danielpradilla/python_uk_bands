#!/usr/bin/env python3
"""Build the canonical Crawley-inclusive top-100 popularity-first experiment."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat as nbf
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.popularity_first_visuals import add_raw_reach_rank  # noqa: E402


DEFAULT_SNAPSHOT_ID = "20260718T204522Z"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default=DEFAULT_SNAPSHOT_ID)
    parser.add_argument("--bands", type=Path)
    parser.add_argument("--origins", type=Path)
    parser.add_argument("--mapping-audit", type=Path)
    parser.add_argument("--strict", type=Path)
    parser.add_argument("--extended", type=Path)
    parser.add_argument("--selection-report", type=Path)
    parser.add_argument("--population-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def _default_path(kind: str, snapshot_id: str) -> Path:
    prefix = f"popularity_first_top100_{snapshot_id}"
    paths = {
        "bands": PROJECT_ROOT / "data" / "processed" / f"{prefix}_bands.csv",
        "origins": PROJECT_ROOT / "data" / "processed" / f"{prefix}_origins.csv",
        "mapping_audit": (
            PROJECT_ROOT / "data" / "interim" / f"{prefix}_fua_mapping_audit.csv"
        ),
        "strict": (
            PROJECT_ROOT / "data" / "processed" / f"{prefix}_population_strict.csv"
        ),
        "extended": (
            PROJECT_ROOT / "data" / "processed" / f"{prefix}_population_extended.csv"
        ),
        "selection_report": (
            PROJECT_ROOT / "data" / "processed" / f"{prefix}_report.json"
        ),
        "population_report": (
            PROJECT_ROOT
            / "data"
            / "processed"
            / f"{prefix}_population_adjusted_report.json"
        ),
    }
    return paths[kind]


def _relative(path: Path) -> Path:
    return path.resolve().relative_to(PROJECT_ROOT)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    snapshot_id = args.snapshot_id
    paths = {
        name: (
            getattr(args, name).resolve()
            if getattr(args, name) is not None
            else _default_path(name, snapshot_id)
        )
        for name in [
            "bands",
            "origins",
            "mapping_audit",
            "strict",
            "extended",
            "selection_report",
            "population_report",
        ]
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing frozen inputs: {missing}")

    output_path = (
        args.output
        or PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "snapshots"
        / f"uk_bands_top100_popularity_first_fua_{snapshot_id}.ipynb"
    ).resolve()
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"{output_path} already exists; pass --force to rebuild it"
        )

    bands = pd.read_csv(paths["bands"], keep_default_na=False)
    origins = pd.read_csv(paths["origins"], keep_default_na=False)
    mapping_audit = pd.read_csv(paths["mapping_audit"], keep_default_na=False)
    strict = pd.read_csv(paths["strict"], keep_default_na=False)
    ranked = add_raw_reach_rank(strict)

    if len(bands) != 100 or bands["returned_spotify_id"].nunique() != 100:
        raise ValueError("The canonical experiment requires 100 unique bands")
    if origins["band_count"].sum() != 100 or len(mapping_audit) != 100:
        raise ValueError("Origin and FUA audit rows must cover all 100 bands")
    if strict.iloc[0]["study_city_label"] != "Crawley":
        raise ValueError("Expected Crawley to lead the frozen strict FUA result")

    crawley_bands = mapping_audit.loc[
        mapping_audit["study_city_label"].eq("Crawley")
        & mapping_audit["mapping_tier"].eq("strict"),
        "spotify_name",
    ].tolist()
    stable = strict.loc[strict["band_count"].ge(2)].sort_values(
        "rank_by_listener_reach_per_resident"
    )
    stable_top_three = stable.head(3)["study_city_label"].tolist()
    london = ranked.loc[ranked["study_city_label"].eq("London")].iloc[0]
    manchester = ranked.loc[ranked["study_city_label"].eq("Manchester")].iloc[0]
    crawley = ranked.loc[ranked["study_city_label"].eq("Crawley")].iloc[0]

    relative_paths = {name: _relative(path) for name, path in paths.items()}
    artifact_dir = Path(
        f"artifacts/experiments/top100_popularity_first_fua/{snapshot_id}"
    )
    predecessor_raw = (
        "notebooks/experiments/snapshots/"
        f"uk_bands_top100_popularity_first_{snapshot_id}.ipynb"
    )
    predecessor_adjusted = (
        "notebooks/experiments/snapshots/"
        "uk_bands_top100_popularity_first_population_adjusted_"
        f"{snapshot_id}.ipynb"
    )

    cells: list = []
    cells.append(
        nbf.v4.new_markdown_cell(
            """# Top 100 UK bands: origins, scale and population

This popularity-first experiment starts with the 100 UK groups with the
largest captured Spotify monthly-listener counts in a frozen candidate
universe. It then asks two questions in sequence:

1. Where is the selected popularity concentrated before adjusting for
   population?
2. How does the result change when each origin is mapped to an OECD/EU
   Functional Urban Area (FUA) and divided by its 2021 population?

The second question brings **Crawley** to the top because The Cure has a large
global audience relative to Crawley's population. That is a valid
population-normalized output result, but it is based on one selected band—not
evidence of a deep local scene."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f"""from pathlib import Path
import json

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
    raise FileNotFoundError("Could not locate the uk-music-cities repository root")

import sys
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.popularity_first_visuals import (
    add_raw_reach_rank,
    plot_multiband_stability,
    plot_population_adjusted_fua_reach,
    plot_raw_fua_reach,
    plot_raw_vs_normalized_fua_ranks,
    plot_top_selected_bands,
)
from python_uk_bands.visuals import apply_chart_style

SNAPSHOT_ID = "{snapshot_id}"
BANDS_PATH = ROOT / "{relative_paths["bands"].as_posix()}"
ORIGINS_PATH = ROOT / "{relative_paths["origins"].as_posix()}"
MAPPING_AUDIT_PATH = ROOT / "{relative_paths["mapping_audit"].as_posix()}"
STRICT_PATH = ROOT / "{relative_paths["strict"].as_posix()}"
EXTENDED_PATH = ROOT / "{relative_paths["extended"].as_posix()}"
SELECTION_REPORT_PATH = ROOT / "{relative_paths["selection_report"].as_posix()}"
POPULATION_REPORT_PATH = ROOT / "{relative_paths["population_report"].as_posix()}"
CHART_OUTPUT_DIR = ROOT / "{artifact_dir.as_posix()}"

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
origins = pd.read_csv(ORIGINS_PATH, keep_default_na=False)
mapping_audit = pd.read_csv(MAPPING_AUDIT_PATH, keep_default_na=False)
strict = pd.read_csv(STRICT_PATH, keep_default_na=False)
extended = pd.read_csv(EXTENDED_PATH, keep_default_na=False)
selection_report = json.loads(SELECTION_REPORT_PATH.read_text(encoding="utf-8"))
population_report = json.loads(
    POPULATION_REPORT_PATH.read_text(encoding="utf-8")
)
ranked_strict = add_raw_reach_rank(strict)

assert len(bands) == 100
assert bands["popularity_rank"].tolist() == list(range(1, 101))
assert bands["returned_spotify_id"].nunique() == 100
assert origins["band_count"].sum() == 100
assert len(mapping_audit) == 100
assert strict["fua_code"].nunique() == len(strict) == 20
assert (strict["population"] > 0).all()
assert strict.iloc[0]["study_city_label"] == "Crawley"
assert set(mapping_audit["popularity_rank"]) == set(range(1, 101))

apply_chart_style()
CHART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

captured_at = pd.Timestamp(bands["stats_extracted_at_utc"].iloc[0])
snapshot_date = captured_at.strftime("%-d %B %Y")
display(Markdown(
    f"**Frozen Spotify snapshot:** `{{SNAPSHOT_ID}}` "
    f"({{captured_at.isoformat()}}) · **100 selected groups** · "
    f"**OECD/EU FUA population:** {{population_report['population_year']}} · "
    "**Notebook execution makes no network calls**"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 01. Study design

This is a **popularity-first** study. It can find globally prominent acts from
places outside the largest-city panel—Radiohead/Oxford and The Cure/Crawley are
exactly the cases this design is meant to surface.

It is not the same study as the balanced city-first notebook:

- **Popularity-first:** select bands by captured reach → map origins → compare
  geographic concentration and output relative to population.
- **City-first:** select a fixed city universe → curate the same number of
  bands per city → compare population-normalized scene output.

The popularity-first design is best read as the geography of this selected top
100. It does not estimate the full output or scene depth of every FUA."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """design = pd.DataFrame(
    [
        {
            "view": "Raw origin concentration",
            "numerator": "Selected band count and captured global reach",
            "denominator": "None",
            "interpretation": "Where this selected top 100 is concentrated",
        },
        {
            "view": "Population-adjusted output (main FUA view)",
            "numerator": "Captured global reach of strictly mapped bands",
            "denominator": "2021 OECD/EU FUA population",
            "interpretation": "Selected reach represented per FUA resident",
        },
        {
            "view": "Multi-band stability diagnostic",
            "numerator": "Same population-adjusted output",
            "denominator": "Same FUA population; display requires n ≥ 2",
            "interpretation": "Which results are not determined by one band",
        },
    ]
)
display(design.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 02. Frozen sources, selection and coverage

The band candidate frame comes from an archived Wikidata query for UK musical
groups with Spotify artist IDs. Spotify monthly listeners were captured once,
then identity mismatches, redirects, orchestras and origin assignments were
reviewed. Execution below reads those frozen local outputs only.

The population denominator is the
[OECD definition of cities and Functional Urban Areas](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html)
and its
[Data Explorer population series](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en)
for 2021. The main adjusted result uses the conservative **strict**
origin-to-FUA mapping; a broader reviewed mapping is retained only as a
sensitivity check."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """lineage = pd.DataFrame(
    [
        {
            "stage": "Candidate universe",
            "frozen input": selection_report["inputs"]["candidates"],
            "rule": "Archived Wikidata UK musical-group query",
        },
        {
            "stage": "Spotify reach capture",
            "frozen input": selection_report["inputs"]["metrics"],
            "rule": "One timestamped monthly-listener capture",
        },
        {
            "stage": "Identity and origin review",
            "frozen input": selection_report["inputs"]["overrides"],
            "rule": "Reviewed aliases, exclusions and origin overrides",
        },
        {
            "stage": "Origin → FUA audit",
            "frozen input": population_report["inputs"]["mapping"],
            "rule": "Strict, reviewed-extended or excluded decision",
        },
        {
            "stage": "Population denominator",
            "frozen input": population_report["inputs"]["population"],
            "rule": "OECD/EU FUA population, 2021",
        },
    ]
)
display(lineage.style.hide(axis="index"))

selection_qa = pd.DataFrame(
    [
        ("Candidate Spotify IDs", selection_report["candidate_ids"]),
        ("Pages with listener metrics", selection_report["metrics_rows"]),
        ("Pages without listener metrics", selection_report["metric_failures"]),
        ("Name mismatches sent to review", selection_report["identity_name_reviews"]),
        ("Accepted identities after review", selection_report["identity_accepted_rows"]),
        ("Orchestra rows excluded", selection_report["orchestra_rows_excluded"]),
        ("Redirect duplicates removed", selection_report["redirect_duplicate_rows"]),
        ("Selected groups", selection_report["selected_bands"]),
        ("Selected groups with resolved origins", selection_report["origin_resolved_bands"]),
    ],
    columns=["selection check", "count"],
)
display(selection_qa.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """strict_coverage = population_report["strict_mapping"]
extended_coverage = population_report["extended_mapping_sensitivity"]
coverage = pd.DataFrame(
    [
        {
            "mapping view": "Strict (main)",
            "mapped bands": strict_coverage["mapped_bands"],
            "band coverage": strict_coverage["mapped_band_share"],
            "captured-reach coverage": strict_coverage["mapped_listener_reach_share"],
            "mapped FUAs": strict_coverage["mapped_fuas"],
        },
        {
            "mapping view": "Reviewed extended (sensitivity)",
            "mapped bands": extended_coverage["mapped_bands"],
            "band coverage": extended_coverage["mapped_band_share"],
            "captured-reach coverage": extended_coverage["mapped_listener_reach_share"],
            "mapped FUAs": extended_coverage["mapped_fuas"],
        },
    ]
)
display(
    coverage.style.hide(axis="index").format(
        {
            "band coverage": "{:.1%}",
            "captured-reach coverage": "{:.1%}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 03. The selected top 100

Monthly listeners measure current global Spotify reach, not historical
importance or local listening. The chart shows the top 20 for orientation;
the complete table keeps the cutoff and origin decision auditable."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """figure_01_path = plot_top_selected_bands(
    bands,
    snapshot_date=snapshot_date,
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{figure_01_path.relative_to(ROOT)}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """top100_table = bands[
    [
        "popularity_rank",
        "spotify_name",
        "monthly_listeners",
        "formation_label",
        "origin_cluster",
        "origin_resolution",
    ]
].rename(
    columns={
        "popularity_rank": "Rank",
        "spotify_name": "Band / group",
        "monthly_listeners": "Captured monthly listeners",
        "formation_label": "Reported formation place",
        "origin_cluster": "Reviewed origin cluster",
        "origin_resolution": "Origin rule",
    }
)
display(
    top100_table.style.hide(axis="index").format(
        {"Captured monthly listeners": "{:,.0f}"}
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 04. Raw geographic concentration

Before population enters the calculation, London dominates the selected
sample: 44 of the 100 bands and almost half of captured listener reach. The
chart below moves from editorial origin clusters to the 20 strictly mapped
FUAs so the raw and normalized rankings later use the same geographic rows."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """origin_table = origins.head(15).rename(
    columns={
        "origin_cluster": "Origin cluster",
        "band_count": "Selected bands",
        "monthly_listeners_total": "Captured monthly listeners",
        "band_share": "Band share",
        "listener_share": "Reach share",
    }
)
display(
    origin_table.style.hide(axis="index").format(
        {
            "Captured monthly listeners": "{:,.0f}",
            "Band share": "{:.1%}",
            "Reach share": "{:.1%}",
        }
    )
)

figure_02_path = plot_raw_fua_reach(
    strict,
    snapshot_date=snapshot_date,
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{figure_02_path.relative_to(ROOT)}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 05. Population-adjusted result

The main adjusted rate is:

> sum of captured global monthly listeners for selected bands mapped to an FUA
> ÷ 2021 FUA population

This ratio can exceed one because the numerator is a global audience and the
denominator is a local population. It does not mean that each resident listens
to the band. Every strict-mapped FUA remains in the chart; hatching identifies
rates supported by only one selected band."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """figure_03_path = plot_population_adjusted_fua_reach(
    strict,
    snapshot_date=snapshot_date,
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{figure_03_path.relative_to(ROOT)}`."))

strict_table = ranked_strict[
    [
        "rank_by_listener_reach_per_resident",
        "study_city_label",
        "band_count",
        "population",
        "monthly_listeners_total",
        "top100_monthly_listeners_per_resident",
        "raw_reach_rank",
    ]
].rename(
    columns={
        "rank_by_listener_reach_per_resident": "Normalized rank",
        "study_city_label": "FUA",
        "band_count": "Selected bands",
        "population": "2021 population",
        "monthly_listeners_total": "Captured monthly listeners",
        "top100_monthly_listeners_per_resident": "Listeners / resident",
        "raw_reach_rank": "Raw reach rank",
    }
)
display(
    strict_table.style.hide(axis="index").format(
        {
            "2021 population": "{:,.0f}",
            "Captured monthly listeners": "{:,.0f}",
            "Listeners / resident": "{:.2f}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""**Reading the result.** Crawley moves from raw strict-FUA rank
{int(crawley["raw_reach_rank"])} to population-adjusted rank
{int(crawley["rank_by_listener_reach_per_resident"])}. Its numerator is one
band—**{", ".join(crawley_bands)}**. London moves from raw rank
{int(london["raw_reach_rank"])} to normalized rank
{int(london["rank_by_listener_reach_per_resident"])}; Manchester moves from
{int(manchester["raw_reach_rank"])} to
{int(manchester["rank_by_listener_reach_per_resident"])}. Population
normalization is therefore changing the question, not merely rescaling the
same league table."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 06. Multi-band stability diagnostic

The complete strict ranking above is the main population-adjusted result. This
diagnostic narrows the display to FUAs represented by at least two selected
bands. It does not retroactively remove Crawley or redefine the top 100; it
shows which high rates have support beyond a single superstar."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """figure_04_path = plot_multiband_stability(
    strict,
    snapshot_date=snapshot_date,
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{figure_04_path.relative_to(ROOT)}`."))

stable_table = (
    strict.loc[strict["band_count"].ge(2)]
    .sort_values("top100_monthly_listeners_per_resident", ascending=False)
    [
        [
            "study_city_label",
            "band_count",
            "top100_monthly_listeners_per_resident",
            "rank_by_listener_reach_per_resident",
        ]
    ]
    .rename(
        columns={
            "study_city_label": "FUA",
            "band_count": "Selected bands",
            "top100_monthly_listeners_per_resident": "Listeners / resident",
            "rank_by_listener_reach_per_resident": "Rank in full strict result",
        }
    )
)
display(
    stable_table.style.hide(axis="index").format(
        {"Listeners / resident": "{:.2f}"}
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""Among FUAs with at least two selected bands, the leading three
are **{", ".join(stable_top_three)}**. This is a more stable reading of the
popularity-first sample, but it still is not a balanced scene-depth study:
London contributes 44 selected bands while Oxford and Cambridge contribute
two each."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 07. What the denominator changes

The final chart compares the raw and population-adjusted ranks for exactly the
same 20 strict-mapped FUAs. It makes the denominator effect visible without
mixing in the broader reviewed mapping or dropping one-band cases."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """figure_05_path = plot_raw_vs_normalized_fua_ranks(
    strict,
    snapshot_date=snapshot_date,
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{figure_05_path.relative_to(ROOT)}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 08. Conclusion and limitations

The consolidated result is:

- **Raw scale:** London is the dominant origin in the selected top 100 and the
  largest strict-mapped FUA by captured reach.
- **Population-adjusted output:** Crawley ranks first because The Cure's global
  reach is large relative to Crawley's population.
- **Multi-band stability:** Oxford, Cambridge and Sheffield lead among FUAs
  with at least two selected bands.

These are complementary findings, not competing answers. Crawley is the most
interesting result precisely because it demonstrates both the value and the
risk of population normalization in a popularity-selected sample.

The conclusions remain narrow:

- The candidate frame inherits Wikidata coverage, classifications and Spotify
  ID quality; it is reproducible but not exhaustive.
- Monthly listeners are volatile current global reach, not historical impact,
  cultural influence, record sales or local listening.
- The top-100 cutoff creates selection sensitivity around the final qualifying
  bands.
- The strict FUA result maps 87 bands and 89.0% of captured reach. Unmapped
  bands are excluded from the denominator view rather than forced into a
  nearby FUA.
- Origin-to-FUA assignment is a boundary decision. Strict and broader reviewed
  mappings are kept separate.
- FUA population is from 2021 while Spotify reach was captured in 2026.
- One-band FUAs can rank highly from one globally dominant act. That is output
  per population, not scene depth."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## Appendix A. Extended mapping sensitivity

The broader view adds reviewed associations where an origin does not match an
FUA label directly. It covers more of the top 100 but embeds more geographic
judgment, so it is not promoted to the main chart. Crawley remains first."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """comparison = strict[
    [
        "fua_code",
        "study_city_label",
        "band_count",
        "top100_monthly_listeners_per_resident",
        "rank_by_listener_reach_per_resident",
    ]
].merge(
    extended[
        [
            "fua_code",
            "study_city_label",
            "band_count",
            "top100_monthly_listeners_per_resident",
            "rank_by_listener_reach_per_resident",
        ]
    ],
    on=["fua_code", "study_city_label"],
    how="outer",
    suffixes=("_strict", "_extended"),
)
comparison["band_count_change"] = (
    comparison["band_count_extended"].fillna(0)
    - comparison["band_count_strict"].fillna(0)
)
comparison["rank_change"] = (
    comparison["rank_by_listener_reach_per_resident_strict"]
    - comparison["rank_by_listener_reach_per_resident_extended"]
)
changed = comparison.loc[
    comparison["band_count_change"].ne(0)
    | comparison["rank_change"].fillna(0).ne(0)
].sort_values(
    "rank_by_listener_reach_per_resident_extended",
    na_position="last",
)
display(
    changed.style.hide(axis="index").format(
        {
            "band_count_strict": "{:.0f}",
            "band_count_extended": "{:.0f}",
            "top100_monthly_listeners_per_resident_strict": "{:.2f}",
            "top100_monthly_listeners_per_resident_extended": "{:.2f}",
            "rank_by_listener_reach_per_resident_strict": "{:.0f}",
            "rank_by_listener_reach_per_resident_extended": "{:.0f}",
            "band_count_change": "{:+.0f}",
            "rank_change": "{:+.0f}",
        },
        na_rep="—",
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""## Appendix B. Why there used to be two top-100 notebooks

The two predecessor notebooks are preserved as analysis history:

- `{predecessor_raw}` established the raw popularity-first selection and
  origin-concentration result.
- `{predecessor_adjusted}` added the FUA population denominator and surfaced
  Crawley, but presented itself as a separate companion.

This notebook resolves that presentation duality by placing the raw result,
the strict population-adjusted result and the multi-band stability diagnostic
in one narrative. It does not overwrite either predecessor, change the frozen
top 100, refresh Spotify data or alter the city-first final notebook."""
        )
    )

    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
            "analysis": {
                "kind": "canonical-popularity-first-origin-and-fua",
                "snapshot_id": snapshot_id,
                "frozen_inputs": [path.as_posix() for path in relative_paths.values()],
                "predecessors_preserved": [
                    predecessor_raw,
                    predecessor_adjusted,
                ],
                "published_notebook_modified": False,
            },
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, output_path)
    print(output_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
