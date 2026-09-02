"""Validation for the interactive explorer's canonical data pointer."""

from __future__ import annotations

import csv
import importlib.util
import json
import unittest

from python_uk_bands.config import (
    FUA_POPULATION_PATH,
    FUA_POPULATION_YEAR,
    POPULARITY_FIRST_SNAPSHOT_ID,
    POPULARITY_FIRST_TOP1000_BANDS_PATH,
    PROJECT_ROOT,
)


REQUIRED_COLUMNS = {
    "popularity_rank",
    "returned_spotify_id",
    "spotify_name",
    "band_name",
    "monthly_listeners",
    "followers",
    "stats_extracted_at_utc",
    "origin_cluster",
    "origin_resolution",
}


class InteractiveDashboardTests(unittest.TestCase):
    def test_canonical_source_and_browser_asset_are_in_sync(self) -> None:
        self.assertTrue(POPULARITY_FIRST_TOP1000_BANDS_PATH.is_file())
        with POPULARITY_FIRST_TOP1000_BANDS_PATH.open(
            newline="", encoding="utf-8"
        ) as source:
            reader = csv.DictReader(source)
            self.assertTrue(REQUIRED_COLUMNS.issubset(reader.fieldnames or ()))
            rows = list(reader)

        ids = [row["returned_spotify_id"] for row in rows]
        self.assertEqual(len(rows), 1000)
        self.assertEqual(len(set(ids)), 1000)

        dashboard = json.loads(
            (PROJECT_ROOT / "interactive/public/data/dashboard.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            dashboard["meta"]["snapshotId"], POPULARITY_FIRST_SNAPSHOT_ID
        )
        self.assertEqual(
            dashboard["meta"]["sourceFilename"],
            POPULARITY_FIRST_TOP1000_BANDS_PATH.name,
        )
        self.assertEqual(dashboard["meta"]["recordCount"], len(rows))
        self.assertTrue(
            all("worldRank" not in band for band in dashboard["bands"])
        )

        loader = (PROJECT_ROOT / "interactive/src/data.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('"/data/dashboard.json"', loader)
        self.assertNotIn(".csv", loader)

        self.assertEqual(dashboard["schemaVersion"], 3)
        self.assertEqual(len(dashboard["bands"]), 1000)
        self.assertEqual(len(dashboard["places"]), 220)
        self.assertEqual(len(dashboard["fuas"]), 59)
        self.assertEqual(dashboard["meta"]["resolvedOriginBands"], 749)
        self.assertEqual(dashboard["meta"]["ukLocatedBands"], 743)
        self.assertEqual(dashboard["meta"]["bandsWithGenre"], 928)
        self.assertEqual(dashboard["meta"]["bandsWithWikipedia"], 956)
        self.assertEqual(dashboard["meta"]["strictFuaMappedBands"], 663)
        self.assertEqual(dashboard["meta"]["strictFuaCount"], 59)
        self.assertEqual(dashboard["meta"]["fuaPopulationYear"], 2024)

    def test_population_normalized_fua_package_is_reconciled(self) -> None:
        self.assertTrue(FUA_POPULATION_PATH.is_file())
        dashboard = json.loads(
            (PROJECT_ROOT / "interactive/public/data/dashboard.json").read_text(
                encoding="utf-8"
            )
        )
        fuas = dashboard["fuas"]
        bands = dashboard["bands"]
        fua_by_id = {fua["id"]: fua for fua in fuas}
        self.assertEqual(len(fua_by_id), len(fuas))
        self.assertEqual(
            sum(band["fuaCode"] is not None for band in bands), 663
        )
        for fua in fuas:
            fua_bands = [
                band for band in bands if band["fuaCode"] == fua["id"]
            ]
            self.assertEqual(fua["populationYear"], FUA_POPULATION_YEAR)
            self.assertGreater(fua["population"], 0)
            self.assertEqual(fua["bandCount"], len(fua_bands))
            self.assertEqual(
                fua["monthlyListenersTotal"],
                sum(band["monthlyListeners"] for band in fua_bands),
            )
            self.assertEqual(
                fua["followersTotal"],
                sum(band["followers"] for band in fua_bands),
            )
            self.assertAlmostEqual(
                fua["monthlyListenersPerResident"],
                fua["monthlyListenersTotal"] / fua["population"],
            )
            self.assertAlmostEqual(
                fua["followersPerResident"],
                fua["followersTotal"] / fua["population"],
            )
        self.assertTrue(
            all(
                band["fuaCode"] is None or band["fuaCode"] in fua_by_id
                for band in bands
            )
        )

    def test_packaged_links_locations_and_ranks_are_valid(self) -> None:
        dashboard = json.loads(
            (PROJECT_ROOT / "interactive/public/data/dashboard.json").read_text(
                encoding="utf-8"
            )
        )
        bands = dashboard["bands"]
        self.assertTrue(
            all(
                band["spotifyUrl"]
                == f"https://open.spotify.com/artist/{band['id']}"
                for band in bands
            )
        )
        self.assertEqual(
            sum(band["wikipediaUrl"] is not None for band in bands), 956
        )
        self.assertTrue(
            all(
                "wikipedia.org/wiki/" in band["wikipediaUrl"]
                and "search" not in band["wikipediaUrl"]
                for band in bands
                if band["wikipediaUrl"]
            )
        )
        self.assertTrue(
            all(
                band["latitude"] is None and band["longitude"] is None
                for band in bands
                if band["locationStatus"] == "outside_uk"
            )
        )

        for origin in {band["originCluster"] for band in bands if band["originCluster"]}:
            origin_bands = [
                band for band in bands if band["originCluster"] == origin
            ]
            for rank_field in (
                "placeRankMonthlyListeners",
                "placeRankFollowers",
            ):
                self.assertEqual(
                    sorted(band[rank_field] for band in origin_bands),
                    list(range(1, len(origin_bands) + 1)),
                )

        validation = json.loads(
            (
                PROJECT_ROOT
                / "interactive/public/data/dashboard.validation.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(validation["status"], "passed")
        self.assertEqual(validation["counts"]["catalogBands"], 1000)

    def test_place_ranking_uses_deterministic_tie_breakers(self) -> None:
        builder_path = (
            PROJECT_ROOT / "interactive/scripts/build_dashboard_data.py"
        )
        spec = importlib.util.spec_from_file_location(
            "interactive_dashboard_builder", builder_path
        )
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bands = [
            {
                "name": "Zulu",
                "originCluster": "Test",
                "fuaCode": "UK000",
                "monthlyListeners": 100,
                "followers": 5,
                "catalogRank": 20,
            },
            {
                "name": "Alpha",
                "originCluster": "Test",
                "fuaCode": "UK000",
                "monthlyListeners": 100,
                "followers": 5,
                "catalogRank": 10,
            },
        ]
        module._rank_bands(
            bands,
            "monthlyListeners",
            "originCluster",
            "placeRankMonthlyListeners",
        )
        self.assertEqual(bands[1]["placeRankMonthlyListeners"], 1)
        self.assertEqual(bands[0]["placeRankMonthlyListeners"], 2)


if __name__ == "__main__":
    unittest.main()
