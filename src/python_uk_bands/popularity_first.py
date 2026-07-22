"""Selection and origin helpers for the popularity-first experiment."""

from __future__ import annotations

import re

import pandas as pd

from .matching import normalize_name


GENERIC_ORIGINS = {"", "england", "great britain", "united kingdom", "uk"}

# Editorial clustering is intentionally conservative. It combines named
# districts with their commonly understood city and keeps other places as
# reported. These are not claimed to be official FUA assignments.
ORIGIN_CLUSTER = {
    "abingdon-on-thames": "Oxford",
    "bushey": "London",
    "deptford": "London",
    "leyton": "London",
    "lewisham": "London",
    "london borough of hackney": "London",
    "london borough of islington": "London",
    "salford": "Manchester",
    "stockport": "Manchester",
    "west hampstead": "London",
    "wigan": "Manchester",
    "wilmslow": "Manchester",
}

MULTI_PLACE_ORIGIN = {
    "braintree|essex": "Braintree",
    "england|hertford|london": "Hertford",
    "godalming|surrey": "Godalming",
}


def resolve_origin(
    formation_label: str,
    override: str = "",
) -> tuple[str, str]:
    """Resolve a reported formation label to a conservative origin cluster."""

    if override.strip():
        return override.strip(), "reviewed_override"
    raw = formation_label.strip()
    raw_key = raw.casefold()
    if raw_key in MULTI_PLACE_ORIGIN:
        return MULTI_PLACE_ORIGIN[raw_key], "reviewed_multi_place_rule"
    parts = [
        part.strip()
        for part in raw.split("|")
        if part.strip().casefold() not in GENERIC_ORIGINS
    ]
    if not parts:
        return "", "unresolved_generic_or_missing"
    if len(parts) > 1:
        return "", "unresolved_multiple_places"
    place = parts[0]
    return ORIGIN_CLUSTER.get(place.casefold(), place), (
        "editorial_city_cluster"
        if place.casefold() in ORIGIN_CLUSTER
        else "reported_place"
    )


def select_top_groups(
    candidates: pd.DataFrame,
    metrics: pd.DataFrame,
    overrides: pd.DataFrame,
    top_n: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit identities, deduplicate redirected pages, and select top groups."""

    candidate_frame = candidates.rename(
        columns={"spotify_id": "requested_spotify_id"}
    )
    metric_frame = metrics.rename(
        columns={
            "band": "capture_key",
            "spotify_id": "returned_spotify_id",
        }
    )
    merged = metric_frame.merge(
        candidate_frame,
        on="capture_key",
        how="left",
        validate="one_to_one",
    )
    if merged["requested_spotify_id"].eq("").any():
        raise ValueError("All metric rows must match a candidate capture key")

    override_frame = overrides.rename(
        columns={"spotify_id": "requested_spotify_id"}
    )
    merged = merged.merge(
        override_frame,
        on="requested_spotify_id",
        how="left",
        validate="many_to_one",
    )
    for column in [
        "identity_decision",
        "origin_override",
        "reason",
        "source_url",
    ]:
        merged[column] = merged[column].fillna("")

    merged["identity_name_match"] = merged.apply(
        lambda row: normalize_name(row["spotify_expected_name"])
        == normalize_name(row["spotify_name"]),
        axis=1,
    )
    merged["identity_status"] = merged["identity_name_match"].map(
        {True: "accepted_exact_name", False: "rejected_name_mismatch"}
    )
    merged.loc[
        merged["identity_decision"].eq("approve"), "identity_status"
    ] = "accepted_reviewed_alias"
    merged.loc[
        merged["identity_decision"].eq("reject"), "identity_status"
    ] = "rejected_reviewed"
    merged["identity_accepted"] = merged["identity_status"].str.startswith(
        "accepted"
    )

    orchestra_pattern = re.compile(r"\borchestra\b", flags=re.IGNORECASE)
    merged["band_eligible"] = ~(
        merged["spotify_name"].str.contains(orchestra_pattern)
        | merged["instance_label"].str.contains(orchestra_pattern)
    )
    merged["eligibility_status"] = merged["band_eligible"].map(
        {True: "eligible_group_or_duo", False: "excluded_orchestra"}
    )
    merged["requested_is_returned"] = merged[
        "requested_spotify_id"
    ].eq(merged["returned_spotify_id"])
    merged = merged.sort_values(
        [
            "monthly_listeners",
            "requested_is_returned",
            "identity_accepted",
            "capture_key",
        ],
        ascending=[False, False, False, True],
    )
    merged["redirect_duplicate"] = merged.duplicated(
        "returned_spotify_id", keep="first"
    )

    selection_pool = merged[
        merged["identity_accepted"]
        & merged["band_eligible"]
        & ~merged["redirect_duplicate"]
    ].copy()
    if len(selection_pool) < top_n:
        raise ValueError(
            f"Only {len(selection_pool)} eligible identities for top {top_n}"
        )
    selected = selection_pool.head(top_n).copy()
    selected.insert(0, "popularity_rank", range(1, len(selected) + 1))
    selected[["origin_cluster", "origin_resolution"]] = selected.apply(
        lambda row: pd.Series(
            resolve_origin(
                row["formation_label"],
                row["origin_override"],
            )
        ),
        axis=1,
    )
    return selected.reset_index(drop=True), merged.reset_index(drop=True)


def build_origin_concentration(selected: pd.DataFrame) -> pd.DataFrame:
    """Aggregate band counts and captured reach by resolved origin."""

    frame = selected.copy()
    frame["origin_cluster_display"] = frame["origin_cluster"].where(
        frame["origin_cluster"].ne(""), "Unresolved"
    )
    grouped = (
        frame.groupby("origin_cluster_display", as_index=False)
        .agg(
            band_count=("returned_spotify_id", "nunique"),
            monthly_listeners_total=("monthly_listeners", "sum"),
        )
        .rename(columns={"origin_cluster_display": "origin_cluster"})
    )
    grouped["band_share"] = grouped["band_count"] / len(frame)
    grouped["listener_share"] = (
        grouped["monthly_listeners_total"]
        / grouped["monthly_listeners_total"].sum()
    )
    return grouped.sort_values(
        ["band_count", "monthly_listeners_total", "origin_cluster"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def attach_fua_population(
    selected: pd.DataFrame,
    mapping: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Attach one reviewed FUA decision and population to every selected band."""

    required_band_columns = {
        "origin_cluster",
        "returned_spotify_id",
        "monthly_listeners",
    }
    required_mapping_columns = {
        "origin_cluster",
        "fua_code",
        "mapping_tier",
        "mapping_method",
        "notes",
    }
    required_population_columns = {
        "fua_code",
        "official_fua_name",
        "study_city_label",
        "population_year",
        "population",
    }
    for frame, required, label in [
        (selected, required_band_columns, "selected bands"),
        (mapping, required_mapping_columns, "origin mapping"),
        (population, required_population_columns, "FUA population"),
    ]:
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} is missing columns: {sorted(missing)}")

    if mapping["origin_cluster"].duplicated().any():
        duplicates = mapping.loc[
            mapping["origin_cluster"].duplicated(keep=False),
            "origin_cluster",
        ].tolist()
        raise ValueError(f"Origin mapping contains duplicates: {duplicates}")
    if population["fua_code"].duplicated().any():
        raise ValueError("FUA population contains duplicate FUA codes")
    if (population["population"] <= 0).any():
        raise ValueError("FUA populations must be positive")

    selected_origins = set(selected["origin_cluster"])
    mapped_origins = set(mapping["origin_cluster"])
    missing_origins = sorted(selected_origins.difference(mapped_origins))
    extra_origins = sorted(mapped_origins.difference(selected_origins))
    if missing_origins or extra_origins:
        raise ValueError(
            "Origin mapping must cover the selected origin universe exactly; "
            f"missing={missing_origins}, extra={extra_origins}"
        )

    allowed_tiers = {
        "strict",
        "reviewed_extended",
        "excluded_non_uk",
        "excluded_no_defensible_fua",
        "excluded_missing_population",
    }
    invalid_tiers = sorted(set(mapping["mapping_tier"]) - allowed_tiers)
    if invalid_tiers:
        raise ValueError(f"Unknown origin mapping tiers: {invalid_tiers}")
    needs_fua = mapping["mapping_tier"].isin(
        {"strict", "reviewed_extended"}
    )
    if mapping.loc[needs_fua, "fua_code"].eq("").any():
        raise ValueError("Included mapping tiers require a FUA code")
    if mapping.loc[~needs_fua, "fua_code"].ne("").any():
        raise ValueError("Excluded mapping tiers must not contain a FUA code")

    attached = selected.merge(
        mapping,
        on="origin_cluster",
        how="left",
        validate="many_to_one",
    ).merge(
        population[
            [
                "fua_code",
                "official_fua_name",
                "study_city_label",
                "population_year",
                "population",
            ]
        ],
        on="fua_code",
        how="left",
        validate="many_to_one",
    )
    included = attached["mapping_tier"].isin(
        {"strict", "reviewed_extended"}
    )
    if attached.loc[included, "population"].isna().any():
        missing_codes = attached.loc[
            included & attached["population"].isna(), "fua_code"
        ].unique()
        raise ValueError(
            f"Mapped FUA codes missing from population data: {missing_codes}"
        )
    return attached


def build_population_adjusted_metrics(
    attached: pd.DataFrame,
    *,
    included_tiers: set[str],
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Aggregate a popularity-selected sample and normalize by FUA population."""

    allowed_included_tiers = {"strict", "reviewed_extended"}
    if not included_tiers or not included_tiers.issubset(
        allowed_included_tiers
    ):
        raise ValueError(
            "included_tiers must be a non-empty subset of "
            f"{sorted(allowed_included_tiers)}"
        )

    included = attached["mapping_tier"].isin(included_tiers)
    mapped = attached.loc[included].copy()
    grouped = (
        mapped.groupby(
            [
                "fua_code",
                "official_fua_name",
                "study_city_label",
                "population_year",
                "population",
            ],
            as_index=False,
        )
        .agg(
            band_count=("returned_spotify_id", "nunique"),
            monthly_listeners_total=("monthly_listeners", "sum"),
        )
    )
    grouped["population"] = grouped["population"].astype(int)
    grouped["selected_bands_per_million_residents"] = (
        grouped["band_count"] / grouped["population"] * 1_000_000
    )
    grouped["selected_monthly_listeners_per_resident"] = (
        grouped["monthly_listeners_total"] / grouped["population"]
    )
    # Preserve the original top-100 field names so the frozen predecessor
    # notebooks remain rerunnable against newly generated outputs.
    grouped["top100_bands_per_million_residents"] = grouped[
        "selected_bands_per_million_residents"
    ]
    grouped["top100_monthly_listeners_per_resident"] = grouped[
        "selected_monthly_listeners_per_resident"
    ]
    grouped["one_band_fua"] = grouped["band_count"].eq(1)
    grouped["rank_by_listener_reach_per_resident"] = (
        grouped["selected_monthly_listeners_per_resident"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    grouped["rank_by_bands_per_million"] = (
        grouped["selected_bands_per_million_residents"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    grouped = grouped.sort_values(
        [
            "rank_by_listener_reach_per_resident",
            "rank_by_bands_per_million",
            "study_city_label",
        ]
    ).reset_index(drop=True)

    total_reach = attached["monthly_listeners"].sum()
    mapped_reach = mapped["monthly_listeners"].sum()
    coverage: dict[str, float | int] = {
        "selected_bands": int(attached["returned_spotify_id"].nunique()),
        "mapped_bands": int(mapped["returned_spotify_id"].nunique()),
        "mapped_band_share": float(
            mapped["returned_spotify_id"].nunique()
            / attached["returned_spotify_id"].nunique()
        ),
        "selected_listener_reach": int(total_reach),
        "mapped_listener_reach": int(mapped_reach),
        "mapped_listener_reach_share": float(mapped_reach / total_reach),
        "mapped_origin_clusters": int(mapped["origin_cluster"].nunique()),
        "mapped_fuas": int(grouped["fua_code"].nunique()),
    }
    return grouped, coverage
