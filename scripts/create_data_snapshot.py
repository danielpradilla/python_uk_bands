#!/usr/bin/env python3
"""Create a checksummed snapshot of canonical project data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.snapshots import create_data_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="Human-readable reason for the snapshot")
    parser.add_argument(
        "--include",
        action="append",
        type=Path,
        help=(
            "Repository-relative file to preserve. Repeat for multiple files. "
            "When omitted, the canonical data inputs are preserved."
        ),
    )
    args = parser.parse_args(argv)
    snapshot_path = create_data_snapshot(
        label=args.label,
        paths=tuple(args.include) if args.include else None,
    )
    print(snapshot_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
