"""Discovery and selection helpers for frozen scene-depth snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .config import PROCESSED_DATA_DIR


SNAPSHOT_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
METRICS_GLOB = "scene_depth_band_metrics_*.csv"


@dataclass(frozen=True)
class SceneDepthSnapshot:
    """Paths belonging to one complete scene-depth snapshot."""

    snapshot_id: str
    metrics_path: Path
    rankings_path: Path


def list_scene_depth_snapshot_ids(
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> list[str]:
    """Return complete snapshot IDs in chronological filename order."""
    snapshot_ids: list[str] = []
    prefix = "scene_depth_band_metrics_"
    for metrics_path in processed_dir.glob(METRICS_GLOB):
        snapshot_id = metrics_path.stem.removeprefix(prefix)
        rankings_path = processed_dir / f"scene_depth_rankings_{snapshot_id}.csv"
        if SNAPSHOT_ID_PATTERN.fullmatch(snapshot_id) and rankings_path.exists():
            snapshot_ids.append(snapshot_id)
    return sorted(snapshot_ids)


def resolve_scene_depth_snapshot(
    selector: str,
    *,
    processed_dir: Path = PROCESSED_DATA_DIR,
) -> SceneDepthSnapshot:
    """Resolve ``latest``, an ISO date, or an exact timestamp to one snapshot."""
    available = list_scene_depth_snapshot_ids(processed_dir)
    if not available:
        raise FileNotFoundError("No complete scene-depth snapshots are available")

    normalized = selector.strip()
    if normalized == "latest":
        snapshot_id = available[-1]
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        date_prefix = normalized.replace("-", "")
        matches = [value for value in available if value.startswith(date_prefix)]
        if not matches:
            raise FileNotFoundError(
                f"No complete scene-depth snapshot exists for {normalized}"
            )
        snapshot_id = matches[-1]
    elif normalized in available:
        snapshot_id = normalized
    else:
        choices = ", ".join(available)
        raise FileNotFoundError(
            f"Unknown scene-depth snapshot {selector!r}; available: {choices}"
        )

    return SceneDepthSnapshot(
        snapshot_id=snapshot_id,
        metrics_path=processed_dir / f"scene_depth_band_metrics_{snapshot_id}.csv",
        rankings_path=processed_dir / f"scene_depth_rankings_{snapshot_id}.csv",
    )
