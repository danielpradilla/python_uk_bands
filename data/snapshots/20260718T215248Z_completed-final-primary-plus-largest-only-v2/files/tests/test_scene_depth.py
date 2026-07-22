"""Tests for the isolated ten-band scene-depth experiment."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.scene_depth import (
    build_primary_scene_depth_rankings,
    build_scene_depth_rankings,
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

    def test_trims_highest_and_lowest_before_ranking(self) -> None:
        rankings = build_scene_depth_rankings(
            self.bands,
            expected_cities=2,
            bands_per_city=5,
        )

        alpha = rankings.set_index("city").loc["Alpha"]
        self.assertEqual(alpha["lowest_excluded_bands"], "Alpha-1")
        self.assertEqual(alpha["highest_excluded_bands"], "Alpha-5")
        self.assertEqual(alpha["trimmed_value"], 60)
        self.assertEqual(alpha["trimmed_mean"], 20)
        self.assertEqual(alpha["population_normalized_trimmed_mean"], 0.2)
        self.assertEqual(alpha["scene_depth_ratio"], 0.6)
        self.assertEqual(alpha["retained_bands"], 3)
        self.assertEqual(alpha["trim_fraction_each_tail"], 0.2)
        self.assertEqual(alpha["untrimmed_value"], 1_061)
        self.assertEqual(alpha["top_excluded_value"], 61)
        self.assertEqual(alpha["untrimmed_rank"], 1)
        self.assertEqual(alpha["top_excluded_rank"], 1)
        self.assertEqual(alpha["rank_shift_after_trim"], 0)

    def test_balanced_city_design_is_required(self) -> None:
        malformed = self.bands.iloc[:-1].copy()

        with self.assertRaisesRegex(ValueError, "Expected 5 bands per city"):
            validate_scene_depth_dataset(
                malformed,
                expected_cities=2,
                bands_per_city=5,
            )

    def test_primary_result_and_largest_band_test_keep_other_bands(self):
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
        self.assertEqual(alpha["all_ten_rank"], 1)
        self.assertEqual(alpha["top_excluded_rank"], 1)


if __name__ == "__main__":
    unittest.main()
