#!/usr/bin/env python3
"""Build a dated, offline-executable popularity-first origin notebook."""

from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", required=True, type=Path)
    parser.add_argument("--origins", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
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
    audit_path = _relative(args.audit)
    report_path = _relative(args.report)
    output_path = (
        args.output
        or PROJECT_ROOT
        / "notebooks"
        / "experiments"
        / "06_uk_bands_top100_popularity_first.ipynb"
    ).resolve()
    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"{output_path} already exists; pass --force to rebuild it"
        )
    artifact_dir = Path(
        f"artifacts/top100_popularity_first/{args.snapshot_id}"
    )

    cells = []
    cells.append(
        nbf.v4.new_markdown_cell(
            """# Exploratory study: top 100 UK groups → origins

This is the separate **popularity-first** companion to the city-first scene
depth study. It asks where the most-listened-to UK musical groups in a frozen
candidate universe originated.

It does **not** rank city scene depth. Starting with popularity structurally
favours places that produced globally dominant acts, so these results describe
geographic concentration within this selected top 100 only."""
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
AUDIT_PATH = ROOT / "{audit_path.as_posix()}"
REPORT_PATH = ROOT / "{report_path.as_posix()}"
ARTIFACT_DIR = ROOT / "{artifact_dir.as_posix()}"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
origins = pd.read_csv(ORIGINS_PATH, keep_default_na=False)
audit = pd.read_csv(AUDIT_PATH, keep_default_na=False)
report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

assert len(bands) == 100
assert bands["popularity_rank"].tolist() == list(range(1, 101))
assert bands["returned_spotify_id"].nunique() == 100
assert origins["band_count"].sum() == 100
assert report["radiohead_selected"]

captured_at = bands["stats_extracted_at_utc"].iloc[0]
display(Markdown(
    f"**Frozen reach snapshot:** `{{SNAPSHOT_ID}}` ({{captured_at}}) · "
    f"**{{report['candidate_ids']:,}} candidate Spotify IDs** · "
    "**100 selected groups**"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 01. Selection rule and lineage

1. Start with the archived Wikidata query response for entities returned as UK
   musical groups, bands, or duos with a Spotify artist ID.
2. Capture current Spotify monthly listeners for those IDs.
3. Accept exact display-name matches plus explicitly reviewed aliases; reject
   unresolved name mismatches.
4. Collapse Spotify redirects to one canonical artist page and exclude
   orchestras from the “bands/groups” selection.
5. Select the 100 largest monthly-listener counts, then map their reported
   formation places to conservative origin clusters.

The source snapshot, every response, identity audit, and manual override are
retained. This notebook performs no network calls."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """lineage = pd.DataFrame(
    [
        {
            "stage": "Candidate universe",
            "frozen input": "data/raw/wikidata/uk_group_candidates_with_spotify_20260718T201100Z.json",
            "definition": "Archived Wikidata UK-group query response",
        },
        {
            "stage": "Reach capture",
            "frozen input": report["inputs"]["metrics"],
            "definition": "Spotify monthly listeners captured at one UTC time",
        },
        {
            "stage": "Identity review",
            "frozen input": str(AUDIT_PATH.relative_to(ROOT)),
            "definition": "Exact names, reviewed aliases, redirects, exclusions",
        },
        {
            "stage": "Origin review",
            "frozen input": "reference/popularity_first_overrides_20260718.csv",
            "definition": "Formation-place overrides with source URLs",
        },
    ]
)
display(lineage.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 02. Capture and identity quality

The counts below keep the incomplete and rejected rows visible. A missing
listener metric or mismatched name is not silently converted to zero."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """qa = pd.DataFrame(
    [
        ("Candidate Spotify IDs", report["candidate_ids"]),
        ("Pages with listener metrics", report["metrics_rows"]),
        ("Pages without a listener metric", report["metric_failures"]),
        ("Display-name mismatches sent to review", report["identity_name_reviews"]),
        ("Accepted identities after review", report["identity_accepted_rows"]),
        ("Orchestra rows excluded from selection pool", report["orchestra_rows_excluded"]),
        ("Redirect-duplicate rows removed", report["redirect_duplicate_rows"]),
        ("Selected groups", report["selected_bands"]),
        ("Selected groups with resolved origins", report["origin_resolved_bands"]),
    ],
    columns=["check", "count"],
)
display(qa.style.hide(axis="index"))

reviewed_exceptions = bands.loc[
    bands["identity_status"].eq("accepted_reviewed_alias")
    | bands["origin_resolution"].eq("reviewed_override"),
    [
        "popularity_rank",
        "band_name",
        "spotify_name",
        "identity_status",
        "formation_label",
        "origin_cluster",
        "reason",
        "source_url",
    ],
]
display(Markdown("**Reviewed exceptions that enter the selected 100**"))
display(reviewed_exceptions.style.hide(axis="index"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 03. The selected top 100

Monthly listeners are a volatile global reach measure, not a timeless quality
score. The full table is shown so the cutoff and every origin assignment remain
auditable."""
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
        "popularity_rank": "rank",
        "spotify_name": "group",
        "monthly_listeners": "monthly listeners",
        "formation_label": "reported formation place",
        "origin_cluster": "origin cluster",
        "origin_resolution": "origin rule",
    }
)
display(
    top100_table.style
    .hide(axis="index")
    .format({"monthly listeners": "{:,.0f}"})
)"""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """plot_top = bands.head(20).sort_values("monthly_listeners")
fig, ax = plt.subplots(figsize=(10, 7))
colors = ["#1f77b4" if origin == "London" else "#b8bec6" for origin in plot_top["origin_cluster"]]
ax.barh(plot_top["spotify_name"], plot_top["monthly_listeners"] / 1_000_000, color=colors)
ax.set(
    title="Top 20 selected UK groups by captured monthly listeners",
    xlabel="Monthly listeners (millions)",
    ylabel="",
)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
path = ARTIFACT_DIR / "01_top20_groups.png"
fig.savefig(path, dpi=180, bbox_inches="tight")
plt.show()
display(Markdown("*Blue denotes a London origin cluster; grey denotes every other origin.*"))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 04. Geographic concentration

Counts answer “how many of the selected 100 came from each origin?” Listener
share answers “how much of the selected sample’s captured reach came from each
origin?” Both use the same frozen top 100."""
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            """origin_top = origins.head(12).sort_values("band_count")
fig, ax = plt.subplots(figsize=(9, 6))
colors = ["#d95f02" if origin == "London" else "#b8bec6" for origin in origin_top["origin_cluster"]]
ax.barh(origin_top["origin_cluster"], origin_top["band_count"], color=colors)
ax.set(
    title="Most frequent origin clusters in the selected top 100",
    xlabel="Number of selected groups",
    ylabel="",
)
ax.spines[["top", "right"]].set_visible(False)
for y, value in enumerate(origin_top["band_count"]):
    ax.text(value + 0.35, y, f"{int(value)}", va="center")
fig.tight_layout()
path = ARTIFACT_DIR / "02_origin_band_counts.png"
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
        nbf.v4.new_code_cell(
            """london = origins.loc[origins["origin_cluster"].eq("London")].iloc[0]
manchester = origins.loc[origins["origin_cluster"].eq("Manchester")].iloc[0]
radiohead = bands.loc[bands["spotify_name"].eq("Radiohead")].iloc[0]
effective_origins_count = 1 / report["origin_hhi_band_count_resolved"]
effective_origins_reach = 1 / report["origin_hhi_reach_resolved"]

display(Markdown(
    f\"\"\"## 05. Result

- **London contributes {int(london['band_count'])} of the selected 100 groups**
  ({london['listener_share']:.1%} of captured reach).
- **Manchester contributes {int(manchester['band_count'])} groups**
  ({manchester['listener_share']:.1%} of reach).
- **Radiohead ranks #{int(radiohead['popularity_rank'])}** and maps from
  Abingdon-on-Thames to the **Oxford** origin cluster—the kind of small-place,
  giant-band case the city-first design intentionally cannot discover.
- The resolved-origin HHI is
  **{report['origin_hhi_band_count_resolved']:.3f} by group count** and
  **{report['origin_hhi_reach_resolved']:.3f} by listener reach**. Expressed as
  inverse-HHI “effective origins,” that is about
  **{effective_origins_count:.1f}** and **{effective_origins_reach:.1f}**
  equally sized origins respectively.

This is strong concentration within the popularity-selected sample. It is not
evidence that London has the deepest population-normalized scene; that is the
different question answered by the city-first study.\"\"\"
))"""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            """## 06. Limitations

- The candidate frame inherits Wikidata coverage, classifications, Spotify-ID
  errors, and multi-country edge cases. It is reproducible, but not exhaustive.
- “UK group” means the entity was returned by the archived UK-country query.
  Cases such as the Bee Gees or America demonstrate why nationality and
  formation place are not always equivalent.
- Monthly listeners change daily and measure global reach. Results belong to
  this snapshot only.
- Spotify’s web-player artist overview supplied the metric. The endpoint is
  undocumented; raw responses are retained for audit.
- Origin is usually the Wikidata formation place. A small reviewed override
  table fills missing or overly broad values, and conservative editorial
  clustering joins named districts to London, Manchester, or Oxford.
- HHI depends on how origins are clustered and on the top-100 cutoff.

The conclusion is therefore narrow: **among this frozen popularity-selected
top 100, origins and listener reach are geographically concentrated, especially
in London.**"""
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
                "kind": "popularity-first-origin-concentration",
                "snapshot_id": args.snapshot_id,
                "frozen_inputs": [
                    bands_path.as_posix(),
                    origins_path.as_posix(),
                    audit_path.as_posix(),
                    report_path.as_posix(),
                ],
            },
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, output_path)
    print(output_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
