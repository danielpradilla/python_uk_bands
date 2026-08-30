"""Regression tests for the frozen final FUA study."""

from __future__ import annotations

import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from python_uk_bands.config import PROJECT_ROOT
from python_uk_bands.fua import validate_top_fua_universe
from python_uk_bands.scene_depth import build_primary_scene_depth_rankings


SNAPSHOT_ID = "20260718T204000Z"


class FrozenFuaStudyTests(unittest.TestCase):
    def test_top10_uses_the_first_ten_official_fua_rows(self) -> None:
        universe = pd.read_csv(
            PROJECT_ROOT / "reference" / "uk_fua_top20_2021.csv"
        ).head(10)
        validate_top_fua_universe(universe, expected_rows=10, year=2021)
        bands = pd.read_csv(
            PROJECT_ROOT
            / "data"
            / "processed"
            / f"fua_top10_band_metrics_{SNAPSHOT_ID}.csv"
        )
        observed = (
            bands[
                [
                    "uk_population_rank",
                    "fua_code",
                    "city",
                    "population",
                ]
            ]
            .drop_duplicates()
            .sort_values("uk_population_rank")
            .reset_index(drop=True)
        )
        expected = (
            universe[
                [
                    "uk_population_rank",
                    "fua_code",
                    "study_city_label",
                    "population",
                ]
            ]
            .rename(columns={"study_city_label": "city"})
            .reset_index(drop=True)
        )
        assert_frame_equal(observed, expected, check_dtype=False)
        self.assertEqual(len(bands), 100)
        self.assertTrue(bands.groupby("city").size().eq(10).all())

    def test_saved_final_rankings_recompute(self) -> None:
        bands = pd.read_csv(
            PROJECT_ROOT
            / "data"
            / "processed"
            / f"fua_top10_band_metrics_{SNAPSHOT_ID}.csv"
        )
        saved = pd.read_csv(
            PROJECT_ROOT
            / "data"
            / "processed"
            / f"fua_top10_rankings_{SNAPSHOT_ID}.csv"
        )
        recalculated = build_primary_scene_depth_rankings(
            bands,
            metric="monthly_listeners",
            expected_cities=10,
            bands_per_city=10,
        )
        assert_frame_equal(
            recalculated.sort_values("city").reset_index(drop=True),
            saved.sort_values("city").reset_index(drop=True),
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
