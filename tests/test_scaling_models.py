"""Checks for the population-scaling model helpers."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from python_uk_bands.scaling_models import (
    fit_loglog_follower_scaling,
    fit_negative_binomial_band_scaling,
)


def _frame(
    populations: list[int],
    band_counts: list[int],
    follower_totals: list[float],
) -> pd.DataFrame:
    population_array = np.asarray(populations, dtype=float)
    follower_array = np.asarray(follower_totals, dtype=float)
    selected_followers = max(float(follower_array.sum()), 1.0)
    rows = []
    for index, (population, count, followers) in enumerate(
        zip(populations, band_counts, follower_totals)
    ):
        rows.append(
            {
                "fua_code": f"UK{index:03d}F",
                "study_city_label": f"City {index}",
                "population_year": 2021,
                "population": population,
                "population_share": population / population_array.sum(),
                "band_count": count,
                "followers_total": followers,
                "follower_share": followers / selected_followers,
                "largest_band_by_followers": "Example" if count else "",
                "largest_band_follower_share": 1 / count if count else 0,
            }
        )
    return pd.DataFrame(rows)


class ScalingModelTests(unittest.TestCase):
    def test_negative_binomial_matches_reference_fit(self) -> None:
        populations = [100, 150, 220, 330, 500, 750, 1100, 1700, 2600, 4000, 6200, 9500]
        counts = [0, 2, 0, 1, 8, 0, 2, 12, 1, 25, 7, 50]
        followers = [float(max(count, 1) * 100) for count in counts]
        data = _frame(populations, counts, followers)

        results, summary = fit_negative_binomial_band_scaling(data)

        # Cross-checked against MASS::glm.nb 7.3-60.2.
        self.assertAlmostEqual(summary["population_exponent_beta"], 0.8887135, places=5)
        self.assertAlmostEqual(summary["dispersion_alpha"], 0.8904198, places=5)
        self.assertAlmostEqual(summary["aic"], 69.07561, places=4)
        self.assertEqual(len(results), len(populations))
        self.assertEqual(int(results["band_count"].eq(0).sum()), 3)
        self.assertTrue(summary["converged"])

    def test_loglog_recovers_known_scaling_exponent_and_excludes_zero(self) -> None:
        populations = [100, 150, 220, 330, 500, 750, 1100, 1700, 2600, 4000]
        counts = [0, 1, 1, 2, 2, 3, 4, 5, 6, 7]
        followers = [0.0] + [5.0 * population**1.5 for population in populations[1:]]
        data = _frame(populations, counts, followers)

        results, summary = fit_loglog_follower_scaling(data)

        self.assertAlmostEqual(summary["population_exponent_beta"], 1.5, places=10)
        self.assertAlmostEqual(summary["huber_population_exponent_beta"], 1.5, places=10)
        self.assertAlmostEqual(summary["r_squared_log_scale"], 1.0, places=10)
        self.assertEqual(summary["n_fuas_included"], 9)
        excluded = results.loc[results["study_city_label"].eq("City 0")].iloc[0]
        self.assertFalse(bool(excluded["model_included"]))
        self.assertTrue(np.isnan(excluded["log_residual"]))

    def test_rejects_duplicate_fua_rows(self) -> None:
        data = _frame(
            [100, 200, 300, 400, 500, 600, 700, 800],
            [0, 1, 1, 2, 2, 3, 4, 5],
            [0, 10, 20, 30, 40, 50, 60, 70],
        )
        data.loc[1, "fua_code"] = data.loc[0, "fua_code"]

        with self.assertRaisesRegex(ValueError, "one row per FUA"):
            fit_negative_binomial_band_scaling(data)


if __name__ == "__main__":
    unittest.main()
