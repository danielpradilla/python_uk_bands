#!/usr/bin/env python3
"""Build an offline population-adjusted companion to the top-100 notebook."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", required=True, type=Path)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--mapping-audit", required=True, type=Path)
    parser.add_argument("--strict", required=True, type=Path)
    parser.add_argument("--extended", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def _relative(path: Path) -> Path:
    return path.resolve().relative_to(PROJECT_ROOT)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bands_path = _relative(args.bands)
    origins_path = _relative(args.origins)
    mapping_audit_path = _relative(args.mapping_audit)
    strict_path = _relative(args.strict)
    extended_path = _relative(args.extended)
    report_path = _relative(args.report)
    output_path = (
        args.output
        or PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "snapshots"
        / (
            "uk_bands_top100_popularity_first_population_adjusted_"
            f"{args.snapshot_id}.ipynb"
        )
    ).resolve()
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"{output_path} already exists; pass --force to rebuild it"
        )
    artifact_dir = Path(
        f"artifacts/top100_popularity_first_population_adjusted/"
        f"{args.snapshot_id}"
    )

    cells = []
    cells.append(
        nbf.v4.new_markdown_cell(
            """# Top 100 UK groups: population-adjusted origin analysis

This companion keeps the original popularity-first concentration analysis and
adds a population denominator. It asks:

> Relative to the size of an origin’s Functional Urban Area, how much of this
> frozen top 100 did the area produce?

This is an **output-per-population sensitivity analysis**, not a scene-depth
ranking. A city can rank highly because one globally dominant band clears the
top-100 cutoff."""
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
    raise FileNotFoundError("Could not locate the uk-music-cities repository root")

SNAPSHOT_ID = "{args.snapshot_id}"
BANDS_PATH = ROOT / "{bands_path.as_posix()}"
ORIGINS_PATH = ROOT / "{origins_path.as_posix()}"
MAPPING_AUDIT_PATH = ROOT / "{mapping_audit_path.as_posix()}"
STRICT_PATH = ROOT / "{strict_path.as_posix()}"
EXTENDED_PATH = ROOT / "{extended_path.as_posix()}"
REPORT_PATH = ROOT / "{report_path.as_posix()}"
ARTIFACT_DIR = ROOT / "{artifact_dir.as_posix()}"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
origins = pd.read_csv(ORIGINS_PATH, keep_default_na=False)
mapping_audit = pd.read_csv(MAPPING_AUDIT_PATH, keep_default_na=False)
strict = pd.read_csv(STRICT_PATH, keep_default_na=False)
extended = pd.read_csv(EXTENDED_PATH, keep_default_na=False)
report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

assert len(bands) == 100
assert bands["returned_spotify_id"].nunique() == 100
assert origins["band_count"].sum() == 100
assert len(mapping_audit) == 100
assert strict["fua_code"].nunique() == len(strict)
assert (strict["population"] > 0).all()
assert (
    strict["top100_monthly_listeners_per_resident"]
    .sort_values(ascending=False)
    .tolist()
    == strict["top100_monthly_listeners_per_resident"].tolist()
)

captured_at = bands["stats_extracted_at_utc"].iloc[0]
strict_coverage = report["strict_mapping"]
extended_coverage = report["extended_mapping_sensitivity"]
display(Markdown(
    f"**Frozen Spotify snapshot:** `{{SNAPSHOT_ID}}` ({{captured_at}}) · "
    f"**Population:** OECD/EU FUA, {{report['population_year']}} · "
    f"**Strict mapping:** {{strict_coverage['mapped_bands']}}/100 bands "
    f"({{strict_coverage['mapped_listener_reach_share']:.1%}} of reach)"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 1. What changes when population enters the denominator?

The original analysis measures concentration inside a popularity-selected
sample. This companion retains that result, then calculates two rates:

- **Top-100 bands per million residents** = selected band count ÷ 2021 FUA
  population × 1,000,000.
- **Top-100 monthly listeners per resident** = the selected bands’ captured
  global monthly listeners ÷ 2021 FUA population.

“Listeners per resident” is a normalization ratio. It is **not** the share of
local residents listening, so it can exceed one. The numerator is global
Spotify reach; only the denominator is local."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """lineage = pd.DataFrame(
    [
        {
            "stage": "Popularity selection",
            "frozen input": report["inputs"]["bands"],
            "role": "The same reviewed top 100 as the original analysis",
        },
        {
            "stage": "Raw origin concentration",
            "frozen input": report["inputs"]["origins"],
            "role": "Unadjusted count and listener-share baseline",
        },
        {
            "stage": "Origin → FUA decisions",
            "frozen input": report["inputs"]["mapping"],
            "role": "Strict assignments, sensitivity assignments, exclusions",
        },
        {
            "stage": "Population denominator",
            "frozen input": report["inputs"]["population"],
            "role": "2021 OECD/EU Functional Urban Area population",
        },
    ]
)
display(lineage.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 2. Keep the raw result visible

Population adjustment answers a different question, so the raw geographic
concentration is not discarded. London still supplies the largest number of
bands in the selected 100."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """origin_top = origins.head(12).sort_values("band_count")
fig, ax = plt.subplots(figsize=(9, 6))
colors = [
    "#d95f02" if origin == "London" else "#b8bec6"
    for origin in origin_top["origin_cluster"]
]
ax.barh(origin_top["origin_cluster"], origin_top["band_count"], color=colors)
ax.set(
    title="Raw origin concentration in the selected top 100",
    xlabel="Number of selected groups",
    ylabel="",
)
ax.spines[["top", "right"]].set_visible(False)
for y, value in enumerate(origin_top["band_count"]):
    ax.text(value + 0.35, y, f"{int(value)}", va="center")
fig.tight_layout()
path = ARTIFACT_DIR / "01_raw_origin_counts.png"
fig.savefig(path, dpi=180, bbox_inches="tight")
plt.show()

display(
    origins.head(15).style
    .hide(axis="index")
    .format(
        {
            "monthly_listeners_total": "{:,.0f}",
            "band_share": "{:.1%}",
            "listener_share": "{:.1%}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 3. Denominator coverage

The main result uses only exact FUA label matches and three transparent label
aliases: Bath, Brighton and Dundee. It does not silently force every formation
place into the nearest large city."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """coverage = pd.DataFrame(
    [
        {
            "view": "Strict (main)",
            "mapped bands": strict_coverage["mapped_bands"],
            "band coverage": strict_coverage["mapped_band_share"],
            "listener-reach coverage": strict_coverage["mapped_listener_reach_share"],
            "mapped FUAs": strict_coverage["mapped_fuas"],
        },
        {
            "view": "Extended (sensitivity)",
            "mapped bands": extended_coverage["mapped_bands"],
            "band coverage": extended_coverage["mapped_band_share"],
            "listener-reach coverage": extended_coverage["mapped_listener_reach_share"],
            "mapped FUAs": extended_coverage["mapped_fuas"],
        },
    ]
)
display(
    coverage.style
    .hide(axis="index")
    .format(
        {
            "band coverage": "{:.1%}",
            "listener-reach coverage": "{:.1%}",
        }
    )
)

strict_exclusions = mapping_audit.loc[
    mapping_audit["mapping_tier"].ne("strict"),
    [
        "spotify_name",
        "origin_cluster",
        "monthly_listeners",
        "mapping_tier",
        "study_city_label",
        "notes",
    ],
].sort_values("monthly_listeners", ascending=False)
display(Markdown("**Bands excluded from the strict denominator view**"))
display(
    strict_exclusions.style
    .hide(axis="index")
    .format({"monthly_listeners": "{:,.0f}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 4. Main result: captured reach per resident

Every strict-mapped FUA remains in the result. Bars supported by two or more
bands are coloured; one-band results are grey and explicitly labelled."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """plot_strict = strict.head(20).sort_values(
    "top100_monthly_listeners_per_resident"
)
fig, ax = plt.subplots(figsize=(10, 8))
colors = [
    "#1f77b4" if count >= 2 else "#b8bec6"
    for count in plot_strict["band_count"]
]
ax.barh(
    plot_strict["study_city_label"],
    plot_strict["top100_monthly_listeners_per_resident"],
    color=colors,
)
ax.set(
    title="Top-100 captured listener reach per FUA resident",
    xlabel="Sum of captured global monthly listeners / 2021 FUA population",
    ylabel="",
)
ax.spines[["top", "right"]].set_visible(False)
for y, (_, row) in enumerate(plot_strict.iterrows()):
    ax.text(
        row["top100_monthly_listeners_per_resident"] + 2,
        y,
        f"n={int(row['band_count'])}",
        va="center",
        fontsize=9,
    )
fig.tight_layout()
path = ARTIFACT_DIR / "02_population_adjusted_all_fuas.png"
fig.savefig(path, dpi=180, bbox_inches="tight")
plt.show()
display(Markdown(
    "*Blue: at least two selected bands. Grey: one selected band. "
    "n is the selected-band count behind the rate.*"
))

strict_table = strict[
    [
        "rank_by_listener_reach_per_resident",
        "study_city_label",
        "band_count",
        "population",
        "monthly_listeners_total",
        "top100_monthly_listeners_per_resident",
        "top100_bands_per_million_residents",
    ]
].rename(
    columns={
        "rank_by_listener_reach_per_resident": "rank",
        "study_city_label": "FUA",
        "band_count": "selected bands",
        "monthly_listeners_total": "captured listeners",
        "top100_monthly_listeners_per_resident": "listeners / resident",
        "top100_bands_per_million_residents": "bands / million",
    }
)
display(
    strict_table.style
    .hide(axis="index")
    .format(
        {
            "population": "{:,.0f}",
            "captured listeners": "{:,.0f}",
            "listeners / resident": "{:.2f}",
            "bands / million": "{:.2f}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 5. Stability view: require at least two selected bands

The full ranking above is the main result. This diagnostic removes no
observations from the calculations; it simply focuses the display on FUAs whose
rate is not determined by a single band."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """stable = (
    strict.loc[strict["band_count"].ge(2)]
    .sort_values("top100_monthly_listeners_per_resident")
)
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(
    stable["study_city_label"],
    stable["top100_monthly_listeners_per_resident"],
    color="#1f77b4",
)
ax.set(
    title="Population-adjusted reach where at least two bands qualify",
    xlabel="Sum of captured global monthly listeners / 2021 FUA population",
    ylabel="",
)
ax.spines[["top", "right"]].set_visible(False)
for y, (_, row) in enumerate(stable.iterrows()):
    ax.text(
        row["top100_monthly_listeners_per_resident"] + 1.5,
        y,
        f"n={int(row['band_count'])}",
        va="center",
        fontsize=9,
    )
fig.tight_layout()
path = ARTIFACT_DIR / "03_population_adjusted_minimum_two_bands.png"
fig.savefig(path, dpi=180, bbox_inches="tight")
plt.show()"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """top_fua = strict.iloc[0]
top_fua_bands = mapping_audit.loc[
    mapping_audit["fua_code"].eq(top_fua["fua_code"])
    & mapping_audit["mapping_tier"].eq("strict"),
    "spotify_name",
].tolist()
stable_ranked = (
    strict.loc[strict["band_count"].ge(2)]
    .sort_values("rank_by_listener_reach_per_resident")
)
stable_names = stable_ranked.head(5)["study_city_label"].tolist()

display(Markdown(
    f\"\"\"## 6. Interpretation

- **{top_fua['study_city_label']} ranks first in the complete strict view**, but
  its rate is based on one band: **{', '.join(top_fua_bands)}**. That is a
  superstar result, not evidence of broad scene depth.
- Among FUAs represented by at least two selected bands, the first five are
  **{', '.join(stable_names)}**.
- London’s raw scale remains exceptional, but its much larger population moves
  it below several smaller FUAs after normalization.
- The two rates describe representation within this particular top 100. They
  should not be read as estimates of all musical output or local listening.
\"\"\"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 7. Extended mapping sensitivity

The extended view adds seven reviewed associations for places that do not match
an FUA label directly. These are deliberately treated as sensitivity
assignments, not official boundary facts."""
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
    changed.style
    .hide(axis="index")
    .format(
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
            """## 8. Conclusion and limitations

Population adjustment is useful here, but it changes the estimand. The raw
view answers where the selected top 100 came from; the adjusted view answers
how much representation and captured global reach those selected bands account
for relative to FUA population.

The result is informative precisely because it exposes superstar cases:
Crawley, Bath and Eastbourne rise sharply on one qualifying band. For a more
scene-like reading, the at-least-two-band diagnostic is more stable, but it is
still conditional on a popularity-selected top 100.

Further limitations:

- The top-100 frame inherits Wikidata coverage, identity decisions and a
  volatile Spotify snapshot.
- Thirteen bands are outside the strict denominator view. Six remain unmapped
  even after the extended review.
- Origin-to-FUA assignment is a boundary problem; the strict and extended
  results are separated so that judgment remains visible.
- FUA population is 2021 population; Spotify reach is captured in 2026.
- A deeper city-scene study needs a balanced catalogue per city. That remains
  the purpose of the separate city-first analysis."""
        )
    )

    frozen_inputs = [
        bands_path.as_posix(),
        origins_path.as_posix(),
        mapping_audit_path.as_posix(),
        strict_path.as_posix(),
        extended_path.as_posix(),
        report_path.as_posix(),
    ]
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
                "kind": "popularity-first-population-adjusted-sensitivity",
                "snapshot_id": args.snapshot_id,
                "frozen_inputs": frozen_inputs,
                "preserves_original_popularity_first_notebook": True,
            },
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, output_path)
    print(output_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
