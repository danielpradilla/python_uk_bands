#!/usr/bin/env python3
"""Build the frozen top-100 UK-group origin analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from python_uk_bands.io import write_csv, write_json
from python_uk_bands.popularity_first import (
    build_origin_concentration,
    select_top_groups,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--capture-report", required=True, type=Path)
    parser.add_argument("--overrides", required=True, type=Path)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--top-n", type=int, default=100)
    return parser


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidates = pd.read_csv(args.candidates, keep_default_na=False)
    metrics = pd.read_csv(args.metrics, keep_default_na=False)
    overrides = pd.read_csv(args.overrides, keep_default_na=False)
    capture_report = json.loads(args.capture_report.read_text(encoding="utf-8"))

    selected, audit = select_top_groups(
        candidates,
        metrics,
        overrides,
        top_n=args.top_n,
    )
    concentration = build_origin_concentration(selected)

    prefix = f"popularity_first_top{args.top_n}_{args.snapshot_id}"
    selected_path = (
        PROJECT_ROOT / "data" / "processed" / f"{prefix}_bands.csv"
    )
    concentration_path = (
        PROJECT_ROOT / "data" / "processed" / f"{prefix}_origins.csv"
    )
    audit_path = (
        PROJECT_ROOT / "data" / "interim" / f"{prefix}_identity_audit.csv"
    )
    report_path = (
        PROJECT_ROOT / "data" / "processed" / f"{prefix}_report.json"
    )
    write_csv(selected, selected_path)
    write_csv(concentration, concentration_path)
    write_csv(audit, audit_path)

    resolved = selected["origin_cluster"].ne("")
    resolved_counts = selected.loc[resolved, "origin_cluster"].value_counts()
    resolved_reach = selected.loc[resolved].groupby("origin_cluster")[
        "monthly_listeners"
    ].sum()
    report = {
        "snapshot_id": args.snapshot_id,
        "selection_frame": (
            "Spotify IDs on UK musical-group entities returned by the "
            "archived Wikidata query"
        ),
        "candidate_ids": len(candidates),
        "metrics_rows": len(metrics),
        "metric_failures": len(capture_report["metric_failures"]),
        "identity_name_reviews": len(capture_report["name_review"]),
        "identity_accepted_rows": int(audit["identity_accepted"].sum()),
        "orchestra_rows_excluded": int(
            audit["eligibility_status"].eq("excluded_orchestra").sum()
        ),
        "redirect_duplicate_rows": int(audit["redirect_duplicate"].sum()),
        "selected_bands": len(selected),
        "origin_resolved_bands": int(resolved.sum()),
        "origin_coverage": float(resolved.mean()),
        "origin_hhi_band_count_resolved": float(
            ((resolved_counts / resolved_counts.sum()) ** 2).sum()
        ),
        "origin_hhi_reach_resolved": float(
            ((resolved_reach / resolved_reach.sum()) ** 2).sum()
        ),
        "top_origin_by_band_count": concentration.iloc[0][
            "origin_cluster"
        ],
        "top_origin_band_count": int(concentration.iloc[0]["band_count"]),
        "radiohead_selected": bool(
            selected["spotify_name"].eq("Radiohead").any()
        ),
        "radiohead_origin": selected.loc[
            selected["spotify_name"].eq("Radiohead"), "origin_cluster"
        ].squeeze(),
        "inputs": {
            "candidates": _relative(args.candidates),
            "metrics": _relative(args.metrics),
            "capture_report": _relative(args.capture_report),
            "overrides": _relative(args.overrides),
        },
        "outputs": {
            "bands": _relative(selected_path),
            "origins": _relative(concentration_path),
            "identity_audit": _relative(audit_path),
        },
        "canonical_files_modified": False,
    }
    write_json(report, report_path)
    print(selected_path.relative_to(PROJECT_ROOT))
    print(concentration_path.relative_to(PROJECT_ROOT))
    print(audit_path.relative_to(PROJECT_ROOT))
    print(report_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
