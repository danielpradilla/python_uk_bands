#!/usr/bin/env python3
"""Build the executed-ready top-1,000 UK follower maps notebook."""

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

from python_uk_bands.follower_maps import prepare_top_city_map_data  # noqa: E402
from python_uk_bands.output_share import build_output_share_metrics  # noqa: E402


SNAPSHOT_ID = "20260718T204522Z"
POPULATION_SNAPSHOT_ID = "20260718T201304Z"
ASSET_DATE = "20260723"
TOP_CITY_COUNT = 10


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _paths() -> dict[str, Path]:
    return {
        "bands": PROJECT_ROOT
        / f"data/processed/popularity_first_top1000_{SNAPSHOT_ID}_bands.csv",
        "mapping": PROJECT_ROOT
        / f"data/interim/popularity_first_top1000_{SNAPSHOT_ID}_fua_mapping_audit.csv",
        "population": PROJECT_ROOT
        / (
            "data/processed/uk_fua_population_2021_"
            f"{POPULATION_SNAPSHOT_ID}.csv"
        ),
        "coordinates": PROJECT_ROOT
        / "reference"
        / f"top1000_fua_map_coordinates_{ASSET_DATE}.csv",
        "photos": PROJECT_ROOT
        / "reference"
        / f"top1000_city_band_photo_manifest_{ASSET_DATE}.csv",
        "capture_metadata": PROJECT_ROOT
        / "reference"
        / f"top1000_follower_map_asset_capture_{ASSET_DATE}.json",
        "geography": PROJECT_ROOT
        / "data/raw/geography"
        / f"natural_earth_50m_united_kingdom_{ASSET_DATE}.geojson",
        "artifacts": PROJECT_ROOT
        / "artifacts/experiments/top1000_follower_maps"
        / SNAPSHOT_ID,
        "notebook": PROJECT_ROOT
        / "notebooks/experiments"
        / "15_uk_bands_top1000_follower_maps.ipynb",
    }


def _summary(paths: dict[str, Path]) -> tuple[pd.DataFrame, dict[str, float | int]]:
    bands = pd.read_csv(paths["bands"], keep_default_na=False)
    mapping = pd.read_csv(paths["mapping"], keep_default_na=False)
    population = pd.read_csv(paths["population"], keep_default_na=False)
    coordinates = pd.read_csv(paths["coordinates"], keep_default_na=False)
    photos = pd.read_csv(paths["photos"], keep_default_na=False)
    shares, coverage = build_output_share_metrics(
        bands,
        mapping,
        population,
        included_tiers={"strict", "reviewed_extended"},
    )
    map_data = prepare_top_city_map_data(
        shares,
        coordinates,
        photos,
        top_city_count=TOP_CITY_COUNT,
    )
    return map_data, coverage


def build_notebook(paths: dict[str, Path]) -> nbf.NotebookNode:
    map_data, coverage = _summary(paths)
    london = map_data.loc[map_data["study_city_label"].eq("London")].iloc[0]
    manchester = map_data.loc[
        map_data["study_city_label"].eq("Manchester")
    ].iloc[0]
    exeter = map_data.loc[map_data["study_city_label"].eq("Exeter")].iloc[0]
    crawley = map_data.loc[map_data["study_city_label"].eq("Crawley")].iloc[0]
    sheffield = map_data.loc[
        map_data["study_city_label"].eq("Sheffield")
    ].iloc[0]
    leeds = map_data.loc[map_data["study_city_label"].eq("Leeds")].iloc[0]
    top_share_mapped = map_data["share_of_mapped_followers"].sum()
    top_share_selected = map_data["follower_share"].sum()
    london_vs_manchester = london["followers_total"] / manchester["followers_total"]

    cells: list[nbf.NotebookNode] = []
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""# Top-1,000 follower geography: city bubbles and leading-band photos

## tl;dr

- **London leads by a large margin:** its mapped bands sum to **{london['followers_total'] / 1_000_000:.0f} million** Spotify followers, **{london_vs_manchester:.1f}×** Manchester's total.
- The top {TOP_CITY_COUNT} FUAs contain **{top_share_mapped:.1%} of followers allocated to mapped cities**, or **{top_share_selected:.1%} of the full selected top-1,000 follower denominator**.
- Map 1 uses bubble **area** in direct proportion to each city's combined follower total.
- Map 2 keeps exactly the same cities, positions and area scale. Its photo is only the **largest-followed selected band** in that city: Coldplay is {london['largest_band_follower_share']:.1%} of London's total, while Muse is {exeter['largest_band_follower_share']:.1%} of Exeter's and The Cure is {crawley['largest_band_follower_share']:.0%} of Crawley's.
- Map 3 shows the **follower output quotient**—the “punching above weight” multiplier. Crawley reaches **{crawley['follower_output_quotient']:.2f}×**, while Leeds is **{leeds['follower_output_quotient']:.2f}×**.

**Bottom line:** Map 1 shows absolute follower reach, Map 3 shows population-relative overperformance, and the photo version is an identity layer rather than a complete picture of each city's scene."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            r"""## 01. Context & Methods

This experiment maps the follower output already defined in the top-1,000 share analysis. For FUA (i), the metric is

$$
F_i = \sum_{b \in i} \text{Spotify followers}_b.
$$

Only strict and reviewed-extended FUA assignments are allocated. Unresolved or excluded bands stay in the selected-catalogue denominator and are not redistributed. A "combined follower" is a summed account-to-band follow relationship, **not a unique person**: one Spotify user may follow several bands.

Bubble area is (A_i = F_i / 100{,}000) points², so a city with twice the follower total gets twice the bubble area. The centre pin is the named city's Wikidata coordinate and stands in for its whole OECD/EU Functional Urban Area; it is not an FUA centroid or boundary.

The photo in Map 2 is selected deterministically: the mapped band with the largest Spotify follower count in that FUA. It is an identity cue, not a weighted collage and not evidence that one band caused the city's total.

Map 3 uses the follower output quotient:

$$
Q_i = \frac{F_i / F_{\text{selected UK top 1,000}}}{P_i / P_{\text{all 83 UK FUAs}}}.
$$

At **1×**, follower share equals population share. Above 1× is punching above population weight; below 1× is under the proportional benchmark. Bubble area is proportional to `Q_i`; filled circles are at or above 1× and open circles are below it. The displayed set remains the same top ten chosen by raw combined followers.

### Frozen supporting assets

- UK outline: Natural Earth 1:50m Admin 0, public domain.
- City coordinates: Wikidata `P625`, CC0.
- Band photos: local Wikimedia Commons thumbnails; the per-file creator, page and licence are listed after the maps.
"""
        )
    )
    setup_code = f'''from pathlib import Path
import hashlib
import json
import sys

import pandas as pd
from IPython.display import Image, Markdown, display

ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path.cwd().parents)
        if (candidate / "{_relative(paths['bands'])}").exists()
    ),
    None,
)
if ROOT is None:
    raise FileNotFoundError("Could not locate the uk-music-cities repository root")

SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.follower_maps import (
    load_geojson,
    plot_city_follower_bubbles,
    plot_city_follower_output_quotient,
    plot_city_follower_photo_bubbles,
    prepare_top_city_map_data,
)
from python_uk_bands.output_share import build_output_share_metrics

SNAPSHOT_ID = "{SNAPSHOT_ID}"
TOP_CITY_COUNT = {TOP_CITY_COUNT}
BANDS_PATH = ROOT / "{_relative(paths['bands'])}"
MAPPING_PATH = ROOT / "{_relative(paths['mapping'])}"
POPULATION_PATH = ROOT / "{_relative(paths['population'])}"
COORDINATE_PATH = ROOT / "{_relative(paths['coordinates'])}"
PHOTO_MANIFEST_PATH = ROOT / "{_relative(paths['photos'])}"
CAPTURE_METADATA_PATH = ROOT / "{_relative(paths['capture_metadata'])}"
GEOGRAPHY_PATH = ROOT / "{_relative(paths['geography'])}"
ARTIFACT_DIR = ROOT / "{_relative(paths['artifacts'])}"

bands = pd.read_csv(BANDS_PATH, keep_default_na=False)
mapping_audit = pd.read_csv(MAPPING_PATH, keep_default_na=False)
population = pd.read_csv(POPULATION_PATH, keep_default_na=False)
coordinates = pd.read_csv(COORDINATE_PATH, keep_default_na=False)
photo_manifest = pd.read_csv(PHOTO_MANIFEST_PATH, keep_default_na=False)
with CAPTURE_METADATA_PATH.open(encoding="utf-8") as handle:
    capture_metadata = json.load(handle)

shares, coverage = build_output_share_metrics(
    bands,
    mapping_audit,
    population,
    included_tiers={{"strict", "reviewed_extended"}},
)
map_data = prepare_top_city_map_data(
    shares,
    coordinates,
    photo_manifest,
    top_city_count=TOP_CITY_COUNT,
)
geography = load_geojson(GEOGRAPHY_PATH)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

assert len(bands) == bands["returned_spotify_id"].nunique() == 1000
assert coverage["mapped_bands"] == int(shares["band_count"].sum()) == 660
assert coverage["population_fuas"] == len(shares) == 83
assert map_data["study_city_label"].tolist() == {map_data['study_city_label'].tolist()!r}
assert file_sha256(GEOGRAPHY_PATH) == capture_metadata["natural_earth"]["sha256"]
for photo in map_data.itertuples(index=False):
    assert file_sha256(ROOT / photo.local_path) == photo.image_sha256

MAP_DATA_PATH = ARTIFACT_DIR / "top_city_follower_map_data.csv"
map_data.to_csv(MAP_DATA_PATH, index=False)

coverage_table = pd.DataFrame(
    [
        {{"Measure": "Selected bands", "Value": f"{{coverage['selected_bands']:,}}"}},
        {{"Measure": "Mapped bands", "Value": f"{{coverage['mapped_bands']:,}} ({{coverage['mapped_band_share']:.1%}})"}},
        {{"Measure": "Mapped follower coverage", "Value": f"{{coverage['mapped_follower_share']:.1%}}"}},
        {{"Measure": "Population universe", "Value": f"{{coverage['population_fuas']}} FUAs"}},
        {{"Measure": "Mapped FUAs", "Value": f"{{coverage['mapped_fuas']}}"}},
        {{"Measure": "Displayed FUAs", "Value": f"{{TOP_CITY_COUNT}}"}},
    ]
)
display(coverage_table.style.hide(axis="index"))
display(Markdown(f"Saved the joined map frame to `{{MAP_DATA_PATH.relative_to(ROOT)}}`."))
'''
    cells.append(nbf.v4.new_markdown_cell("## 02. Data"))
    cells.append(nbf.v4.new_code_cell(setup_code))
    cells.append(
        nbf.v4.new_markdown_cell(
            "### The ten displayed cities\n\n"
            "The ranking is based on the sum across all mapped selected bands, "
            "not on the pictured band's followers alone."
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''ranking = map_data[
    [
        "rank_by_followers",
        "study_city_label",
        "followers_total",
        "band_count",
        "follower_output_quotient",
        "largest_band_by_followers",
        "largest_band_follower_share",
    ]
].rename(
    columns={
        "rank_by_followers": "Rank",
        "study_city_label": "FUA",
        "followers_total": "Combined followers",
        "band_count": "Mapped bands",
        "follower_output_quotient": "Follower output quotient",
        "largest_band_by_followers": "Photo / largest band",
        "largest_band_follower_share": "Largest-band share",
    }
)
display(
    ranking.style.hide(axis="index").format(
        {
            "Combined followers": "{:,.0f}",
            "Follower output quotient": "{:.2f}×",
            "Largest-band share": "{:.1%}",
        }
    )
)
'''
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 03. Results"))
    cells.append(nbf.v4.new_markdown_cell("### 03.01 Map 1 — combined follower totals"))
    cells.append(
        nbf.v4.new_code_cell(
            '''FOLLOWER_MAP_PATH = ARTIFACT_DIR / "chart_01_top_city_follower_bubbles.png"
plot_city_follower_bubbles(
    map_data,
    geography,
    snapshot_date="18 July 2026",
    output_path=FOLLOWER_MAP_PATH,
)
display(Image(filename=str(FOLLOWER_MAP_PATH)))
display(Markdown(f"Exported to `{FOLLOWER_MAP_PATH.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""London's **{london['followers_total'] / 1_000_000:.0f}m** combined follower total dominates the area encoding. Manchester (**{manchester['followers_total'] / 1_000_000:.1f}m**), Sheffield and Liverpool form the next tier. The top {TOP_CITY_COUNT} together contain **{top_share_mapped:.1%} of all followers that could be allocated to an FUA**.

This is a map of the global follower reach attached to bands from each city, not a map of where those followers live."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "### 03.02 Map 2 — same totals, filled with each city's largest band"
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''PHOTO_MAP_PATH = ARTIFACT_DIR / "chart_02_top_city_follower_photo_bubbles.png"
plot_city_follower_photo_bubbles(
    map_data,
    geography,
    project_root=ROOT,
    snapshot_date="18 July 2026",
    output_path=PHOTO_MAP_PATH,
)
display(Image(filename=str(PHOTO_MAP_PATH)))
display(Markdown(f"Exported to `{PHOTO_MAP_PATH.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""The photo layer is most representative where one band supplies nearly all of the city total: Crawley (**The Cure, {crawley['largest_band_follower_share']:.0%}**) and Exeter (**Muse, {exeter['largest_band_follower_share']:.1%}**). It is much less representative of a broad catalogue such as London, where Coldplay supplies only **{london['largest_band_follower_share']:.1%}** of the combined total.

That difference is why the plain-circle version remains the primary analytical chart."""
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "### 03.03 Map 3 — follower output relative to population weight"
        )
    )
    cells.append(
        nbf.v4.new_code_cell(
            '''OUTPUT_QUOTIENT_MAP_PATH = ARTIFACT_DIR / "chart_03_follower_output_quotient_map.png"
plot_city_follower_output_quotient(
    map_data,
    geography,
    snapshot_date="18 July 2026",
    output_path=OUTPUT_QUOTIENT_MAP_PATH,
)
display(Image(filename=str(OUTPUT_QUOTIENT_MAP_PATH)))
display(Markdown(f"Exported to `{OUTPUT_QUOTIENT_MAP_PATH.relative_to(ROOT)}`."))
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""This is the **punching-above-weight map**. Among the same ten high-following FUAs, Crawley leads at **{crawley['follower_output_quotient']:.2f}×**, followed by Sheffield at **{sheffield['follower_output_quotient']:.2f}×**. London is also well above proportional at **{london['follower_output_quotient']:.2f}×**. Leeds is the clearest below-benchmark case at **{leeds['follower_output_quotient']:.2f}×**.

The quotient changes the question: Map 1 asks “where is follower output largest?”, while Map 3 asks “where is follower output largest relative to population share?”"""
        )
    )
    cells.append(nbf.v4.new_markdown_cell("## 04. Photo credits and licences"))
    cells.append(
        nbf.v4.new_code_cell(
            '''for photo in map_data.itertuples(index=False):
    creator = photo.artist or photo.credit or "See source page"
    license_part = photo.license_short_name or "See source page"
    if photo.license_url:
        license_part = f"[{license_part}]({photo.license_url})"
    display(
        Markdown(
            f"- **{photo.study_city_label} — {photo.band_name}:** "
            f"[{creator}]({photo.commons_page_url}); {license_part}."
        )
    )

display(
    Markdown(
        "**Base geography:** [Natural Earth 1:50m Admin 0]"
        f"({capture_metadata['natural_earth']['source_page_url']}), public domain. "
        "**Coordinates:** Wikidata P625, CC0; per-city source URLs are in the joined map CSV."
    )
)
'''
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            f"""## 05. Limitations

- The Spotify capture is a frozen **18 July 2026** snapshot. Follower counts change.
- Only **{coverage['mapped_bands']} of 1,000 selected bands** have an included FUA assignment. They cover **{coverage['mapped_follower_share']:.1%}** of selected followers, but origin-missing bands remain unallocated.
- Summed followers are not unique audience. A person can follow multiple bands, and the data do not reveal follower residence.
- City-centre points represent FUAs. They do not show FUA boundaries, intra-FUA origins or movement between cities.
- Historical bands are compared with current place coordinates and 2021 FUA definitions.
- A single photo can overstate one band's representativeness, particularly in cities with broad catalogues.
- The quotient map compares only the same top ten cities selected by raw follower total; it is not a ranking of every UK FUA by quotient.

## 06. Conclusion

Use **Map 1** to compare city-level follower output. Use **Map 2** when the leading-band identity helps the story, but always retain the subtitle and attribution table so the portrait is not mistaken for the whole scene. Use **Map 3** for the population-relative “punching above weight” comparison."""
        )
    )
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata.update(
        {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        }
    )
    return notebook


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    paths = _paths()
    notebook_path = paths["notebook"]
    if notebook_path.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite {notebook_path}; pass --force"
        )
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(build_notebook(paths), notebook_path)
    print(_relative(notebook_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
