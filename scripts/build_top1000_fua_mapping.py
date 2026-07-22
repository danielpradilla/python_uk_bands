#!/usr/bin/env python3
"""Build the reviewed top-1,000 origin-to-FUA map and evidence table."""

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

from python_uk_bands.fua_mapping import build_origin_fua_mapping  # noqa: E402
from python_uk_bands.io import write_csv, write_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bands", required=True, type=Path)
    parser.add_argument("--population", required=True, type=Path)
    parser.add_argument("--municipalities", required=True, type=Path)
    parser.add_argument("--entities", required=True, type=Path)
    parser.add_argument("--legacy-mapping", required=True, type=Path)
    parser.add_argument("--mapping-output", required=True, type=Path)
    parser.add_argument("--evidence-output", required=True, type=Path)
    return parser


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bands = pd.read_csv(args.bands, keep_default_na=False)
    population = pd.read_csv(args.population, keep_default_na=False)
    municipalities = pd.read_csv(args.municipalities, keep_default_na=False)
    legacy = pd.read_csv(args.legacy_mapping, keep_default_na=False)
    entities = json.loads(args.entities.read_text(encoding="utf-8"))

    mapping, evidence = build_origin_fua_mapping(
        bands,
        population,
        municipalities,
        entities,
        legacy,
    )
    mapping_path = args.mapping_output.resolve()
    evidence_path = args.evidence_output.resolve()
    report_path = evidence_path.with_name(f"{evidence_path.stem}_report.json")
    write_csv(mapping, mapping_path)
    write_csv(evidence, evidence_path)

    included = mapping["mapping_tier"].isin({"strict", "reviewed_extended"})
    included_origins = set(mapping.loc[included, "origin_cluster"])
    mapped_bands = bands["origin_cluster"].isin(included_origins)
    report = {
        "selected_bands": len(bands),
        "origin_clusters": len(mapping),
        "resolved_origin_bands": int(bands["origin_cluster"].ne("").sum()),
        "mapped_bands": int(mapped_bands.sum()),
        "mapped_band_share": float(mapped_bands.mean()),
        "mapped_monthly_listener_share": float(
            bands.loc[mapped_bands, "monthly_listeners"].sum()
            / bands["monthly_listeners"].sum()
        ),
        "mapped_follower_share": float(
            bands.loc[mapped_bands, "followers"].sum()
            / bands["followers"].sum()
        ),
        "mapping_tier_counts": {
            str(key): int(value)
            for key, value in mapping["mapping_tier"].value_counts().items()
        },
        "inputs": {
            "bands": _relative(args.bands),
            "population": _relative(args.population),
            "municipalities": _relative(args.municipalities),
            "entities": _relative(args.entities),
            "legacy_mapping": _relative(args.legacy_mapping),
        },
        "outputs": {
            "mapping": _relative(mapping_path),
            "evidence": _relative(evidence_path),
        },
    }
    write_json(report, report_path)
    print(mapping_path.relative_to(PROJECT_ROOT))
    print(evidence_path.relative_to(PROJECT_ROOT))
    print(report_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
