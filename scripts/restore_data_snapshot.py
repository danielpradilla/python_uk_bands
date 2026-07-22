#!/usr/bin/env python3
"""Verify and optionally restore a project data snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.snapshots import load_snapshot_manifest, restore_data_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Snapshot directory containing manifest.json")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Restore the files. Without this flag the command only verifies the snapshot.",
    )
    args = parser.parse_args(argv)
    snapshot_path = args.snapshot.resolve()
    manifest = load_snapshot_manifest(snapshot_path)
    print(f"Verified {len(manifest['files'])} files in {snapshot_path}")
    if not args.apply:
        print("Dry run only. Pass --apply to restore this snapshot.")
        return 0

    safety_snapshot = restore_data_snapshot(snapshot_path)
    print(f"Restored {snapshot_path}")
    print(f"Pre-restore safety snapshot: {safety_snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
