"""Build and validate the separate top-20 Functional Urban Area catalogue."""

from __future__ import annotations

import pandas as pd


SPOTIFY_DISPLAY_NAME_OVERRIDES = {
    "The Fire Engines": "Fire Engines",
}


def build_top20_catalog(
    *,
    scene_depth_catalog: pd.DataFrame,
    existing_metrics: pd.DataFrame,
    additions_review: pd.DataFrame,
    fua_universe: pd.DataFrame,
) -> pd.DataFrame:
    """Combine 90 reused bands with 110 separately reviewed candidates."""
    top20_cities = set(fua_universe["study_city_label"])
    reused = scene_depth_catalog.loc[
        scene_depth_catalog["original_city_label"].isin(top20_cities)
    ].copy()
    reused = reused.merge(
        existing_metrics[["band", "spotify_id", "spotify_name"]],
        left_on="band_name",
        right_on="band",
        validate="one_to_one",
    )
    reused_rows = pd.DataFrame(
        {
            "band_name": reused["band_name"],
            "study_city_label": reused["original_city_label"],
            "claimed_formation_place": reused["original_city_label"],
            "origin_review_status": "reviewed",
            "origin_alignment": "existing_catalogue",
            "origin_evidence_url": reused["origin_evidence_url"],
            "origin_confidence": reused["origin_confidence"],
            "spotify_id": reused["spotify_id"],
            "spotify_name_prior": reused["spotify_name"],
            "spotify_expected_name": reused["spotify_match_name"].where(
                reused["spotify_match_name"].ne(""),
                reused["band_name"],
            ),
            "musicbrainz_id": reused["musicbrainz_id"],
            "wikidata_id": "",
            "catalogue_source": "reused balanced 100-band catalogue",
            "selection_source": reused["selection_source"],
            "notes": reused["notes"].fillna(""),
        }
    )

    additions = additions_review.copy()
    additions_rows = pd.DataFrame(
        {
            "band_name": additions["band_name"],
            "study_city_label": additions["study_city_label"],
            "claimed_formation_place": additions["claimed_formation_place"],
            "origin_review_status": additions["origin_review_status"],
            "origin_alignment": additions["origin_alignment"],
            "origin_evidence_url": additions["evidence_url"],
            "origin_confidence": additions["origin_alignment"].map(
                {"exact": "high", "review_required": "low"}
            ),
            "spotify_id": additions["spotify_id"],
            "spotify_name_prior": additions.get("musicbrainz_name", ""),
            "spotify_expected_name": additions["band_name"].map(
                SPOTIFY_DISPLAY_NAME_OVERRIDES
            ).fillna(additions["band_name"]),
            "musicbrainz_id": additions["musicbrainz_id"],
            "wikidata_id": additions["wikidata_id"],
            "catalogue_source": "top-20 city candidate review",
            "selection_source": additions["selection_source"],
            "notes": additions["notes"],
        }
    )

    combined = pd.concat([reused_rows, additions_rows], ignore_index=True)
    combined = combined.merge(
        fua_universe[
            [
                "uk_population_rank",
                "fua_code",
                "official_fua_name",
                "study_city_label",
                "population_year",
                "population",
                "territorial_definition",
                "source_dataset_url",
            ]
        ],
        on="study_city_label",
        validate="many_to_one",
    )
    combined["catalogue_review_ready"] = (
        combined["origin_review_status"].eq("reviewed")
        & combined["spotify_id"].ne("")
    )
    combined = combined.sort_values(
        ["uk_population_rank", "band_name"]
    ).reset_index(drop=True)
    validate_top20_catalog(combined)
    return combined


def validate_top20_catalog(catalog: pd.DataFrame) -> None:
    """Validate the balanced population-selected experimental design."""
    required = {
        "band_name",
        "study_city_label",
        "population",
        "population_year",
        "fua_code",
        "uk_population_rank",
        "spotify_id",
    }
    missing = sorted(required.difference(catalog.columns))
    if missing:
        raise ValueError(f"Top-20 catalogue is missing columns: {missing}")
    if len(catalog) != 200:
        raise ValueError(f"Expected 200 bands, found {len(catalog)}")
    if catalog["band_name"].duplicated().any():
        duplicates = catalog.loc[
            catalog["band_name"].duplicated(keep=False),
            "band_name",
        ].tolist()
        raise ValueError(f"Band names must be unique: {duplicates}")
    city_counts = catalog.groupby("study_city_label").size()
    if len(city_counts) != 20 or not city_counts.eq(10).all():
        observed = ", ".join(
            f"{city}={count}" for city, count in city_counts.items()
        )
        raise ValueError(f"Expected 20 cities with ten bands each; {observed}")
    if catalog["population"].isna().any() or (catalog["population"] <= 0).any():
        raise ValueError("Every catalogue row needs a positive FUA population")
    if catalog.groupby("study_city_label")["population"].nunique().max() != 1:
        raise ValueError("Each city must have one population denominator")
