"""Discovery and selection helpers for frozen 50-band Spotify snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .config import PROCESSED_DATA_DIR, SHORTLIST_METRICS_PATH


SNAPSHOT_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
SNAPSHOT_GLOB = "shortlist_spotify_metrics_*.json"


@dataclass(frozen=True)
class ShortlistSnapshot:
    """One selectable 50-band metrics snapshot."""

    snapshot_id: str
    metrics_path: Path
    is_publication: bool = False


def list_shortlist_snapshot_ids(
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> list[str]:
    """Return timestamped candidate snapshot IDs in filename order."""
    prefix = "shortlist_spotify_metrics_"
    snapshot_ids = [
        path.stem.removeprefix(prefix)
        for path in processed_dir.glob(SNAPSHOT_GLOB)
        if SNAPSHOT_ID_PATTERN.fullmatch(path.stem.removeprefix(prefix))
    ]
    return sorted(snapshot_ids)


def resolve_shortlist_snapshot(
    selector: str,
    *,
    processed_dir: Path = PROCESSED_DATA_DIR,
    publication_path: Path = SHORTLIST_METRICS_PATH,
) -> ShortlistSnapshot:
    """Resolve ``publication``, ``latest``, a date, or an exact timestamp."""
    normalized = selector.strip()
    if normalized == "publication":
        if not publication_path.exists():
            raise FileNotFoundError(
                f"Publication snapshot does not exist: {publication_path}"
            )
        return ShortlistSnapshot(
            snapshot_id="publication",
            metrics_path=publication_path,
            is_publication=True,
        )

    available = list_shortlist_snapshot_ids(processed_dir)
    if not available:
        raise FileNotFoundError("No timestamped shortlist snapshots are available")
    if normalized == "latest":
        snapshot_id = available[-1]
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        date_prefix = normalized.replace("-", "")
        matches = [value for value in available if value.startswith(date_prefix)]
        if not matches:
            raise FileNotFoundError(
                f"No shortlist snapshot exists for {normalized}"
            )
        snapshot_id = matches[-1]
    elif normalized in available:
        snapshot_id = normalized
    else:
        choices = ", ".join(available)
        raise FileNotFoundError(
            f"Unknown shortlist snapshot {selector!r}; available: {choices}"
        )

    return ShortlistSnapshot(
        snapshot_id=snapshot_id,
        metrics_path=processed_dir / f"shortlist_spotify_metrics_{snapshot_id}.json",
    )
