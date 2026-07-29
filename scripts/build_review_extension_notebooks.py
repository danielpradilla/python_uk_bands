#!/usr/bin/env python3
"""Build study-review follow-up experiments 19–23."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import nbformat as nbf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.review_extension_experiments import (  # noqa: E402
    build_band_networks,
    build_beyond_spotify,
    build_genre_history,
    build_longitudinal_reach,
    build_scene_infrastructure,
)


NOTEBOOK_DIR = PROJECT_ROOT / "notebooks/experiments"
CAPTURE_DATE = "20260725"
WIKIDATA_PATH = (
    PROJECT_ROOT / f"data/raw/wikidata/review_extension_entities_{CAPTURE_DATE}.json"
)
MUSICBRAINZ_PATH = (
    PROJECT_ROOT / f"data/raw/musicbrainz/review_extension_artists_{CAPTURE_DATE}.json"
)
OSM_PATH = (
    PROJECT_ROOT / f"data/raw/openstreetmap/music_infrastructure_{CAPTURE_DATE}.json"
)
PAGEVIEWS_PATH = (
    PROJECT_ROOT
    / "data/raw/wikimedia/"
    "top1000_enwiki_pageviews_20250701_20260630_20260725.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--only",
        choices=("19", "20", "21", "22", "23"),
        action="append",
        help="Build only the named experiment; may be repeated.",
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


def _metadata(experiment_id: str, title: str) -> dict[str, object]:
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
            "generated_by": "scripts/build_review_extension_notebooks.py",
            "external_capture_date": CAPTURE_DATE,
        },
    }


def _genre_notebook() -> nbf.NotebookNode:
    _, _, decade, coverage = build_genre_history(
        PROJECT_ROOT, wikidata_path=WIKIDATA_PATH
    )
    totals = decade.groupby("genre_family")["weighted_bands"].sum().sort_values(
        ascending=False
    )
    dominant = totals.index[0]
    title = "Genre-specific city histories"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

Wikidata supplies at least one genre for **{coverage['bands_with_genre']}/{coverage['selected_bands']}
bands ({coverage['genre_coverage']:.0%})** and an inception year for
**{coverage['bands_with_inception_year']}/{coverage['selected_bands']}
({coverage['inception_year_coverage']:.0%})**. After FUA mapping, **{coverage['mapped_bands_with_genre_and_year']} bands**
have both fields. **{dominant}** is the largest broad family in the observed
formation-decade data. The results support an exploratory genre history, but
the taxonomy is a transparent reduction of community-authored Wikidata labels,
not a definitive classification."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The study review proposes genre-specific histories rather than treating all
bands as one production system. This experiment uses the popularity-first top
1,000, accepted FUA mappings, Wikidata `genre` (`P136`) claims and Wikidata
`inception` (`P571`) dates.

Genre labels are mapped into six broad families. A band with labels in several
families contributes fractional credit summing to one, preventing multi-tagged
bands from inflating totals.

### Key Assumptions

Wikidata labels are community-maintained and uneven in specificity. Formation
year marks a cohort, not the date a city developed a scene. Current Spotify
followers are retained only as context and are not interpreted as historical
audience.

Source documentation: [Wikidata API](https://www.mediawiki.org/wiki/Wikibase/API)."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nRebuild the audit from the frozen Wikidata entity capture."
        ),
        nbf.v4.new_code_cell(
            _setup_cell("artifacts/experiments/genre_city_histories/20260725")
        ),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_extension_experiments import (
    build_genre_history,
    plot_city_genre_mix,
    plot_genre_by_decade,
)

WIKIDATA_PATH = ROOT / "data/raw/wikidata/review_extension_entities_20260725.json"
band_audit, city_genre, decade_genre, coverage = build_genre_history(
    ROOT, wikidata_path=WIKIDATA_PATH
)

assert len(band_audit) == 1000
assert band_audit["popularity_rank"].is_unique
assert 0 <= coverage["genre_coverage"] <= 1
assert 0 <= coverage["inception_year_coverage"] <= 1
assert city_genre.groupby("study_city_label")["genre_share"].sum().round(10).eq(1).all()

band_audit.to_csv(ARTIFACT_DIR / "band_genre_year_audit.csv", index=False)
city_genre.to_csv(ARTIFACT_DIR / "city_genre_summary.csv", index=False)
decade_genre.to_csv(ARTIFACT_DIR / "decade_genre_summary.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(coverage, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{coverage['bands_with_genre']}/{coverage['selected_bands']} genres · "
    f"{coverage['bands_with_inception_year']}/{coverage['selected_bands']} inception years · "
    f"{coverage['mapped_bands_with_genre_and_year']} mapped bands with both**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. Which broad genre families appear in each formation decade?"
        ),
        nbf.v4.new_code_cell(
            '''display(decade_genre.sort_values(
    ["formation_decade", "weighted_bands"], ascending=[True, False]
).style.hide(axis="index").format({
    "weighted_bands": "{:.2f}",
    "weighted_followers": "{:,.0f}",
}))

decade_path = plot_genre_by_decade(
    decade_genre,
    output_path=ARTIFACT_DIR / "chart_01_genre_by_decade.png",
)
display(Image(filename=str(decade_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. How different are the genre mixes of the best-covered FUAs?"
        ),
        nbf.v4.new_code_cell(
            '''mix_path = plot_city_genre_mix(
    city_genre,
    output_path=ARTIFACT_DIR / "chart_02_city_genre_mix.png",
)
display(Image(filename=str(mix_path)))

display(city_genre.sort_values(
    ["study_city_label", "genre_share"], ascending=[True, False]
).style.hide(axis="index").format({
    "weighted_bands": "{:.2f}",
    "weighted_followers": "{:,.0f}",
    "genre_share": "{:.1%}",
}))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Genre and formation-year coverage are high enough for a transparent
  exploratory description of the popularity-first top 1,000.
- Broad family assignments make city differences readable but discard
  important distinctions such as post-punk versus punk or trip hop versus
  electronic music.
- Multi-genre bands receive fractional credit; totals therefore describe band
  equivalents rather than raw tag counts.
- A publication-quality genre history still needs reviewed genre decisions and
  population denominators appropriate to each formation decade."""
        ),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata=_metadata("19", title))


def _infrastructure_notebook() -> nbf.NotebookNode:
    _, summary, coverage = build_scene_infrastructure(
        PROJECT_ROOT, osm_path=OSM_PATH
    )
    london = summary.set_index("study_city_label").loc["London"]
    title = "Scene infrastructure near the twenty largest FUAs"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

The OpenStreetMap capture identifies **{coverage['classified_elements']:,}
classified infrastructure elements** around the twenty study-city centres.
London has **{int(london['music_place_count'])} distinct mapped music places**
within 15 km. Across the nineteen FUAs with a top-1,000 scene-depth result, the
rank correlation between the raw mapped-place count and effective-band count
is **{coverage['rank_correlation_count_vs_depth']:.2f}**. The correlation
between infrastructure per capita and the follower output quotient is only
**{coverage['rank_correlation_density_vs_output']:.2f}**. These are current
documentation patterns, not evidence that infrastructure caused band output."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The infrastructure branch counts OpenStreetMap nodes and ways tagged as music
venues, nightclubs, arts centres, music shops or audio studios within 15 km of
each study-city centre. Universities are counted separately as context. The
result is joined to the effective-band count and follower output quotient from
experiment 17.

### Key Assumptions

The 15 km circles are reproducible comparison windows, not OECD FUA boundaries.
OpenStreetMap is a live, volunteer-maintained inventory: missing tags mean
"not observed here," not "does not exist." Current places cannot explain bands
formed decades earlier without historical infrastructure data.

Source documentation: [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL)
and [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nParse the checkpointed OpenStreetMap/Overpass capture."
        ),
        nbf.v4.new_code_cell(
            _setup_cell("artifacts/experiments/scene_infrastructure/20260725")
        ),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_extension_experiments import (
    build_scene_infrastructure,
    plot_infrastructure_counts,
    plot_infrastructure_vs_depth,
)

OSM_PATH = ROOT / "data/raw/openstreetmap/music_infrastructure_20260725.json"
place_audit, city_infrastructure, coverage = build_scene_infrastructure(
    ROOT, osm_path=OSM_PATH
)

assert len(city_infrastructure) == 20
assert not place_audit.duplicated(
    ["study_city_label", "element_key", "category"]
).any()
assert city_infrastructure["music_place_count"].ge(0).all()
assert city_infrastructure["music_places_per_million"].ge(0).all()

place_audit.to_csv(ARTIFACT_DIR / "osm_place_audit.csv", index=False)
city_infrastructure.to_csv(ARTIFACT_DIR / "city_infrastructure_summary.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(coverage, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{coverage['classified_elements']:,} classified elements · "
    f"{coverage['named_row_share']:.1%} named rows · "
    f"{coverage['cities_with_scene_depth']}/20 cities with scene-depth results**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. What infrastructure is currently mapped near each city centre?"
        ),
        nbf.v4.new_code_cell(
            '''display(city_infrastructure[[
    "study_city_label", "music_place_count", "music_places_per_million",
    "Music venue", "Nightclub", "Arts centre", "Music shop", "Audio studio",
    "University",
]].style.hide(axis="index").format({"music_places_per_million": "{:.1f}"}))

count_path = plot_infrastructure_counts(
    city_infrastructure,
    output_path=ARTIFACT_DIR / "chart_01_infrastructure_counts.png",
)
display(Image(filename=str(count_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Does mapped infrastructure align with selected-scene breadth?"
        ),
        nbf.v4.new_code_cell(
            '''relationship_path = plot_infrastructure_vs_depth(
    city_infrastructure,
    output_path=ARTIFACT_DIR / "chart_02_infrastructure_vs_depth.png",
)
display(Image(filename=str(relationship_path)))

display(pd.DataFrame({
    "comparison": [
        "raw music-place count vs effective-band count",
        "music places per million vs follower output quotient",
    ],
    "Spearman rank correlation": [
        coverage["rank_correlation_count_vs_depth"],
        coverage["rank_correlation_density_vs_output"],
    ],
}).style.hide(axis="index").format({"Spearman rank correlation": "{:.2f}"}))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Larger and broader music cities tend to have more currently mapped places,
  but city size and mapping intensity are obvious alternative explanations.
- Per-capita infrastructure does not track the follower output quotient in
  this twenty-city comparison.
- Dedicated `music_venue` tagging is sparse; nightclubs, arts centres and
  shops account for much of the observed inventory.
- Historical directories, venue opening dates, labels, rehearsal rooms, rents
  and funding would be needed for an explanatory infrastructure study."""
        ),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata=_metadata("20", title))


def _network_notebook() -> nbf.NotebookNode:
    _, _, _, city, _, coverage = build_band_networks(
        PROJECT_ROOT,
        wikidata_path=WIKIDATA_PATH,
        musicbrainz_path=MUSICBRAINZ_PATH,
    )
    london = city.set_index("study_city_label").loc["London"]
    title = "Band networks: shared members and record labels"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

The mapped portion of the popularity-first top-1,000 catalogue yields **{coverage['member_edges']}
shared-member band pairs** and **{coverage['label_edges']} shared-label pairs**.
Only **{coverage['member_connected_bands']}/{coverage['mapped_bands']} mapped bands** connect through a
documented shared member, compared with **{coverage['label_connected_bands']}/{coverage['mapped_bands']}**
through a shared label. In London, **{london['member_connected_band_share']:.0%}**
of selected bands have a shared-member link and **{london['connected_band_share']:.0%}**
have either type. Label networks are much denser and should not be mistaken for
local collaboration networks."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The network branch combines MusicBrainz `member of band` relationships with
Wikidata `record label` (`P264`) claims for the defensibly mapped bands in the
popularity-first top 1,000. Two selected bands are linked when they
share at least one documented member or label. The experiment reports the two
link types separately and records source coverage for every city.

### Key Assumptions

An absent relationship means undocumented in the frozen sources, not no
relationship. Shared labels can reflect distribution history rather than a
city scene. Producers, venues, educational institutions and informal
collaborations remain outside this first network.

Source documentation: [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)
and [MusicBrainz relationships](https://musicbrainz.org/doc/Relationships)."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nConstruct affiliations, band-pair edges and city summaries."
        ),
        nbf.v4.new_code_cell(
            _setup_cell("artifacts/experiments/band_networks/20260725")
        ),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_extension_experiments import (
    build_band_networks,
    plot_network_city_matrix,
    plot_network_connected_share,
)

WIKIDATA_PATH = ROOT / "data/raw/wikidata/review_extension_entities_20260725.json"
MUSICBRAINZ_PATH = ROOT / "data/raw/musicbrainz/review_extension_artists_20260725.json"
nodes, affiliations, edges, city_network, city_matrix, coverage = build_band_networks(
    ROOT,
    wikidata_path=WIKIDATA_PATH,
    musicbrainz_path=MUSICBRAINZ_PATH,
)

assert coverage["selected_bands"] == 1000
assert len(nodes) == coverage["mapped_bands"]
assert nodes["band_name"].is_unique
assert not affiliations.duplicated(
    ["band_name", "affiliation_type", "entity_id"]
).any()
assert not edges.duplicated(["band_a", "band_b"]).any()
assert city_network["connected_band_share"].between(0, 1).all()

nodes.to_csv(ARTIFACT_DIR / "band_network_nodes.csv", index=False)
affiliations.to_csv(ARTIFACT_DIR / "band_affiliations.csv", index=False)
edges.to_csv(ARTIFACT_DIR / "band_network_edges.csv", index=False)
city_network.to_csv(ARTIFACT_DIR / "city_network_summary.csv", index=False)
city_matrix.to_csv(ARTIFACT_DIR / "city_connection_matrix.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(coverage, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{coverage['musicbrainz_covered_bands']}/{coverage['mapped_bands']} mapped-band member-source coverage · "
    f"{coverage['wikidata_label_covered_bands']}/{coverage['mapped_bands']} mapped-band label-source coverage · "
    f"{coverage['member_edges']} member edges · {coverage['label_edges']} label edges**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. Which selected bands share the strongest documented links?"
        ),
        nbf.v4.new_code_cell(
            '''display(edges.sort_values(
    ["shared_member_count", "connection_count", "band_a", "band_b"],
    ascending=[False, False, True, True],
).head(30).style.hide(axis="index"))

display(city_network.nlargest(30, "selected_bands").style.hide(axis="index").format({
    "connected_band_share": "{:.0%}",
    "member_connected_band_share": "{:.0%}",
    "label_connected_band_share": "{:.0%}",
    "member_source_coverage": "{:.0%}",
    "label_source_coverage": "{:.0%}",
    "mean_degree": "{:.1f}",
    "mean_internal_degree": "{:.1f}",
}))'''
        ),
        nbf.v4.new_code_cell(
            '''share_path = plot_network_connected_share(
    city_network,
    output_path=ARTIFACT_DIR / "chart_01_connected_band_share.png",
)
display(Image(filename=str(share_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Where do observed links stay within a city or cross city boundaries?"
        ),
        nbf.v4.new_code_cell(
            '''matrix_path = plot_network_city_matrix(
    city_matrix,
    output_path=ARTIFACT_DIR / "chart_02_city_connection_matrix.png",
)
display(Image(filename=str(matrix_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Shared-member connections are relatively rare and substantively stronger
  evidence of lineage than shared-label connections.
- Joy Division/New Order, Fun Boy Three/The Specials, Sisters of Mercy/The
  Mission and Heaven 17/The Human League are prominent within-city examples.
- Record-label links dominate the graph and often cross city boundaries,
  describing industry structure more than local scene interaction.
- Coverage differences are large enough that zero-link cities cannot be
  interpreted as having no networks."""
        ),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata=_metadata("21", title))


def _longitudinal_notebook() -> nbf.NotebookNode:
    _, city, summary = build_longitudinal_reach(PROJECT_ROOT)
    top = city.iloc[0]
    bottom = city.iloc[-1]
    title = "Longitudinal platform reach: two fixed snapshots"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

For the same 50 Spotify IDs, every band gains followers between
**{summary['baseline_date']}** and **{summary['current_date']}**, but only
**{summary['bands_with_listener_growth']}/50** gain monthly listeners. Median
change is **{summary['median_follower_change_pct']:.1f}%** for followers and
**{summary['median_listener_change_pct']:.1f}%** for monthly listeners; their
band-level change ranks correlate only **{summary['rank_correlation_listener_vs_follower_change']:.2f}**.
At city-catalogue level, {top['city']} has the largest listener increase
(**{top['listener_change_pct']:.1f}%**) and {bottom['city']} the largest decline
(**{bottom['listener_change_pct']:.1f}%**). Two points measure change, not a
trajectory or its cause."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The longitudinal branch holds the original 50-band catalogue, city assignments
and Spotify IDs fixed, then compares the September 2025 and July 2026 captures.
It reports absolute and percentage changes for followers and rolling monthly
listeners.

### Key Assumptions

The two collection methods aim at the same Spotify concepts but changed from
SpotScraper to public-page extraction. Monthly listeners are rolling and can
respond to releases, tours or viral attention. With only two dates, no event
effect or stable trend is estimated."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nValidate the fixed Spotify-ID panel and compute changes."
        ),
        nbf.v4.new_code_cell(
            _setup_cell(
                "artifacts/experiments/longitudinal_reach/20250920_20260717"
            )
        ),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_extension_experiments import (
    build_longitudinal_reach,
    plot_longitudinal_band_change,
    plot_longitudinal_city_change,
)

band_changes, city_changes, summary = build_longitudinal_reach(ROOT)

assert len(band_changes) == 50
assert band_changes["spotify_id"].is_unique
assert band_changes["city"].nunique() == 10
assert city_changes["bands"].eq(5).all()
assert (band_changes["followers_current"] >= band_changes["followers_baseline"]).all()

band_changes.to_csv(ARTIFACT_DIR / "band_snapshot_changes.csv", index=False)
city_changes.to_csv(ARTIFACT_DIR / "city_snapshot_changes.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{summary['bands']} fixed bands · {summary['cities']} cities · "
    f"{summary['bands_with_listener_growth']} listener gains · "
    f"{summary['bands_with_follower_growth']} follower gains**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. How did each fixed five-band city catalogue move?"
        ),
        nbf.v4.new_code_cell(
            '''display(city_changes.style.hide(axis="index").format({
    "listeners_baseline": "{:,.0f}",
    "listeners_current": "{:,.0f}",
    "followers_baseline": "{:,.0f}",
    "followers_current": "{:,.0f}",
    "listener_change_pct": "{:+.1f}%",
    "follower_change_pct": "{:+.1f}%",
}))

city_path = plot_longitudinal_city_change(
    city_changes,
    output_path=ARTIFACT_DIR / "chart_01_city_change.png",
)
display(Image(filename=str(city_path)))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Do follower gains and monthly-listener changes move together?"
        ),
        nbf.v4.new_code_cell(
            '''band_path = plot_longitudinal_band_change(
    band_changes,
    output_path=ARTIFACT_DIR / "chart_02_band_change.png",
)
display(Image(filename=str(band_path)))

display(band_changes.sort_values(
    "monthly_listeners_change_pct", ascending=False
).style.hide(axis="index").format({
    "monthly_listeners_change_pct": "{:+.1f}%",
    "followers_change_pct": "{:+.1f}%",
}))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Followers rise monotonically in this panel, while rolling monthly listeners
  rise for only 28 of 50 bands.
- Follower growth and listener change are weakly aligned, so they should remain
  separate robustness measures.
- City aggregates can move materially even when the artist panel is fixed.
- A genuine longitudinal design needs fixed monthly captures plus release,
  tour, reissue, viral-event and membership-event annotations."""
        ),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata=_metadata("22", title))


def _beyond_spotify_notebook() -> nbf.NotebookNode:
    audit, _, summary = build_beyond_spotify(
        PROJECT_ROOT, pageviews_path=PAGEVIEWS_PATH
    )
    top = audit.nlargest(1, "attention_residual_log10").iloc[0]
    title = "Beyond Spotify: English Wikipedia attention"
    cells = [
        nbf.v4.new_markdown_cell(
            f"""# {title}

## tl;dr

English Wikipedia pageviews are available for
**{summary['bands_with_pageviews']}/{summary['selected_bands']} bands
({summary['pageview_coverage']:.1%})** over July 2025–June 2026. Their rank
correlation with Spotify followers is **{summary['rank_correlation_followers_vs_pageviews']:.2f}**:
the measures overlap, but are not interchangeable. {top['spotify_name']} has
the largest positive residual from the descriptive log–log fit. Wikipedia
pageviews measure attention and information seeking, not listening or local
audience, so this is triangulation rather than validation of one "true" impact
metric."""
        ),
        nbf.v4.new_markdown_cell(
            """## Context & Methods

The beyond-Spotify branch joins the popularity-first top 1,000 to their Wikidata
English-Wikipedia sitelinks and twelve monthly Wikimedia pageview aggregates.
It compares annual user pageviews with Spotify followers using ranks and a
descriptive log–log fit. Positive residuals identify bands receiving more
Wikipedia attention than their follower count predicts within this sample.

### Key Assumptions

English Wikipedia omits attention in other languages and can respond strongly
to news, deaths, anniversaries or controversy. Pageviews include repeat visits
but exclude automated agents. The Spotify follower count is a point-in-time
stock, whereas pageviews cover a year.

Source documentation: [Wikimedia page-view API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)."""
        ),
        nbf.v4.new_markdown_cell(
            "## Data\n\nAggregate the frozen monthly pageview responses and join by Wikidata ID."
        ),
        nbf.v4.new_code_cell(
            _setup_cell("artifacts/experiments/beyond_spotify/20250701_20260630")
        ),
        nbf.v4.new_code_cell(
            '''from python_uk_bands.review_extension_experiments import (
    build_beyond_spotify,
    plot_attention_residuals,
    plot_spotify_vs_pageviews,
)

PAGEVIEWS_PATH = ROOT / (
    "data/raw/wikimedia/"
    "top1000_enwiki_pageviews_20250701_20260630_20260725.json"
)
band_audit, city_summary, summary = build_beyond_spotify(
    ROOT, pageviews_path=PAGEVIEWS_PATH
)

assert len(band_audit) == 1000
assert band_audit["popularity_rank"].is_unique
assert band_audit["pageviews_total"].ge(0).all()
assert summary["comparable_bands"] <= summary["bands_with_pageviews"]
assert city_summary[["follower_share", "pageview_share"]].sum().round(10).eq(1).all()

band_audit.to_csv(ARTIFACT_DIR / "band_pageview_audit.csv", index=False)
city_summary.to_csv(ARTIFACT_DIR / "city_pageview_summary.csv", index=False)
(ARTIFACT_DIR / "coverage_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\\n"
)

display(Markdown(
    f"**{summary['bands_with_pageviews']}/{summary['selected_bands']} pageview coverage · "
    f"{summary['comparable_bands']} comparable positive observations · "
    f"rank correlation {summary['rank_correlation_followers_vs_pageviews']:.2f}**"
))'''
        ),
        nbf.v4.new_markdown_cell(
            "## Results\n\n### 1. How closely do follower stocks and Wikipedia attention align?"
        ),
        nbf.v4.new_code_cell(
            '''scatter_path = plot_spotify_vs_pageviews(
    band_audit,
    output_path=ARTIFACT_DIR / "chart_01_followers_vs_pageviews.png",
)
display(Image(filename=str(scatter_path)))

display(pd.DataFrame({
    "Measure": ["Coverage", "Rank correlation", "Log–log slope"],
    "Value": [
        f"{summary['bands_with_pageviews']}/{summary['selected_bands']}",
        f"{summary['rank_correlation_followers_vs_pageviews']:.2f}",
        f"{summary['log_model_slope']:.2f}",
    ],
}).style.hide(axis="index"))'''
        ),
        nbf.v4.new_markdown_cell(
            "### 2. Which bands receive unusually high Wikipedia attention?"
        ),
        nbf.v4.new_code_cell(
            '''residual_path = plot_attention_residuals(
    band_audit,
    output_path=ARTIFACT_DIR / "chart_02_attention_residuals.png",
)
display(Image(filename=str(residual_path)))

display(band_audit.dropna(subset=["attention_residual_log10"]).sort_values(
    "attention_residual_log10", ascending=False
).head(25)[[
    "spotify_name", "followers", "enwiki_title", "pageviews_total",
    "follower_rank", "pageview_rank", "attention_residual_log10",
]].style.hide(axis="index").format({
    "followers": "{:,.0f}",
    "pageviews_total": "{:,.0f}",
    "attention_residual_log10": "{:+.2f}",
}))'''
        ),
        nbf.v4.new_markdown_cell(
            """## Takeaways

- Spotify followers and English Wikipedia attention are strongly but
  imperfectly aligned.
- Residuals reveal bands whose cultural or news attention is not summarized by
  follower scale alone.
- Wikipedia is a useful independent attention measure, not a listening metric.
- Further triangulation should add chart history, certifications, radio,
  touring, YouTube, Last.fm and set-list activity under separate definitions."""
        ),
    ]
    return nbf.v4.new_notebook(cells=cells, metadata=_metadata("23", title))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    builders = {
        "19": (
            NOTEBOOK_DIR / "19_uk_bands_genre_city_histories.ipynb",
            _genre_notebook,
        ),
        "20": (
            NOTEBOOK_DIR / "20_uk_bands_scene_infrastructure.ipynb",
            _infrastructure_notebook,
        ),
        "21": (
            NOTEBOOK_DIR / "21_uk_bands_band_networks.ipynb",
            _network_notebook,
        ),
        "22": (
            NOTEBOOK_DIR / "22_uk_bands_longitudinal_reach.ipynb",
            _longitudinal_notebook,
        ),
        "23": (
            NOTEBOOK_DIR / "23_uk_bands_beyond_spotify.ipynb",
            _beyond_spotify_notebook,
        ),
    }
    selected = set(args.only or builders)
    notebooks = {path: builder() for key, (path, builder) in builders.items() if key in selected}
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
