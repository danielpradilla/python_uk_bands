"""Tests for the top-20 city-first catalogue."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.top20 import validate_top20_catalog


class Top20CatalogueTests(unittest.TestCase):
    def test_accepts_balanced_twenty_by_ten_design(self) -> None:
        rows = []
        for city_number in range(20):
            for band_number in range(10):
                rows.append(
                    {
                        "band_name": f"Band-{city_number}-{band_number}",
                        "study_city_label": f"City-{city_number}",
                        "population": 1000 + city_number,
                        "population_year": 2021,
                        "fua_code": f"F{city_number}",
                        "uk_population_rank": city_number + 1,
                        "spotify_id": f"S{city_number}-{band_number}",
                    }
                )

        validate_top20_catalog(pd.DataFrame(rows))

    def test_rejects_unbalanced_design(self) -> None:
        rows = [
            {
                "band_name": f"Band-{index}",
                "study_city_label": "Only",
                "population": 100,
                "population_year": 2021,
                "fua_code": "F1",
                "uk_population_rank": 1,
                "spotify_id": f"S{index}",
            }
            for index in range(10)
        ]

        with self.assertRaisesRegex(ValueError, "Expected 200 bands"):
            validate_top20_catalog(pd.DataFrame(rows))


if __name__ == "__main__":
    unittest.main()
