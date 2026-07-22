"""Project-level configuration constants."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = PROJECT_ROOT / "reference"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
CHART_DIR = PROJECT_ROOT / "artifacts" / "charts"

MUSICBRAINZ_RAW_DIR = RAW_DATA_DIR / "musicbrainz"
SPOTIFY_RAW_DIR = RAW_DATA_DIR / "spotify"

SHORTLIST_PATH = REFERENCE_DIR / "original_shortlist.csv"
BUILT_UP_AREAS_PATH = REFERENCE_DIR / "built_up_areas.csv"
SPOTIFY_IDENTIFIERS_PATH = REFERENCE_DIR / "spotify_band_ids.json"
SHORTLIST_METRICS_PATH = PROCESSED_DATA_DIR / "shortlist_spotify_metrics.json"

MUSICBRAINZ_ARTIST_ENDPOINT = "https://musicbrainz.org/ws/2/artist"
MUSICBRAINZ_AREA_ENDPOINT = "https://musicbrainz.org/ws/2/area"
MUSICBRAINZ_API_LIMIT = 100
DEFAULT_MUSICBRAINZ_USER_AGENT = os.getenv(
    "MUSICBRAINZ_USER_AGENT",
    "python-uk-bands/1.0 (contact: info@danielpradilla.info)",
)
