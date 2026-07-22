"""Create and restore checksummed project data snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

from .config import PROJECT_ROOT, SNAPSHOT_DIR


DEFAULT_SNAPSHOT_PATHS = (
    Path("data/processed/shortlist_spotify_metrics.json"),
    Path("reference/original_shortlist.csv"),
    Path("reference/built_up_areas.csv"),
    Path("reference/reviewed_bands.csv"),
    Path("reference/spotify_band_ids.json"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_label(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-")
    return normalized or "snapshot"


def create_data_snapshot(
    *,
    label: str,
    paths: tuple[Path, ...] | None = None,
    project_root: Path = PROJECT_ROOT,
    snapshot_root: Path = SNAPSHOT_DIR,
) -> Path:
    """Copy canonical inputs into a timestamped directory and write a manifest."""
    paths = DEFAULT_SNAPSHOT_PATHS if paths is None else paths
    if not paths:
        raise ValueError("A snapshot must include at least one path")
    invalid_paths = [
        path
        for path in paths
        if path.is_absolute() or ".." in path.parts
    ]
    if invalid_paths:
        raise ValueError(
            f"Snapshot paths must be repository-relative: {invalid_paths}"
        )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = snapshot_root / f"{timestamp}_{_safe_label(label)}"
    snapshot_path.mkdir(parents=True, exist_ok=False)

    files: list[dict[str, str | int]] = []
    for relative_path in paths:
        source = project_root / relative_path
        if not source.exists():
            continue
        destination = snapshot_path / "files" / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        files.append(
            {
                "path": relative_path.as_posix(),
                "sha256": _sha256(destination),
                "size_bytes": destination.stat().st_size,
            }
        )

    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "project_root": str(project_root),
        "files": files,
    }
    (snapshot_path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return snapshot_path


def load_snapshot_manifest(snapshot_path: Path) -> dict:
    """Load a snapshot manifest and verify every stored file checksum."""
    manifest_path = snapshot_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        stored_file = snapshot_path / "files" / entry["path"]
        if not stored_file.exists():
            raise FileNotFoundError(f"Snapshot file is missing: {stored_file}")
        actual_hash = _sha256(stored_file)
        if actual_hash != entry["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {entry['path']}")
    return manifest


def restore_data_snapshot(
    snapshot_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    create_safety_snapshot: bool = True,
) -> Path | None:
    """Restore a verified snapshot, optionally preserving the current state first."""
    manifest = load_snapshot_manifest(snapshot_path)
    safety_snapshot = None
    if create_safety_snapshot:
        safety_snapshot = create_data_snapshot(label=f"pre-restore-{snapshot_path.name}")

    for entry in manifest["files"]:
        source = snapshot_path / "files" / entry["path"]
        destination = project_root / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return safety_snapshot
