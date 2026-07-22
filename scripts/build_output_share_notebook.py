#!/usr/bin/env python3
"""Build the top-200 music-output-share versus population experiment."""

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

from python_uk_bands.output_share import build_output_share_metrics  # noqa: E402


DEFAULT_SNAPSHOT_ID = "20260718T204522Z"
DEFAULT_POPULATION_SNAPSHOT_ID = "20260718T201304Z"
DEFAULT_TOP_N = 200


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default=DEFAULT_SNAPSHOT_ID)
    parser.add_argument(
        "--population-snapshot-id", default=DEFAULT_POPULATION_SNAPSHOT_ID
    )
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--bands", type=Path)
    parser.add_argument("--mapping-audit", type=Path)
    parser.add_argument("--population", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser


def _relative(path: Path) -> Path:
    return path.resolve().relative_to(PROJECT_ROOT)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prefix = f"popularity_first_top{args.top_n}_{args.snapshot_id}"
    bands_path = (
        args.bands
        or PROJECT_ROOT / "data" / "processed" / f"{prefix}_bands.csv"
    ).resolve()
    mapping_audit_path = (
        args.mapping_audit
        or PROJECT_ROOT
        / "data"
        / "interim"
        / f"{prefix}_fua_mapping_audit.csv"
    ).resolve()
    population_path = (
        args.population
        or PROJECT_ROOT
        / "data"
        / "processed"
        / (
            "uk_fua_population_2021_"
            f"{args.population_snapshot_id}.csv"
        )
    ).resolve()
    input_paths = {
        "bands": bands_path,
        "mapping_audit": mapping_audit_path,
        "population": population_path,
    }
    missing = [str(path) for path in input_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing frozen inputs: {missing}")

    output_path = (
        args.output
        or PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "snapshots"
        / (
            f"uk_bands_top{args.top_n}_output_share_vs_population_"
            f"{args.snapshot_id}.ipynb"
        )
    ).resolve()
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"{output_path} already exists; pass --force to rebuild it"
        )

    bands = pd.read_csv(bands_path, keep_default_na=False)
    mapping_audit = pd.read_csv(mapping_audit_path, keep_default_na=False)
    population = pd.read_csv(population_path, keep_default_na=False)
    if (
        len(bands) != args.top_n
        or bands["returned_spotify_id"].nunique() != args.top_n
    ):
        raise ValueError(
            f"The output-share experiment requires {args.top_n} unique bands"
        )
    if len(mapping_audit) != args.top_n:
        raise ValueError("Mapping audit must contain one row per selected band")

    strict_shares, strict_coverage = build_output_share_metrics(
        bands,
        mapping_audit,
        population,
        included_tiers={"strict"},
    )
    extended_shares, extended_coverage = build_output_share_metrics(
        bands,
        mapping_audit,
        population,
        included_tiers={"strict", "reviewed_extended"},
    )
    multi_band = extended_shares.loc[extended_shares["band_count"].ge(2)]
    breadth_leader = multi_band.sort_values(
        "band_output_quotient", ascending=False
    ).iloc[0]
    impact_leader = multi_band.sort_values(
        "follower_output_quotient", ascending=False
    ).iloc[0]
    london = extended_shares.loc[
        extended_shares["study_city_label"].eq("London")
    ].iloc[0]
    one_band_impact_leader = extended_shares.loc[
        extended_shares["band_count"].eq(1)
    ].sort_values("follower_output_quotient", ascending=False).iloc[0]
    snapshot_date = str(bands.iloc[0]["stats_extracted_at_utc"])[:10]

    relative_paths = {
        name: _relative(path).as_posix() for name, path in input_paths.items()
    }
    artifact_dir = Path(
        f"artifacts/experiments/top{args.top_n}_output_share_vs_population/"
        f"{args.snapshot_id}"
    )
    output_table_path = artifact_dir / "fua_output_shares_extended.csv"

    cells: list = []
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""# UK music output share versus population share

## tl;dr

This experiment reframes the existing per-capita question as a share comparison.
An output quotient of `1.0×` means that an FUA's share of selected music output
equals its share of the population; `2.0×` means twice the proportional output.

Using the reviewed extended mapping of the frozen top {args.top_n} catalogue:

- **{breadth_leader['study_city_label']}** has the largest selected-band quotient
  among FUAs represented by at least two bands: **{breadth_leader['band_output_quotient']:.2f}×**
  from {int(breadth_leader['band_count'])} selected bands.
- **{impact_leader['study_city_label']}** has the largest follower-share quotient
  in that multi-band group: **{impact_leader['follower_output_quotient']:.2f}×**.
- **London** represents {london['population_share']:.1%} of the population across
  the 83-FUA universe, {london['band_share']:.1%} of the selected bands and
  {london['follower_share']:.1%} of their followers.
- One-band results remain fragile: **{one_band_impact_leader['study_city_label']}**
  reaches **{one_band_impact_leader['follower_output_quotient']:.2f}×** on the
  follower quotient through one selected act.

The chart is descriptive, not a model of how music output should scale with city
size. Its rankings are mathematically identical to the corresponding per-capita
rankings when the same universes and denominators are used."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""## Context & Methods

The selected music universe is the frozen popularity-first top {args.top_n} of
eligible UK groups ranked by captured Spotify monthly listeners. Origins are
assigned to 2021 OECD/EU Functional Urban Areas (FUAs). The main view includes
both strict and reviewed-extended assignments because this maximizes coverage;
strict-only coverage is retained as a sensitivity check.

For output measure $M$ and population $P$, the quotient is:

$$
Q_i = \\frac{{M_i / M_{{UK}}}}{{P_i / P_{{UK}}}}
    = \\frac{{M_i/P_i}}{{M_{{UK}}/P_{{UK}}}}.
$$

The experiment calculates three versions:

1. **Band representation:** share of the selected top-{args.top_n} bands.
2. **Follower impact:** share of followers across those selected bands.
3. **Monthly-listener impact:** share of the frozen monthly-listener total.

The primary chart puts population share on the x-axis and follower share on the
y-axis. Its bubble area encodes selected-band count. Points above the parity
line have a follower output quotient greater than `1.0×`. A secondary chart
retains band share on the y-axis so breadth remains visible.

### Key Assumptions

- The population universe contains all 83 UK FUAs in the frozen OECD extract,
  including places with no selected bands.
- The music denominators contain all {args.top_n} selected bands and their full
  audience totals, including unmapped bands. Mapped shares therefore sum to
  less than 100% rather than being rescaled upward.
- Followers and monthly listeners are summed artist-level counts with unknown
  audience overlap; neither is a unique-person total.
- Current 2021 population is compared with bands formed across many decades.
- The top-{args.top_n} cutoff and Spotify-based candidate frame are measurement
  choices, not a census of British music."""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## Data"))
    cells.append(
        nbf.v4.new_code_cell(
            f"""from pathlib import Path

import pandas as pd
from IPython.display import Markdown, display

ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path.cwd().parents)
        if (candidate / "{relative_paths['bands']}").exists()
    ),
    None,
)
if ROOT is None:
    raise FileNotFoundError("Could not locate the uk-music-cities repository root")

import sys
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.output_share import (
    build_output_share_metrics,
    plot_band_share_vs_population_share,
    plot_follower_share_vs_population_share,
)

SNAPSHOT_ID = "{args.snapshot_id}"
TOP_N = {args.top_n}
BANDS_PATH = ROOT / "{relative_paths['bands']}"
MAPPING_AUDIT_PATH = ROOT / "{relative_paths['mapping_audit']}"
POPULATION_PATH = ROOT / "{relative_paths['population']}"
CHART_OUTPUT_DIR = ROOT / "{artifact_dir.as_posix()}"
OUTPUT_TABLE_PATH = ROOT / "{output_table_path.as_posix()}"

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
mapping_audit = pd.read_csv(MAPPING_AUDIT_PATH, keep_default_na=False)
population = pd.read_csv(POPULATION_PATH, keep_default_na=False)

strict_shares, strict_coverage = build_output_share_metrics(
    bands,
    mapping_audit,
    population,
    included_tiers={{"strict"}},
)
shares, coverage = build_output_share_metrics(
    bands,
    mapping_audit,
    population,
    included_tiers={{"strict", "reviewed_extended"}},
)

CHART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
shares.to_csv(OUTPUT_TABLE_PATH, index=False)

coverage_table = pd.DataFrame(
    [
        {{
            "Mapping": "Strict",
            "Mapped bands": strict_coverage["mapped_bands"],
            "Band share": strict_coverage["mapped_band_share"],
            "Follower share": strict_coverage["mapped_follower_share"],
            "Monthly-listener share": strict_coverage["mapped_monthly_listener_share"],
            "Represented FUAs": strict_coverage["mapped_fuas"],
        }},
        {{
            "Mapping": "Strict + reviewed extended",
            "Mapped bands": coverage["mapped_bands"],
            "Band share": coverage["mapped_band_share"],
            "Follower share": coverage["mapped_follower_share"],
            "Monthly-listener share": coverage["mapped_monthly_listener_share"],
            "Represented FUAs": coverage["mapped_fuas"],
        }},
    ]
)
display(
    coverage_table.style.hide(axis="index").format(
        {{
            "Band share": "{{:.1%}}",
            "Follower share": "{{:.1%}}",
            "Monthly-listener share": "{{:.1%}}",
        }}
    )
)
display(Markdown(f"Saved the full 83-FUA table to `{{OUTPUT_TABLE_PATH.relative_to(ROOT)}}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """The primary reviewed-extended view improves output coverage while
retaining the full catalogue denominator. The stricter view is useful for
checking whether reviewed boundary assignments change the interpretation."""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## Results"))
    cells.append(
        nbf.v4.new_markdown_cell(
            """### Follower-share chart

Follower share supplies the vertical position and selected-band count supplies
bubble area. Marker treatment distinguishes one-band cases from FUAs with at
least two selected bands. Zero-output FUAs remain in the population denominator
and exported table but cannot be positioned on a log y-axis."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f"""chart_path = plot_follower_share_vs_population_share(
    shares,
    snapshot_date="{snapshot_date}",
    selected_count=TOP_N,
    mapping_label="strict + reviewed-extended FUA mapping",
    output_dir=CHART_OUTPUT_DIR,
)
display(Markdown(f"Exported to `{{chart_path.relative_to(ROOT)}}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """The vertical position now measures audience impact directly. A
point above the line contributes a larger follower share than its population
share, while bubble area shows how many selected bands contribute to that
result."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell("### Exact quotients and concentration")
    )
    cells.append(
        nbf.v4.new_code_cell(
            """represented = (
    shares.loc[shares["band_count"].gt(0)]
    .sort_values(
        ["follower_output_quotient", "band_output_quotient"],
        ascending=False,
    )
    .head(20)
    [
        [
            "study_city_label",
            "band_count",
            "population_share",
            "band_share",
            "band_output_quotient",
            "follower_share",
            "follower_output_quotient",
            "largest_band_by_followers",
            "largest_band_follower_share",
        ]
    ]
    .rename(
        columns={
            "study_city_label": "FUA",
            "band_count": "Bands",
            "population_share": "Population share",
            "band_share": "Band share",
            "band_output_quotient": "Band quotient",
            "follower_share": "Follower share",
            "follower_output_quotient": "Follower quotient",
            "largest_band_by_followers": "Largest band",
            "largest_band_follower_share": "Largest-band share",
        }
    )
)
display(
    represented.style.hide(axis="index").format(
        {
            "Population share": "{:.2%}",
            "Band share": "{:.2%}",
            "Band quotient": "{:.2f}×",
            "Follower share": "{:.2%}",
            "Follower quotient": "{:.2f}×",
            "Largest-band share": "{:.1%}",
        }
    )
)"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """### Band-representation companion

The companion chart returns to selected-band share on the y-axis. It measures
breadth rather than audience impact. One-band FUAs necessarily align at
`1 / TOP_N`; this discrete row is a property of the count metric, not a plotting
error."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            f"""band_chart_path = plot_band_share_vs_population_share(
    shares,
    snapshot_date="{snapshot_date}",
    selected_count=TOP_N,
    mapping_label="strict + reviewed-extended FUA mapping",
    output_dir=CHART_OUTPUT_DIR,
    filename="chart_02_band_share_vs_population_share.png",
)
display(Markdown(f"Exported to `{{band_chart_path.relative_to(ROOT)}}`."))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell("### Calculation checks")
    )
    cells.append(
        nbf.v4.new_code_cell(
            """assert len(shares) == coverage["population_fuas"] == 83
assert coverage["mapped_bands"] == int(shares["band_count"].sum())
assert abs(shares["band_share"].sum() - coverage["mapped_band_share"]) < 1e-12
assert abs(shares["follower_share"].sum() - coverage["mapped_follower_share"]) < 1e-12

national_band_rate = TOP_N / shares["population"].sum()
relative_per_capita_rate = (
    shares["band_count"] / shares["population"] / national_band_rate
)
assert (
    shares["band_output_quotient"] - relative_per_capita_rate
).abs().max() < 1e-12

national_follower_rate = bands["followers"].sum() / shares["population"].sum()
relative_follower_rate = (
    shares["followers_total"] / shares["population"] / national_follower_rate
)
assert (
    shares["follower_output_quotient"] - relative_follower_rate
).abs().max() < 1e-12

assert shares.loc[shares["band_count"].eq(0), "band_share"].eq(0).all()
assert shares.loc[shares["band_count"].eq(0), "band_output_quotient"].eq(0).all()
assert coverage["mapped_band_share"] < 1
assert coverage["mapped_follower_share"] < 1

print(
    "Checks passed: 83-FUA population denominator, full-catalogue output "
    "denominators, zero-output retention, and share/per-capita identity."
)"""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## Takeaways"))
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""1. **The share framing works.** It makes the expected-output
   comparison explicit: the diagonal is the national-average per-capita rate.
2. **Breadth and audience impact differ.** {breadth_leader['study_city_label']}
   leads the multi-band band-count quotient at
   {breadth_leader['band_output_quotient']:.2f}×, while
   {impact_leader['study_city_label']} leads the corresponding follower quotient
   at {impact_leader['follower_output_quotient']:.2f}×.
3. **Large cities are not automatically penalized.** London has
   {london['band_output_quotient']:.2f}× its population-proportional share of
   selected bands and {london['follower_output_quotient']:.2f}× its proportional
   follower share.
4. **Small cells still dominate some quotients.** One-band and low-count FUAs
   should remain visible but explicitly marked; the largest-band share is an
   essential concentration guardrail.
5. **This is a presentation improvement, not a new causal estimator.** A later
   log-log or count model should test whether output scales linearly with
   population rather than assuming the parity line is the correct expectation.

### Status

**Share with caveats.** The calculations are internally reproducible and the
chart honestly represents the frozen data, but the catalogue, origin mapping,
current-versus-historical time mismatch and superstar concentration prevent a
definitive ranking of UK music cities."""
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
                "kind": "music-output-share-versus-population-experiment",
                "snapshot_id": args.snapshot_id,
                "catalogue_size": args.top_n,
                "primary_mapping": ["strict", "reviewed_extended"],
                "frozen_inputs": list(relative_paths.values()),
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
