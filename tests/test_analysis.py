"""Tests for city ranking and shortlist data preparation."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.analysis import (
    build_city_rankings,
    build_threshold_sensitivity,
    validate_band_dataset,
)


class CityRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bands = pd.DataFrame(
            [
                {"band": "A1", "city": "Alpha", "followers": 300, "monthly_listeners": 900, "population": 100},
                {"band": "A2", "city": "Alpha", "followers": 200, "monthly_listeners": 600, "population": 100},
                {"band": "A3", "city": "Alpha", "followers": 50, "monthly_listeners": 300, "population": 100},
                {"band": "B1", "city": "Beta", "followers": 600, "monthly_listeners": 1_200, "population": 400},
                {"band": "B2", "city": "Beta", "followers": 400, "monthly_listeners": 800, "population": 400},
                {"band": "B3", "city": "Beta", "followers": 100, "monthly_listeners": 400, "population": 400},
            ]
        )

    def test_top_n_ratio_controls_rank(self) -> None:
        rankings = build_city_rankings(self.bands, metric="monthly_listeners", top_n=2)

        self.assertEqual(rankings.iloc[0]["city"], "Alpha")
        self.assertEqual(rankings.iloc[0]["top_band"], "A1")
        self.assertEqual(rankings.iloc[0]["top_n_ratio"], 15)
        self.assertEqual(rankings.iloc[1]["top_n_ratio"], 5)

    def test_threshold_sensitivity_recalculates_eligible_bands(self) -> None:
        sensitivity = build_threshold_sensitivity(
            self.bands,
            thresholds=[0, 250],
            metric="monthly_listeners",
            top_n=2,
        )

        alpha = sensitivity.loc[sensitivity["city"] == "Alpha"].set_index("follower_threshold")
        self.assertEqual(alpha.loc[0, "eligible_bands"], 3)
        self.assertEqual(alpha.loc[250, "eligible_bands"], 1)

    def test_inconsistent_population_is_rejected(self) -> None:
        malformed = self.bands.copy()
        malformed.loc[1, "population"] = 101

        with self.assertRaisesRegex(ValueError, "inconsistent population"):
            validate_band_dataset(malformed)

    def test_negative_metric_is_rejected(self) -> None:
        malformed = self.bands.copy()
        malformed.loc[0, "followers"] = -1

        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            validate_band_dataset(malformed)


if __name__ == "__main__":
    unittest.main()
