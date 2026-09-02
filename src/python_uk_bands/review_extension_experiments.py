"""Calculations and charts for study-review follow-up experiments 19–23."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from itertools import combinations
import json
from pathlib import Path
import re
import unicodedata

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from .config import FUA_POPULATION_PATH
from .review_experiments import build_top1000_scene_depth
from .visuals import HOUSE, apply_chart_style


GENRE_COLORS = {
    "Rock and indie": "#2f5f7f",
    "Pop, soul and R&B": "#c28a00",
    "Punk and new wave": "#b8653b",
    "Electronic and dance": "#66754b",
    "Metal": "#b05a7a",
    "Other genres": "#abb8c3",
}


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    *,
    label: str,
) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing columns: {sorted(missing)}")


def _qid_values(entity: dict, property_id: str) -> list[str]:
    values: list[str] = []
    for claim in entity.get("claims", {}).get(property_id, []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and value.get("entity-type") == "item":
            qid = value.get("id")
            if qid:
                values.append(str(qid))
    return sorted(set(values))


def _inception_year(entity: dict) -> int | None:
    years: list[int] = []
    for claim in entity.get("claims", {}).get("P571", []):
        if claim.get("rank") == "deprecated":
            continue
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if not isinstance(value, dict):
            continue
        match = re.match(r"^\+?(\d{4})-", str(value.get("time", "")))
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2026:
                years.append(year)
    return min(years) if years else None


def _normalized_artist_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold().replace("&", "and")
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    normalized = re.sub(r"^the\s+", "", normalized)
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _genre_family(label: str) -> str:
    value = label.casefold()
    if any(term in value for term in ("metal", "grindcore", "deathcore")):
        return "Metal"
    if any(
        term in value
        for term in (
            "punk",
            "new wave",
            "goth",
            "hardcore",
            "oi!",
            "anarcho",
        )
    ):
        return "Punk and new wave"
    if any(
        term in value
        for term in (
            "electronic",
            "electronica",
            "synth",
            "techno",
            "house music",
            "trip hop",
            "drum and bass",
            "dance music",
            "ambient",
            "industrial music",
        )
    ):
        return "Electronic and dance"
    if any(term in value for term in ("reggae", "ska", "dub music")):
        return "Other genres"
    if any(term in value for term in ("folk", "country music", "skiffle")):
        return "Other genres"
    if any(
        term in value
        for term in ("pop", "soul", "rhythm and blues", "r&b", "funk")
    ):
        return "Pop, soul and R&B"
    if any(
        term in value
        for term in (
            "rock",
            "indie",
            "britpop",
            "shoegaze",
            "psychedelic",
            "beat music",
        )
    ):
        return "Rock and indie"
    return "Other genres"


def extract_wikidata_band_features(payload: dict) -> pd.DataFrame:
    """Extract inception, genres, labels, members and enwiki titles."""

    entities = payload.get("entities", {})
    labels = payload.get("referenced_labels", {})
    rows: list[dict] = []
    for qid, entity in entities.items():
        genre_qids = _qid_values(entity, "P136")
        label_qids = _qid_values(entity, "P264")
        member_qids = _qid_values(entity, "P527")
        genre_labels = sorted({labels.get(value, "") for value in genre_qids} - {""})
        genre_families = sorted({_genre_family(value) for value in genre_labels})
        rows.append(
            {
                "wikidata_qid": qid,
                "wikidata_name": entity.get("labels", {})
                .get("en", {})
                .get("value", ""),
                "inception_year": _inception_year(entity),
                "genre_qids": "|".join(genre_qids),
                "genre_labels": "|".join(genre_labels),
                "genre_families": "|".join(genre_families),
                "record_label_qids": "|".join(label_qids),
                "record_label_names": "|".join(
                    sorted({labels.get(value, "") for value in label_qids} - {""})
                ),
                "member_qids": "|".join(member_qids),
                "member_names": "|".join(
                    sorted({labels.get(value, "") for value in member_qids} - {""})
                ),
                "enwiki_title": entity.get("sitelinks", {})
                .get("enwiki", {})
                .get("title", ""),
            }
        )
    return pd.DataFrame(rows).sort_values("wikidata_qid").reset_index(drop=True)


def build_genre_history(
    project_root: Path,
    *,
    wikidata_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    """Build a coverage-aware genre and formation-decade experiment."""

    bands = pd.read_csv(
        project_root
        / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv",
        keep_default_na=False,
    )
    mapping = pd.read_csv(
        project_root
        / "data/interim/popularity_first_top1000_20260718T204522Z_fua_mapping_audit.csv",
        keep_default_na=False,
    )
    features = extract_wikidata_band_features(json.loads(wikidata_path.read_text()))
    audit = bands[
        [
            "popularity_rank",
            "returned_spotify_id",
            "spotify_name",
            "wikidata_qid",
            "monthly_listeners",
            "followers",
        ]
    ].merge(features, on="wikidata_qid", how="left", validate="one_to_one")
    audit = audit.merge(
        mapping[
            [
                "returned_spotify_id",
                "mapping_tier",
                "fua_code",
                "study_city_label",
                "population",
            ]
        ],
        on="returned_spotify_id",
        how="left",
        validate="one_to_one",
    )
    audit["mapped_fua"] = audit["mapping_tier"].isin(
        {"strict", "reviewed_extended"}
    )
    audit["has_genre"] = audit["genre_families"].fillna("").ne("")
    audit["has_inception_year"] = audit["inception_year"].notna()
    audit["formation_decade"] = (
        pd.to_numeric(audit["inception_year"], errors="coerce") // 10 * 10
    ).astype("Int64")

    classified = audit.loc[audit["has_genre"] & audit["mapped_fua"]].copy()
    classified["genre_family"] = classified["genre_families"].str.split("|")
    classified = classified.explode("genre_family")
    family_counts = classified.groupby("returned_spotify_id")[
        "genre_family"
    ].transform("nunique")
    classified["band_weight"] = 1 / family_counts
    classified["follower_weight"] = classified["followers"] * classified["band_weight"]

    city_genre = (
        classified.groupby(["study_city_label", "genre_family"], as_index=False)
        .agg(
            weighted_bands=("band_weight", "sum"),
            distinct_bands=("returned_spotify_id", "nunique"),
            weighted_followers=("follower_weight", "sum"),
        )
    )
    city_totals = city_genre.groupby("study_city_label")["weighted_bands"].transform(
        "sum"
    )
    city_genre["genre_share"] = city_genre["weighted_bands"] / city_totals

    by_decade = classified.dropna(subset=["formation_decade"]).copy()
    decade_genre = (
        by_decade.groupby(["formation_decade", "genre_family"], as_index=False)
        .agg(
            weighted_bands=("band_weight", "sum"),
            distinct_bands=("returned_spotify_id", "nunique"),
            weighted_followers=("follower_weight", "sum"),
        )
    )
    coverage = {
        "selected_bands": int(len(audit)),
        "mapped_bands": int(audit["mapped_fua"].sum()),
        "bands_with_genre": int(audit["has_genre"].sum()),
        "genre_coverage": float(audit["has_genre"].mean()),
        "bands_with_inception_year": int(audit["has_inception_year"].sum()),
        "inception_year_coverage": float(audit["has_inception_year"].mean()),
        "mapped_bands_with_genre_and_year": int(
            (audit["mapped_fua"] & audit["has_genre"] & audit["has_inception_year"]).sum()
        ),
    }
    return audit, city_genre, decade_genre, coverage


def _infrastructure_categories(tags: dict) -> list[str]:
    categories: list[str] = []
    if tags.get("amenity") == "music_venue":
        categories.append("Music venue")
    if tags.get("amenity") == "nightclub":
        categories.append("Nightclub")
    if tags.get("amenity") == "arts_centre":
        categories.append("Arts centre")
    if tags.get("shop") == "music":
        categories.append("Music shop")
    if tags.get("studio") == "audio":
        categories.append("Audio studio")
    if tags.get("amenity") == "university":
        categories.append("University")
    return categories


def build_scene_infrastructure(
    project_root: Path,
    *,
    osm_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    """Summarize OpenStreetMap music infrastructure and join scene depth."""

    payload = json.loads(osm_path.read_text())
    if not payload.get("complete"):
        raise ValueError("OpenStreetMap capture is incomplete")
    rows: list[dict] = []
    for record in payload.get("records", []):
        for element in record.get("elements", []):
            tags = element.get("tags", {})
            for category in _infrastructure_categories(tags):
                rows.append(
                    {
                        "fua_code": record["fua_code"],
                        "study_city_label": record["study_city_label"],
                        "radius_metres": record["radius_metres"],
                        "element_key": f"{element.get('type')}:{element.get('id')}",
                        "category": category,
                        "name": tags.get("name", ""),
                        "osm_tags": json.dumps(tags, sort_keys=True),
                    }
                )
    places = pd.DataFrame(rows)
    if places.empty:
        raise ValueError("OpenStreetMap capture contains no classified places")
    if places.duplicated(["study_city_label", "element_key", "category"]).any():
        raise ValueError("Infrastructure rows must be unique per city, element and category")

    categories = [
        "Music venue",
        "Nightclub",
        "Arts centre",
        "Music shop",
        "Audio studio",
        "University",
    ]
    counts = (
        places.groupby(["study_city_label", "category"])["element_key"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(columns=categories, fill_value=0)
    )
    current_population = pd.read_csv(FUA_POPULATION_PATH)[
        ["fua_code", "population_year", "population"]
    ]
    city_base = pd.DataFrame(payload["records"])[
        ["fua_code", "study_city_label", "radius_metres"]
    ].merge(
        current_population,
        on="fua_code",
        how="left",
        validate="one_to_one",
    )
    if city_base["population"].isna().any():
        missing = city_base.loc[
            city_base["population"].isna(), "fua_code"
        ].tolist()
        raise ValueError(f"Missing current FUA population for: {missing}")
    city_base = city_base.set_index("study_city_label")
    places = places.merge(
        current_population,
        on="fua_code",
        how="left",
        validate="many_to_one",
    )
    summary = city_base.join(counts, how="left").fillna(0).reset_index()
    music_categories = categories[:-1]
    music_counts = (
        places.loc[places["category"].isin(music_categories)]
        .groupby("study_city_label")["element_key"]
        .nunique()
    )
    summary["music_place_count"] = summary["study_city_label"].map(music_counts).fillna(0)
    summary["music_places_per_million"] = (
        summary["music_place_count"] / summary["population"] * 1_000_000
    )
    named = places.assign(named=places["name"].ne(""))
    named_share = named.groupby("study_city_label")["named"].mean()
    summary["named_element_share"] = summary["study_city_label"].map(named_share)

    depth, _, _ = build_top1000_scene_depth(project_root)
    summary = summary.merge(
        depth[
            [
                "study_city_label",
                "band_count",
                "effective_band_count",
                "follower_output_quotient",
            ]
        ],
        on="study_city_label",
        how="left",
        validate="one_to_one",
    )
    observed = summary.dropna(subset=["effective_band_count"])
    coverage = {
        "population_year": int(current_population["population_year"].unique().item()),
        "cities": int(len(summary)),
        "classified_elements": int(places["element_key"].nunique()),
        "named_row_share": float(places["name"].ne("").mean()),
        "cities_with_scene_depth": int(len(observed)),
        "rank_correlation_count_vs_depth": float(
            observed["music_place_count"].rank().corr(
                observed["effective_band_count"].rank()
            )
        ),
        "rank_correlation_density_vs_output": float(
            observed["music_places_per_million"].rank().corr(
                observed["follower_output_quotient"].rank()
            )
        ),
    }
    summary = summary.sort_values(
        ["music_place_count", "study_city_label"], ascending=[False, True]
    ).reset_index(drop=True)
    return places, summary, coverage


def build_band_networks(
    project_root: Path,
    *,
    wikidata_path: Path,
    musicbrainz_path: Path,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, int | float],
]:
    """Build shared-member and shared-label links for mapped top-1,000 bands."""

    bands = pd.read_csv(
        project_root
        / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv",
        keep_default_na=False,
    )
    mapping = pd.read_csv(
        project_root
        / "data/interim/popularity_first_top1000_20260718T204522Z_fua_mapping_audit.csv",
        keep_default_na=False,
    )
    nodes = bands[
        [
            "popularity_rank",
            "spotify_name",
            "returned_spotify_id",
            "wikidata_qid",
            "followers",
            "monthly_listeners",
        ]
    ].rename(
        columns={
            "spotify_name": "band_name",
            "returned_spotify_id": "spotify_id",
        }
    ).merge(
        mapping[
            [
                "returned_spotify_id",
                "mapping_tier",
                "fua_code",
                "study_city_label",
            ]
        ].rename(columns={"returned_spotify_id": "spotify_id"}),
        on="spotify_id",
        how="left",
        validate="one_to_one",
    )
    selected_band_count = len(nodes)
    nodes["mapped_fua"] = nodes["mapping_tier"].isin(
        {"strict", "reviewed_extended"}
    )
    nodes = nodes.loc[nodes["mapped_fua"]].copy().reset_index(drop=True)
    wikidata = json.loads(wikidata_path.read_text())
    entities = wikidata["entities"]
    labels = wikidata.get("referenced_labels", {})
    affiliations: list[dict] = []
    for row in nodes.dropna(subset=["wikidata_qid"]).itertuples():
        entity = entities.get(row.wikidata_qid, {})
        for qid in _qid_values(entity, "P264"):
            affiliations.append(
                {
                    "band_name": row.band_name,
                    "study_city_label": row.study_city_label,
                    "affiliation_type": "record_label",
                    "entity_id": f"wd:{qid}",
                    "entity_name": labels.get(qid, qid),
                    "source": "Wikidata P264",
                }
            )

    musicbrainz = json.loads(musicbrainz_path.read_text())
    node_names = set(nodes["band_name"])
    mb_covered = set()
    rejected_musicbrainz_records = 0
    matched_musicbrainz_records = 0
    for record in musicbrainz.get("records", []):
        if record.get("status", "ok") != "ok":
            continue
        if record["band_name"] not in node_names:
            continue
        if _normalized_artist_name(record["band_name"]) != _normalized_artist_name(
            record.get("musicbrainz_name", "")
        ):
            rejected_musicbrainz_records += 1
            continue
        matched_musicbrainz_records += 1
        mb_covered.add(record["band_name"])
        for relation in record.get("member_relations", []):
            affiliations.append(
                {
                    "band_name": record["band_name"],
                    "study_city_label": record["study_city_label"],
                    "affiliation_type": "member",
                    "entity_id": f"mb:{relation['artist_id']}",
                    "entity_name": relation["artist_name"],
                    "source": "MusicBrainz member relationship",
                }
            )
    affiliation_frame = pd.DataFrame(affiliations).drop_duplicates(
        ["band_name", "affiliation_type", "entity_id"]
    )

    edge_entities: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: {"member": set(), "record_label": set()}
    )
    for (kind, entity_id), group in affiliation_frame.groupby(
        ["affiliation_type", "entity_id"]
    ):
        linked_bands = sorted(group["band_name"].unique())
        if len(linked_bands) < 2:
            continue
        entity_name = group["entity_name"].iloc[0]
        for left, right in combinations(linked_bands, 2):
            edge_entities[(left, right)][kind].add(entity_name)
    edge_rows: list[dict] = []
    node_city = nodes.set_index("band_name")["study_city_label"].to_dict()
    for (left, right), values in edge_entities.items():
        edge_rows.append(
            {
                "band_a": left,
                "city_a": node_city[left],
                "band_b": right,
                "city_b": node_city[right],
                "shared_members": "|".join(sorted(values["member"])),
                "shared_member_count": len(values["member"]),
                "shared_labels": "|".join(sorted(values["record_label"])),
                "shared_label_count": len(values["record_label"]),
                "connection_count": len(values["member"]) + len(values["record_label"]),
                "same_city": node_city[left] == node_city[right],
            }
        )
    edges = pd.DataFrame(edge_rows)
    if edges.empty:
        edges = pd.DataFrame(
            columns=[
                "band_a",
                "city_a",
                "band_b",
                "city_b",
                "shared_members",
                "shared_member_count",
                "shared_labels",
                "shared_label_count",
                "connection_count",
                "same_city",
            ]
        )
    edges = edges.sort_values(
        ["connection_count", "band_a", "band_b"], ascending=[False, True, True]
    ).reset_index(drop=True)

    neighbors: dict[str, set[str]] = defaultdict(set)
    internal_neighbors: dict[str, set[str]] = defaultdict(set)
    member_neighbors: dict[str, set[str]] = defaultdict(set)
    label_neighbors: dict[str, set[str]] = defaultdict(set)
    for row in edges.itertuples():
        neighbors[row.band_a].add(row.band_b)
        neighbors[row.band_b].add(row.band_a)
        if row.shared_member_count:
            member_neighbors[row.band_a].add(row.band_b)
            member_neighbors[row.band_b].add(row.band_a)
        if row.shared_label_count:
            label_neighbors[row.band_a].add(row.band_b)
            label_neighbors[row.band_b].add(row.band_a)
        if row.same_city:
            internal_neighbors[row.band_a].add(row.band_b)
            internal_neighbors[row.band_b].add(row.band_a)
    nodes["musicbrainz_covered"] = nodes["band_name"].isin(mb_covered)
    nodes["wikidata_label_covered"] = nodes["wikidata_qid"].isin(entities)
    nodes["network_degree"] = nodes["band_name"].map(
        lambda value: len(neighbors[value])
    )
    nodes["member_degree"] = nodes["band_name"].map(
        lambda value: len(member_neighbors[value])
    )
    nodes["label_degree"] = nodes["band_name"].map(
        lambda value: len(label_neighbors[value])
    )
    nodes["internal_degree"] = nodes["band_name"].map(
        lambda value: len(internal_neighbors[value])
    )
    nodes["connected"] = nodes["network_degree"].gt(0)
    nodes["member_connected"] = nodes["member_degree"].gt(0)
    nodes["label_connected"] = nodes["label_degree"].gt(0)
    city_summary = (
        nodes.groupby("study_city_label", as_index=False)
        .agg(
            selected_bands=("band_name", "nunique"),
            connected_bands=("connected", "sum"),
            member_connected_bands=("member_connected", "sum"),
            label_connected_bands=("label_connected", "sum"),
            mean_degree=("network_degree", "mean"),
            mean_internal_degree=("internal_degree", "mean"),
            member_source_coverage=("musicbrainz_covered", "mean"),
            label_source_coverage=("wikidata_label_covered", "mean"),
        )
    )
    city_summary["connected_band_share"] = (
        city_summary["connected_bands"] / city_summary["selected_bands"]
    )
    city_summary["member_connected_band_share"] = (
        city_summary["member_connected_bands"] / city_summary["selected_bands"]
    )
    city_summary["label_connected_band_share"] = (
        city_summary["label_connected_bands"] / city_summary["selected_bands"]
    )
    city_summary = city_summary.sort_values(
        ["connected_band_share", "mean_degree", "study_city_label"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    city_names = sorted(nodes["study_city_label"].unique())
    matrix = pd.DataFrame(0, index=city_names, columns=city_names, dtype=int)
    for row in edges.itertuples():
        matrix.loc[row.city_a, row.city_b] += 1
        if row.city_a != row.city_b:
            matrix.loc[row.city_b, row.city_a] += 1
    matrix.index.name = "study_city_label"
    matrix = matrix.reset_index()
    coverage = {
        "selected_bands": int(selected_band_count),
        "mapped_bands": int(len(nodes)),
        "musicbrainz_covered_bands": int(nodes["musicbrainz_covered"].sum()),
        "musicbrainz_name_matched_records": int(matched_musicbrainz_records),
        "musicbrainz_name_rejected_records": int(rejected_musicbrainz_records),
        "wikidata_label_covered_bands": int(nodes["wikidata_label_covered"].sum()),
        "affiliations": int(len(affiliation_frame)),
        "band_edges": int(len(edges)),
        "member_edges": int(edges["shared_member_count"].gt(0).sum()),
        "label_edges": int(edges["shared_label_count"].gt(0).sum()),
        "connected_bands": int(nodes["connected"].sum()),
        "member_connected_bands": int(nodes["member_connected"].sum()),
        "label_connected_bands": int(nodes["label_connected"].sum()),
        "connected_band_share": float(nodes["connected"].mean()),
    }
    return nodes, affiliation_frame, edges, city_summary, matrix, coverage


def build_longitudinal_reach(
    project_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Compare a fixed 50-band catalogue across two Spotify snapshots."""

    baseline_path = project_root / "data/processed/shortlist_spotify_metrics.json"
    current_path = (
        project_root
        / "data/processed/shortlist_spotify_metrics_20260717T225913Z.json"
    )
    baseline = pd.DataFrame(json.loads(baseline_path.read_text()))
    current = pd.DataFrame(json.loads(current_path.read_text()))
    _require_columns(
        baseline,
        {"band", "city", "spotify_id", "monthly_listeners", "followers"},
        label="baseline snapshot",
    )
    _require_columns(
        current,
        {"band", "city", "spotify_id", "monthly_listeners", "followers"},
        label="current snapshot",
    )
    if set(baseline["spotify_id"]) != set(current["spotify_id"]):
        raise ValueError("Longitudinal comparison requires identical Spotify IDs")
    changes = baseline[
        ["band", "city", "spotify_id", "monthly_listeners", "followers"]
    ].merge(
        current[["spotify_id", "monthly_listeners", "followers"]],
        on="spotify_id",
        how="inner",
        suffixes=("_baseline", "_current"),
        validate="one_to_one",
    )
    for metric in ("monthly_listeners", "followers"):
        changes[f"{metric}_change"] = (
            changes[f"{metric}_current"] - changes[f"{metric}_baseline"]
        )
        changes[f"{metric}_change_pct"] = (
            changes[f"{metric}_change"]
            / changes[f"{metric}_baseline"].replace(0, np.nan)
            * 100
        )
    city = (
        changes.groupby("city", as_index=False)
        .agg(
            bands=("band", "nunique"),
            listeners_baseline=("monthly_listeners_baseline", "sum"),
            listeners_current=("monthly_listeners_current", "sum"),
            followers_baseline=("followers_baseline", "sum"),
            followers_current=("followers_current", "sum"),
        )
    )
    city["listener_change_pct"] = (
        city["listeners_current"] / city["listeners_baseline"] - 1
    ) * 100
    city["follower_change_pct"] = (
        city["followers_current"] / city["followers_baseline"] - 1
    ) * 100
    city = city.sort_values(
        ["listener_change_pct", "city"], ascending=[False, True]
    ).reset_index(drop=True)
    summary = {
        "baseline_date": str(baseline["stats_extracted_at"].max()),
        "current_date": str(current["stats_extracted_at"].max()),
        "bands": int(len(changes)),
        "cities": int(changes["city"].nunique()),
        "bands_with_listener_growth": int(changes["monthly_listeners_change"].gt(0).sum()),
        "bands_with_follower_growth": int(changes["followers_change"].gt(0).sum()),
        "median_listener_change_pct": float(changes["monthly_listeners_change_pct"].median()),
        "median_follower_change_pct": float(changes["followers_change_pct"].median()),
        "rank_correlation_listener_vs_follower_change": float(
            changes["monthly_listeners_change_pct"].rank().corr(
                changes["followers_change_pct"].rank()
            )
        ),
    }
    return changes, city, summary


def build_beyond_spotify(
    project_root: Path,
    *,
    pageviews_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int | str]]:
    """Triangulate Spotify reach with a year of English Wikipedia pageviews."""

    bands = pd.read_csv(
        project_root
        / "data/processed/popularity_first_top1000_20260718T204522Z_bands.csv",
        keep_default_na=False,
    )
    mapping = pd.read_csv(
        project_root
        / "data/interim/popularity_first_top1000_20260718T204522Z_fua_mapping_audit.csv",
        keep_default_na=False,
    )
    payload = json.loads(pageviews_path.read_text())
    view_rows = []
    for record in payload.get("records", []):
        items = record.get("items", [])
        view_rows.append(
            {
                "wikidata_qid": record["wikidata_qid"],
                "enwiki_title": record.get("article_title", ""),
                "pageview_status": record.get("status", ""),
                "pageviews_total": sum(int(item.get("views", 0)) for item in items),
                "pageview_months": len(items),
            }
        )
    views = pd.DataFrame(view_rows)
    audit = bands[
        [
            "popularity_rank",
            "returned_spotify_id",
            "spotify_name",
            "wikidata_qid",
            "followers",
            "monthly_listeners",
        ]
    ].merge(views, on="wikidata_qid", how="left", validate="one_to_one")
    audit[["enwiki_title", "pageview_status"]] = audit[
        ["enwiki_title", "pageview_status"]
    ].fillna("")
    audit["pageview_status"] = audit["pageview_status"].replace("", "not_captured")
    audit[["pageviews_total", "pageview_months"]] = audit[
        ["pageviews_total", "pageview_months"]
    ].fillna(0).astype(int)
    audit = audit.merge(
        mapping[
            ["returned_spotify_id", "mapping_tier", "fua_code", "study_city_label"]
        ],
        on="returned_spotify_id",
        how="left",
        validate="one_to_one",
    )
    audit["mapped_fua"] = audit["mapping_tier"].isin(
        {"strict", "reviewed_extended"}
    )
    comparable = audit.loc[
        audit["pageview_status"].eq("ok")
        & audit["pageviews_total"].gt(0)
        & audit["followers"].gt(0)
    ].copy()
    comparable["log10_followers"] = np.log10(comparable["followers"])
    comparable["log10_pageviews"] = np.log10(comparable["pageviews_total"])
    slope, intercept = np.polyfit(
        comparable["log10_followers"], comparable["log10_pageviews"], 1
    )
    comparable["expected_log10_pageviews"] = (
        intercept + slope * comparable["log10_followers"]
    )
    comparable["attention_residual_log10"] = (
        comparable["log10_pageviews"] - comparable["expected_log10_pageviews"]
    )
    comparable["follower_rank"] = comparable["followers"].rank(
        method="min", ascending=False
    )
    comparable["pageview_rank"] = comparable["pageviews_total"].rank(
        method="min", ascending=False
    )
    audit = audit.merge(
        comparable[
            [
                "returned_spotify_id",
                "log10_followers",
                "log10_pageviews",
                "expected_log10_pageviews",
                "attention_residual_log10",
                "follower_rank",
                "pageview_rank",
            ]
        ],
        on="returned_spotify_id",
        how="left",
        validate="one_to_one",
    )

    city = (
        audit.loc[audit["mapped_fua"] & audit["pageview_status"].eq("ok")]
        .groupby("study_city_label", as_index=False)
        .agg(
            observed_bands=("returned_spotify_id", "nunique"),
            followers=("followers", "sum"),
            pageviews=("pageviews_total", "sum"),
        )
    )
    city["follower_share"] = city["followers"] / city["followers"].sum()
    city["pageview_share"] = city["pageviews"] / city["pageviews"].sum()
    city["pageview_minus_follower_share"] = (
        city["pageview_share"] - city["follower_share"]
    )
    city = city.sort_values(
        ["pageviews", "study_city_label"], ascending=[False, True]
    ).reset_index(drop=True)

    summary = {
        "selected_bands": int(len(audit)),
        "bands_with_pageviews": int(audit["pageview_status"].eq("ok").sum()),
        "pageview_coverage": float(audit["pageview_status"].eq("ok").mean()),
        "comparable_bands": int(len(comparable)),
        "rank_correlation_followers_vs_pageviews": float(
            comparable["followers"].rank().corr(comparable["pageviews_total"].rank())
        ),
        "log_model_slope": float(slope),
        "log_model_intercept": float(intercept),
        "pageview_start": str(payload.get("start", "")),
        "pageview_end": str(payload.get("end", "")),
    }
    return audit, city, summary


def _save_figure(fig: plt.Figure, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=HOUSE["page"])
    plt.close(fig)
    return output_path


def _title(ax: plt.Axes, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", pad=34, fontsize=15, fontweight="normal")
    ax.text(
        0,
        1.015,
        subtitle,
        transform=ax.transAxes,
        color=HOUSE["secondary"],
        fontsize=9.5,
    )


def plot_genre_by_decade(decade_genre: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot weighted genre-family counts across formation decades."""

    apply_chart_style()
    pivot = decade_genre.pivot_table(
        index="formation_decade",
        columns="genre_family",
        values="weighted_bands",
        aggfunc="sum",
        fill_value=0,
    ).sort_index()
    columns = [column for column in GENRE_COLORS if column in pivot.columns]
    fig, ax = plt.subplots(figsize=(10.8, 6.6))
    bottom = np.zeros(len(pivot))
    for column in columns:
        ax.bar(
            pivot.index.astype(int).astype(str),
            pivot[column],
            bottom=bottom,
            color=GENRE_COLORS[column],
            edgecolor=HOUSE["ink_soft"],
            linewidth=0.35,
            label=column,
        )
        bottom += pivot[column].to_numpy()
    _title(
        ax,
        "Genre families across observed formation decades",
        "Popularity-first top 1,000 · mapped FUAs · fractional credit for multi-genre bands",
    )
    ax.set_xlabel("Formation decade")
    ax.set_ylabel("Weighted number of classified bands")
    ax.grid(axis="y")
    ax.grid(axis="x", visible=False)
    ax.spines[["top", "right"]].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        frameon=False,
        ncols=3,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return _save_figure(fig, output_path)


def plot_city_genre_mix(city_genre: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot the genre-family mix for the best-covered FUAs."""

    apply_chart_style()
    totals = city_genre.groupby("study_city_label")["weighted_bands"].sum()
    selected = totals.nlargest(12).index
    pivot = city_genre.loc[city_genre["study_city_label"].isin(selected)].pivot_table(
        index="study_city_label",
        columns="genre_family",
        values="genre_share",
        aggfunc="sum",
        fill_value=0,
    )
    pivot = pivot.loc[totals.loc[selected].sort_values().index]
    columns = [column for column in GENRE_COLORS if column in pivot.columns]
    fig, ax = plt.subplots(figsize=(10.8, 7.8))
    left = np.zeros(len(pivot))
    for column in columns:
        ax.barh(
            pivot.index,
            pivot[column],
            left=left,
            color=GENRE_COLORS[column],
            edgecolor=HOUSE["ink_soft"],
            linewidth=0.35,
            label=column,
        )
        left += pivot[column].to_numpy()
    _title(
        ax,
        "Genre mix in the twelve best-covered mapped FUAs",
        "Each classified band contributes one unit split across its genre families",
    )
    ax.set_xlabel("Share of weighted classified bands")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        frameon=False,
        ncols=3,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
    )
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return _save_figure(fig, output_path)


def plot_infrastructure_counts(summary: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot observed OSM music-place counts by city and category."""

    apply_chart_style()
    categories = ["Music venue", "Nightclub", "Arts centre", "Music shop", "Audio studio"]
    colors = ["#2f5f7f", "#c28a00", "#b8653b", "#66754b", "#b05a7a"]
    shown = summary.sort_values("music_place_count", ascending=True)
    fig, ax = plt.subplots(figsize=(10.8, 8.0))
    left = np.zeros(len(shown))
    for category, color in zip(categories, colors, strict=True):
        ax.barh(
            shown["study_city_label"],
            shown[category],
            left=left,
            color=color,
            edgecolor=HOUSE["ink_soft"],
            linewidth=0.35,
            label=category,
        )
        left += shown[category].to_numpy()
    _title(
        ax,
        "OpenStreetMap music infrastructure near study-city centres",
        "Nodes and ways within 15 km · current mapped inventory, not an historical FUA census",
    )
    ax.set_xlabel("Distinct mapped places")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, ncols=3, loc="lower right")
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_infrastructure_vs_depth(summary: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot observed infrastructure against effective band count."""

    apply_chart_style()
    shown = summary.dropna(subset=["effective_band_count"])
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    ax.scatter(
        shown["music_place_count"],
        shown["effective_band_count"],
        s=58,
        facecolor=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.7,
    )
    label_names = set(shown.nlargest(6, "music_place_count")["study_city_label"]) | set(
        shown.nlargest(6, "effective_band_count")["study_city_label"]
    )
    for row in shown.itertuples():
        if row.study_city_label in label_names:
            ax.annotate(
                row.study_city_label,
                (row.music_place_count, row.effective_band_count),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8.2,
                color=HOUSE["ink_soft"],
            )
    _title(
        ax,
        "Mapped infrastructure and effective band count",
        "Twenty largest UK FUAs · association is descriptive, not causal",
    )
    ax.set_xlabel("Distinct OSM music places within 15 km")
    ax.set_ylabel("Effective number of equally followed mapped bands")
    ax.grid()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_network_city_matrix(matrix: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot counts of band-pair links within and across cities."""

    apply_chart_style()
    frame = matrix.set_index("study_city_label")
    totals = frame.sum(axis=1)
    selected = totals.nlargest(min(14, len(totals))).index
    frame = frame.loc[selected, selected]
    fig, ax = plt.subplots(figsize=(10.2, 8.8))
    values = frame.to_numpy()
    image = ax.imshow(
        np.ma.masked_equal(values, 0),
        cmap="Blues",
        norm=LogNorm(vmin=1, vmax=max(1, values.max())),
        aspect="auto",
    )
    ax.set_xticks(range(len(frame.columns)), frame.columns, rotation=55, ha="right")
    ax.set_yticks(range(len(frame.index)), frame.index)
    for i in range(len(frame.index)):
        for j in range(len(frame.columns)):
            value = int(frame.iat[i, j])
            if value:
                ax.text(j, i, str(value), ha="center", va="center", fontsize=7.5)
    _title(
        ax,
        "Shared-member or shared-label links between selected bands",
        "Fourteen cities with the most observed links · exact counts shown; colour uses a log scale",
    )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.03, pad=0.02)
    colorbar.set_label("Connected band pairs")
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_network_connected_share(city: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot the observed connected-band share with source coverage context."""

    apply_chart_style()
    shown = (
        city.nlargest(min(25, len(city)), "selected_bands")
        .sort_values("connected_band_share", ascending=True)
    )
    shown = shown.assign(
        display_label=shown.apply(
            lambda row: f"{row['study_city_label']} (n={int(row['selected_bands'])})",
            axis=1,
        )
    )
    y = np.arange(len(shown))
    fig, ax = plt.subplots(figsize=(10.8, 7.8))
    ax.barh(
        y - 0.19,
        shown["connected_band_share"],
        height=0.36,
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.5,
        label="Any observed link",
    )
    ax.barh(
        y + 0.19,
        shown["member_connected_band_share"],
        height=0.36,
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.0,
        label="Shared-member link",
    )
    ax.set_yticks(y, shown["display_label"])
    _title(
        ax,
        "Share of mapped bands linked to another selected band",
        "Twenty-five best-covered FUAs · documented shared members or record labels",
    )
    ax.set_xlabel("Connected-band share")
    ax.set_xlim(0, max(1.0, shown["connected_band_share"].max() + 0.08))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0%}"))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_longitudinal_city_change(city: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot listener and follower change for the fixed city catalogues."""

    apply_chart_style()
    shown = city.sort_values("listener_change_pct", ascending=True)
    y = np.arange(len(shown))
    fig, ax = plt.subplots(figsize=(10.8, 6.8))
    ax.barh(
        y - 0.19,
        shown["listener_change_pct"],
        height=0.36,
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.4,
        label="Monthly listeners",
    )
    ax.barh(
        y + 0.19,
        shown["follower_change_pct"],
        height=0.36,
        facecolor=HOUSE["page"],
        edgecolor=HOUSE["warning"],
        linewidth=1.0,
        label="Followers",
    )
    ax.set_yticks(y, shown["city"])
    ax.axvline(0, color=HOUSE["secondary"], linewidth=1)
    _title(
        ax,
        "Change in fixed five-band city catalogues",
        "20 Sep 2025 to 17 Jul 2026 · two observations do not establish a trend",
    )
    ax.set_xlabel("Change from baseline")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_longitudinal_band_change(changes: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot band-level listener versus follower percentage change."""

    apply_chart_style()
    shown = changes.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["monthly_listeners_change_pct", "followers_change_pct"]
    )
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    ax.scatter(
        shown["followers_change_pct"],
        shown["monthly_listeners_change_pct"],
        s=48,
        facecolor=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.6,
    )
    outlier_index = (
        shown["monthly_listeners_change_pct"].abs()
        + shown["followers_change_pct"].abs()
    ).nlargest(5).index
    for row in shown.loc[outlier_index].itertuples():
        ax.annotate(
            row.band,
            (row.followers_change_pct, row.monthly_listeners_change_pct),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color=HOUSE["ink_soft"],
        )
    ax.axhline(0, color=HOUSE["secondary"], linewidth=0.9)
    ax.axvline(0, color=HOUSE["secondary"], linewidth=0.9)
    _title(
        ax,
        "Band-level movement across two Spotify snapshots",
        "Fixed 50-band catalogue · percentage changes can be volatile for smaller acts",
    )
    ax.set_xlabel("Follower change")
    ax.set_ylabel("Monthly-listener change")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f}%"))
    ax.grid()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_spotify_vs_pageviews(audit: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot Spotify followers against annual English Wikipedia pageviews."""

    apply_chart_style()
    shown = audit.dropna(subset=["log10_followers", "log10_pageviews"]).copy()
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    ax.scatter(
        shown["followers"],
        shown["pageviews_total"],
        s=42,
        facecolor=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.55,
        alpha=0.82,
    )
    x = np.geomspace(shown["followers"].min(), shown["followers"].max(), 100)
    model_slope = np.polyfit(shown["log10_followers"], shown["log10_pageviews"], 1)
    ax.plot(x, 10 ** (model_slope[1] + model_slope[0] * np.log10(x)), color=HOUSE["secondary"])
    labels = shown.nlargest(5, "attention_residual_log10").index.union(
        shown.nsmallest(2, "attention_residual_log10").index
    )
    for row in shown.loc[labels].itertuples():
        ax.annotate(
            row.spotify_name,
            (row.followers, row.pageviews_total),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7.8,
            color=HOUSE["ink_soft"],
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    _title(
        ax,
        "Spotify followers and English Wikipedia attention",
        "Popularity-first top 1,000 · Wikipedia user pageviews, Jul 2025–Jun 2026",
    )
    ax.set_xlabel("Spotify followers · log scale")
    ax.set_ylabel("English Wikipedia pageviews · log scale")
    ax.grid()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)


def plot_attention_residuals(audit: pd.DataFrame, *, output_path: Path) -> Path:
    """Plot bands with the largest positive Wikipedia-attention residuals."""

    apply_chart_style()
    shown = audit.dropna(subset=["attention_residual_log10"]).nlargest(
        16, "attention_residual_log10"
    )
    shown = shown.sort_values("attention_residual_log10")
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    ax.barh(
        shown["spotify_name"],
        shown["attention_residual_log10"],
        color=HOUSE["blue"],
        edgecolor=HOUSE["ink_soft"],
        linewidth=0.45,
    )
    _title(
        ax,
        "Bands with more Wikipedia attention than follower count predicts",
        "Positive residual from a log–log descriptive fit; pageviews are attention, not listening",
    )
    ax.set_xlabel("Observed minus expected log10 annual pageviews")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    return _save_figure(fig, output_path)
