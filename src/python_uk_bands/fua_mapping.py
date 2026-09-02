"""Build auditable origin-to-FUA mappings from official municipality data."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


OECD_MUNICIPALITY_SOURCE = (
    "https://www.oecd.org/content/dam/oecd/en/data/datasets/"
    "oecd-definition-of-cities-and-functional-urban-areas/"
    "list_of_municipalities_in_FUAs_and_Cities.csv"
)

NON_UK_ORIGINS = {
    "Dublin",
    "Hamburg",
    "New York City",
    "Redcliffe",
    "United States",
}


def normalize_admin_name(value: str) -> str:
    """Normalize UK locality and local-authority labels for matching."""

    normalized = (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode()
        .casefold()
        .replace("&", "and")
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    prefixes = [
        "london borough of ",
        "royal borough of ",
        "metropolitan borough of ",
        "borough of ",
        "city of ",
        "district of ",
    ]
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    suffixes = [" county borough", " borough council", " city council", " city"]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.strip()


def _entity_ancestry(
    qid: str,
    entities: dict[str, dict[str, object]],
    *,
    max_depth: int = 6,
) -> list[tuple[int, str, str]]:
    seen = {qid}
    level = [qid]
    rows: list[tuple[int, str, str]] = []
    for depth in range(max_depth + 1):
        next_level: list[str] = []
        for entity_id in level:
            entity = entities.get(entity_id, {})
            rows.append((depth, entity_id, str(entity.get("label", ""))))
            for parent in entity.get("located_in", []):
                parent_id = str(parent)
                if parent_id not in seen:
                    seen.add(parent_id)
                    next_level.append(parent_id)
        level = next_level
        if not level:
            break
    return rows


def build_origin_fua_mapping(
    bands: pd.DataFrame,
    population: pd.DataFrame,
    municipalities: pd.DataFrame,
    entity_snapshot: dict,
    legacy_mapping: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map each selected origin cluster to an OECD FUA or explicit exclusion."""

    required_bands = {
        "origin_cluster",
        "formation_qid",
        "origin_override",
        "returned_spotify_id",
        "spotify_name",
        "monthly_listeners",
    }
    required_population = {
        "fua_code",
        "official_fua_name",
        "study_city_label",
    }
    required_municipalities = {
        "Country",
        "ISO3 code",
        "Municipality name",
        "FUA ID",
        "FUA name",
    }
    required_legacy = {
        "origin_cluster",
        "fua_code",
        "mapping_tier",
        "mapping_method",
        "notes",
    }
    for frame, required, label in [
        (bands, required_bands, "bands"),
        (population, required_population, "population"),
        (municipalities, required_municipalities, "municipalities"),
        (legacy_mapping, required_legacy, "legacy mapping"),
    ]:
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} is missing columns: {sorted(missing)}")

    if bands["returned_spotify_id"].duplicated().any():
        raise ValueError("Bands must contain unique returned Spotify IDs")
    if population["fua_code"].duplicated().any():
        raise ValueError("Population must contain unique FUA codes")
    if legacy_mapping["origin_cluster"].duplicated().any():
        raise ValueError("Legacy mapping must contain unique origin clusters")

    uk_municipalities = municipalities.loc[
        municipalities["ISO3 code"].eq("GBR")
    ].copy()
    uk_municipalities["normalized_name"] = uk_municipalities[
        "Municipality name"
    ].map(normalize_admin_name)
    conflicts = (
        uk_municipalities.groupby("normalized_name")["FUA ID"].nunique()
    )
    if conflicts.gt(1).any():
        raise ValueError("Normalized municipality names map to multiple FUAs")
    municipality_lookup = (
        uk_municipalities.sort_values(["normalized_name", "Municipality name"])
        .drop_duplicates("normalized_name")
        .set_index("normalized_name")
    )

    population_codes = set(population["fua_code"])
    population_name_lookup: dict[str, str] = {}
    for row in population.itertuples(index=False):
        population_name_lookup[normalize_admin_name(row.official_fua_name)] = (
            row.fua_code
        )
        population_name_lookup[normalize_admin_name(row.study_city_label)] = (
            row.fua_code
        )
    legacy_lookup = legacy_mapping.set_index("origin_cluster")
    entities: dict[str, dict[str, object]] = entity_snapshot["entities"]

    mapping_rows: list[dict[str, str]] = []
    evidence_rows: list[dict[str, str | int]] = []
    grouped = bands.groupby("origin_cluster", dropna=False, sort=True)
    for origin_value, origin_bands in grouped:
        origin = str(origin_value)
        band_count = origin_bands["returned_spotify_id"].nunique()
        top_band = origin_bands.sort_values(
            ["monthly_listeners", "spotify_name"], ascending=[False, True]
        ).iloc[0]["spotify_name"]
        qids = sorted(
            {
                qid
                for value in origin_bands["formation_qid"]
                for qid in str(value).split("|")
                if re.fullmatch(r"Q\d+", qid)
            }
        )
        direct_labels = [
            str(entities.get(qid, {}).get("label", "")) for qid in qids
        ]

        candidate_rows: list[tuple[int, str, str, str]] = []
        origin_normalized = normalize_admin_name(origin)
        if origin_normalized in municipality_lookup.index:
            municipality = municipality_lookup.loc[origin_normalized]
            candidate_rows.append(
                (
                    0,
                    str(municipality["Municipality name"]),
                    str(municipality["FUA ID"]),
                    str(municipality["FUA name"]),
                )
            )

        has_override = origin_bands["origin_override"].ne("").any()
        usable_qids = [
            qid
            for qid, label in zip(qids, direct_labels)
            if (
                normalize_admin_name(label) == origin_normalized
                or (len(qids) == 1 and not has_override)
            )
        ]
        for qid in usable_qids:
            for depth, _, label in _entity_ancestry(qid, entities):
                normalized_label = normalize_admin_name(label)
                if normalized_label in municipality_lookup.index:
                    municipality = municipality_lookup.loc[normalized_label]
                    candidate_rows.append(
                        (
                            depth,
                            str(municipality["Municipality name"]),
                            str(municipality["FUA ID"]),
                            str(municipality["FUA name"]),
                        )
                    )

        candidate_rows = sorted(set(candidate_rows))
        candidate_codes = sorted({row[2] for row in candidate_rows})
        matched_municipalities = sorted({row[1] for row in candidate_rows})
        candidate_fua_names = sorted({row[3] for row in candidate_rows})

        fua_code = ""
        mapping_tier = "excluded_no_defensible_fua"
        mapping_method = "no_reviewed_assignment"
        notes = (
            "No assignment is made because the resolved place is not in the "
            "official OECD municipality-to-FUA crosswalk."
        )
        if origin == "":
            mapping_method = "no_resolved_origin"
            notes = (
                "No FUA assignment is possible while the band's origin "
                "remains unresolved."
            )
        elif origin in NON_UK_ORIGINS:
            mapping_tier = "excluded_non_uk"
            mapping_method = "outside_uk_fua_universe"
            notes = f"{origin} is outside the UK FUA universe."
        elif len(candidate_codes) == 1:
            candidate_code = candidate_codes[0]
            municipality_text = ", ".join(matched_municipalities)
            fua_name_text = ", ".join(candidate_fua_names)
            if candidate_code in population_codes:
                fua_code = candidate_code
                mapping_tier = "strict"
                mapping_method = "official_oecd_municipality_crosswalk"
                notes = (
                    f"The official OECD municipality list assigns "
                    f"{municipality_text} to {fua_name_text} FUA."
                )
            else:
                mapping_tier = "excluded_missing_population"
                mapping_method = "official_fua_missing_population"
                notes = (
                    f"The official OECD municipality list assigns "
                    f"{municipality_text} to {fua_name_text} "
                    f"({candidate_code}), but that FUA is absent from the "
                    "frozen population denominator."
                )
        elif len(candidate_codes) > 1:
            mapping_method = "ambiguous_official_crosswalk"
            notes = (
                "The available place hierarchy reaches multiple official FUAs: "
                + ", ".join(candidate_codes)
                + "."
            )
        elif origin_normalized in population_name_lookup:
            fua_code = population_name_lookup[origin_normalized]
            mapping_tier = "strict"
            mapping_method = "exact_fua_label"
            notes = "Origin matches an official or study FUA label."
        elif origin in legacy_lookup.index:
            legacy = legacy_lookup.loc[origin]
            if legacy["mapping_tier"] in {"strict", "reviewed_extended"}:
                fua_code = str(legacy["fua_code"])
                mapping_tier = str(legacy["mapping_tier"])
                mapping_method = "reviewed_legacy_assignment"
                notes = (
                    "Preserved from the reviewed top-200 mapping because the "
                    "official municipality crosswalk does not resolve the "
                    f"reported place. Prior note: {legacy['notes']}"
                )
            elif legacy["mapping_tier"] == "excluded_non_uk":
                mapping_tier = "excluded_non_uk"
                mapping_method = "outside_uk_fua_universe"
                notes = str(legacy["notes"])

        mapping_rows.append(
            {
                "origin_cluster": origin,
                "fua_code": fua_code,
                "mapping_tier": mapping_tier,
                "mapping_method": mapping_method,
                "notes": notes,
            }
        )
        source_urls = [OECD_MUNICIPALITY_SOURCE]
        source_urls.extend(
            f"https://www.wikidata.org/wiki/{qid}" for qid in usable_qids
        )
        evidence_rows.append(
            {
                "origin_cluster": origin,
                "band_count": int(band_count),
                "top_band": str(top_band),
                "formation_qids": "|".join(qids),
                "direct_entity_labels": "|".join(direct_labels),
                "matched_municipalities": "|".join(matched_municipalities),
                "candidate_fua_codes": "|".join(candidate_codes),
                "candidate_fua_names": "|".join(candidate_fua_names),
                "mapping_tier": mapping_tier,
                "fua_code": fua_code,
                "mapping_method": mapping_method,
                "source_urls": "|".join(source_urls),
                "notes": notes,
            }
        )

    mapping = pd.DataFrame(mapping_rows)
    evidence = pd.DataFrame(evidence_rows)
    if mapping["origin_cluster"].duplicated().any():
        raise ValueError("Generated mapping contains duplicate origin clusters")
    if set(mapping["origin_cluster"]) != set(bands["origin_cluster"]):
        raise ValueError("Generated mapping does not cover every origin cluster")
    return mapping, evidence
