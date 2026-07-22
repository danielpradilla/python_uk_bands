"""Regression tests for the frozen top-10 and top-20 FUA studies."""

from __future__ import annotations

import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from python_uk_bands.config import PROJECT_ROOT
from python_uk_bands.scene_depth import build_primary_scene_depth_rankings


SNAPSHOT_ID = "20260718T204000Z"


class FrozenFuaStudyTests(unittest.TestCase):
    def test_top10_uses_the_first_ten_official_fua_rows(self) -> None:
        universe = pd.read_csv(
            PROJECT_ROOT / "reference" / "uk_fua_top20_2021.csv"
        ).head(10)
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

    def test_saved_rankings_recompute_for_both_study_sizes(self) -> None:
        for city_count in (10, 20):
            with self.subTest(city_count=city_count):
                bands = pd.read_csv(
                    PROJECT_ROOT
                    / "data"
                    / "processed"
                    / (
                        f"fua_top{city_count}_band_metrics_"
                        f"{SNAPSHOT_ID}.csv"
                    )
                )
                saved = pd.read_csv(
                    PROJECT_ROOT
                    / "data"
                    / "processed"
                    / f"fua_top{city_count}_rankings_{SNAPSHOT_ID}.csv"
                )
                recalculated = build_primary_scene_depth_rankings(
                    bands,
                    metric="monthly_listeners",
                    expected_cities=city_count,
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
