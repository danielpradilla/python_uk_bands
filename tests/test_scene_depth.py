"""Tests for the final study's ranking calculation."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.scene_depth import (
    build_primary_scene_depth_rankings,
    validate_scene_depth_dataset,
)


class SceneDepthTests(unittest.TestCase):
    def setUp(self) -> None:
        rows = []
        for city, population, values in (
            ("Alpha", 100, [1, 10, 20, 30, 1_000]),
            ("Beta", 200, [2, 20, 40, 60, 200]),
        ):
            for index, value in enumerate(values, start=1):
                rows.append(
                    {
                        "band": f"{city}-{index}",
                        "city": city,
                        "monthly_listeners": value,
                        "population": population,
                    }
                )
        self.bands = pd.DataFrame(rows)

    def test_balanced_city_design_is_required(self) -> None:
        malformed = self.bands.iloc[:-1].copy()

        with self.assertRaisesRegex(ValueError, "Expected 5 bands per city"):
            validate_scene_depth_dataset(
                malformed,
                expected_cities=2,
                bands_per_city=5,
            )

    def test_primary_result_and_largest_band_test_keep_other_bands(self) -> None:
        rankings = build_primary_scene_depth_rankings(
            self.bands,
            expected_cities=2,
            bands_per_city=5,
        )

        alpha = rankings.set_index("city").loc["Alpha"]
        self.assertEqual(alpha["input_bands"], 5)
        self.assertEqual(alpha["top_excluded_retained_bands"], 4)
        self.assertEqual(alpha["highest_excluded_bands"], "Alpha-5")
        self.assertEqual(alpha["all_ten_value"], 1_061)
        self.assertEqual(alpha["top_excluded_value"], 61)
        self.assertEqual(alpha["raw_total_rank"], 1)
        self.assertEqual(alpha["all_ten_rank"], 1)
        self.assertEqual(alpha["top_excluded_rank"], 1)


if __name__ == "__main__":
    unittest.main()
