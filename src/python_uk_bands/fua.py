"""Build a reproducible UK Functional Urban Area population universe."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests


OECD_FUA_DATASET = "OECD.CFE.EDS,DSD_FUA_DEMO@DF_AGE_SEX"
OECD_FUA_SOURCE_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    f"{OECD_FUA_DATASET},/.A..._T._T...?"
    "startPeriod={year}&endPeriod={year}&"
    "dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
)
OECD_FUA_DATASET_URL = (
    "https://data-explorer.oecd.org/vis?"
    "df%5Bag%5D=OECD.CFE.EDS&"
    "df%5Bds%5D=dsDisseminateFinalDMZ&"
    "df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en"
)

STUDY_LABELS = {
    "UK001F": "London",
    "UK002F": "Birmingham",
    "UK003F": "Leeds",
    "UK004F": "Glasgow",
    "UK006F": "Liverpool",
    "UK007F": "Edinburgh",
    "UK008F": "Manchester",
    "UK009F": "Cardiff",
    "UK010F": "Sheffield",
    "UK011F": "Bristol",
    "UK012F": "Belfast",
    "UK013F": "Newcastle",
    "UK014F": "Leicester",
    "UK018F": "Exeter",
    "UK023F": "Portsmouth",
    "UK025F": "Coventry",
    "UK026F": "Hull",
    "UK029F": "Nottingham",
    "UK515F": "Brighton and Hove",
    "UK518F": "Derby",
    "UK520F": "Southampton",
    "UK559F": "Middlesbrough",
    "UK560F": "Oxford",
    "UK568F": "Cheshire West and Chester",
    "UK569F": "Ipswich",
}


def fetch_oecd_fua_population(
    year: int,
    *,
    request_get=requests.get,
    timeout: float = 60,
) -> tuple[str, str]:
    """Download the OECD city/FUA population extract for one reference year."""
    url = OECD_FUA_SOURCE_URL.format(year=year)
    response = request_get(
        url,
        headers={
            "Accept": "text/csv",
            "User-Agent": (
                "uk-music-cities/1.0 "
                "(reproducible urban-area population research)"
            ),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text, url


def build_uk_fua_universe(
    raw_csv: str,
    *,
    year: int,
    top_n: int | None = None,
    captured_at_utc: str | None = None,
) -> pd.DataFrame:
    """Filter an OECD extract to ranked UK Functional Urban Areas."""
    raw = pd.read_csv(StringIO(raw_csv))
    required = {
        "REF_AREA",
        "Reference area",
        "TERRITORIAL_LEVEL",
        "TIME_PERIOD",
        "OBS_VALUE",
        "OBS_STATUS",
    }
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(f"OECD FUA extract is missing columns: {missing}")

    uk = raw.loc[
        raw["REF_AREA"].astype(str).str.match(r"^UK\d{3}F$")
        & raw["TERRITORIAL_LEVEL"].eq("FUA")
        & raw["TIME_PERIOD"].eq(year),
        [
            "REF_AREA",
            "Reference area",
            "TIME_PERIOD",
            "OBS_VALUE",
            "OBS_STATUS",
        ],
    ].copy()
    uk = uk.rename(
        columns={
            "REF_AREA": "fua_code",
            "Reference area": "official_fua_name",
            "TIME_PERIOD": "population_year",
            "OBS_VALUE": "population",
            "OBS_STATUS": "observation_status",
        }
    )
    if uk.empty:
        raise ValueError(f"OECD extract contains no UK FUA observations for {year}")
    if uk["fua_code"].duplicated().any():
        duplicates = uk.loc[uk["fua_code"].duplicated(), "fua_code"].tolist()
        raise ValueError(f"Duplicate UK FUA observations: {duplicates}")
    if uk["population"].isna().any() or (uk["population"] <= 0).any():
        raise ValueError("UK FUA populations must be complete and positive")
    if not uk["observation_status"].eq("A").all():
        statuses = sorted(uk["observation_status"].dropna().unique())
        raise ValueError(f"Unexpected OECD observation statuses: {statuses}")

    captured_at_utc = captured_at_utc or datetime.now(timezone.utc).isoformat()
    uk["population"] = uk["population"].astype(int)
    uk = uk.sort_values(
        ["population", "official_fua_name"],
        ascending=[False, True],
    ).reset_index(drop=True)
    uk.insert(0, "uk_population_rank", uk.index + 1)
    uk.insert(
        3,
        "study_city_label",
        uk["fua_code"].map(STUDY_LABELS).fillna(uk["official_fua_name"]),
    )
    uk["source_dataset"] = "OECD Population by age and sex - Cities and FUAs"
    uk["source_dataset_url"] = OECD_FUA_DATASET_URL
    uk["territorial_definition"] = "OECD/EU Functional Urban Area"
    uk["captured_at_utc"] = captured_at_utc

    if top_n is not None:
        if top_n < 1:
            raise ValueError("top_n must be positive")
        uk = uk.head(top_n).copy()
    return uk


def validate_top_fua_universe(
    universe: pd.DataFrame,
    *,
    expected_rows: int,
    year: int,
) -> None:
    """Validate a frozen population-selected study universe."""
    required = {
        "uk_population_rank",
        "fua_code",
        "official_fua_name",
        "study_city_label",
        "population",
        "population_year",
        "observation_status",
        "source_dataset_url",
        "territorial_definition",
    }
    missing = sorted(required.difference(universe.columns))
    if missing:
        raise ValueError(f"FUA universe is missing columns: {missing}")
    if len(universe) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} FUAs, found {len(universe)}"
        )
    if universe["fua_code"].duplicated().any():
        raise ValueError("FUA codes must be unique")
    if universe["study_city_label"].duplicated().any():
        raise ValueError("Study city labels must be unique")
    if universe["uk_population_rank"].tolist() != list(
        range(1, expected_rows + 1)
    ):
        raise ValueError("FUA population ranks must be consecutive from one")
    if not universe["population_year"].eq(year).all():
        raise ValueError(f"Every FUA population must use reference year {year}")
    if not universe["observation_status"].eq("A").all():
        raise ValueError("Every FUA observation must have normal OECD status A")
    if not universe["population"].is_monotonic_decreasing:
        raise ValueError("FUA universe must be sorted by decreasing population")
