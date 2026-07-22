#!/usr/bin/env python3
"""Build the top-20 FUA experiment with the final notebook's structure."""

from __future__ import annotations

import sys

from build_fua_study_notebook import main as build_fua_study_notebook


def main(argv: list[str] | None = None):
    forwarded = [
        "--city-count",
        "20",
        "--experiment",
        *(argv or []),
    ]
    return build_fua_study_notebook(forwarded)


if __name__ == "__main__":
    main(sys.argv[1:])
