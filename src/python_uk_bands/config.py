"""Project-level configuration constants."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = PROJECT_ROOT / "reference"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHART_DIR = PROJECT_ROOT / "artifacts" / "charts"

MUSICBRAINZ_RAW_DIR = RAW_DATA_DIR / "musicbrainz"
SPOTIFY_RAW_DIR = RAW_DATA_DIR / "spotify"

SHORTLIST_PATH = REFERENCE_DIR / "original_shortlist.csv"
POPULARITY_FIRST_SNAPSHOT_ID = "20260718T204522Z"
POPULARITY_FIRST_TOP1000_BANDS_PATH = (
    PROCESSED_DATA_DIR
    / f"popularity_first_top1000_{POPULARITY_FIRST_SNAPSHOT_ID}_bands.csv"
)
FUA_POPULATION_YEAR = 2024
FUA_POPULATION_SNAPSHOT_ID = "20260830T221015Z"
FUA_POPULATION_PATH = (
    PROCESSED_DATA_DIR
    / f"uk_fua_population_{FUA_POPULATION_YEAR}_{FUA_POPULATION_SNAPSHOT_ID}.csv"
)
FUA_TOP20_PATH = REFERENCE_DIR / f"uk_fua_top20_{FUA_POPULATION_YEAR}.csv"
FINAL_STUDY_SNAPSHOT_ID = "20260718T204000Z"
FINAL_STUDY_BAND_METRICS_PATH = (
    PROCESSED_DATA_DIR
    / f"fua_top10_band_metrics_{FINAL_STUDY_SNAPSHOT_ID}.csv"
)
FINAL_STUDY_RANKINGS_PATH = (
    PROCESSED_DATA_DIR / f"fua_top10_rankings_{FINAL_STUDY_SNAPSHOT_ID}.csv"
)
SPOTIFY_IDENTIFIERS_PATH = REFERENCE_DIR / "spotify_band_ids.json"
SHORTLIST_METRICS_PATH = PROCESSED_DATA_DIR / "shortlist_spotify_metrics.json"

MUSICBRAINZ_ARTIST_ENDPOINT = "https://musicbrainz.org/ws/2/artist"
DEFAULT_MUSICBRAINZ_USER_AGENT = os.getenv(
    "MUSICBRAINZ_USER_AGENT",
    "python-uk-bands/1.0 (contact: info@danielpradilla.info)",
)
