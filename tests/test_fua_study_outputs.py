"""Regression tests for the frozen final FUA study."""

from __future__ import annotations

import json
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from python_uk_bands.config import (
    FINAL_STUDY_BAND_METRICS_PATH,
    FINAL_STUDY_RANKINGS_PATH,
    FUA_POPULATION_PATH,
    FUA_POPULATION_YEAR,
    PROJECT_ROOT,
)
from python_uk_bands.fua import validate_top_fua_universe
from python_uk_bands.scene_depth import (
    build_primary_scene_depth_rankings,
    validate_spotify_capture_window,
)


class FrozenFuaStudyTests(unittest.TestCase):
    def test_spotify_capture_window_is_under_ten_minutes(self) -> None:
        bands = pd.read_csv(FINAL_STUDY_BAND_METRICS_PATH)
        timestamps = validate_spotify_capture_window(bands)
        self.assertLessEqual(
            timestamps.max() - timestamps.min(),
            pd.Timedelta(minutes=10),
        )

    def test_osm_capture_population_context_uses_frozen_2024_fuas(self) -> None:
        population = pd.read_csv(FUA_POPULATION_PATH)[
            [
                "fua_code",
                "population_year",
                "population",
                "captured_at_utc",
            ]
        ]
        payload = json.loads(
            (
                PROJECT_ROOT
                / "data/raw/openstreetmap/music_infrastructure_20260725.json"
            ).read_text()
        )
        self.assertEqual(payload["population_year"], FUA_POPULATION_YEAR)
        self.assertEqual(
            payload["population_path"],
            str(FUA_POPULATION_PATH.relative_to(PROJECT_ROOT)),
        )
        self.assertEqual(
            payload["population_captured_at_utc"],
            population["captured_at_utc"].unique().item(),
        )
        observed = pd.DataFrame(payload["records"])[
            ["fua_code", "population_year", "population"]
        ].sort_values("fua_code").reset_index(drop=True)
        expected = population.loc[
            population["fua_code"].isin(observed["fua_code"])
        ][["fua_code", "population_year", "population"]].sort_values(
            "fua_code"
        ).reset_index(drop=True)
        assert_frame_equal(observed, expected, check_dtype=False)

    def test_top10_uses_the_first_ten_official_fua_rows(self) -> None:
        universe = pd.read_csv(
            PROJECT_ROOT / "reference" / "uk_fua_top20_2024.csv"
        ).head(10)
        validate_top_fua_universe(universe, expected_rows=10, year=2024)
        bands = pd.read_csv(FINAL_STUDY_BAND_METRICS_PATH)
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
        bands = pd.read_csv(FINAL_STUDY_BAND_METRICS_PATH)
        saved = pd.read_csv(FINAL_STUDY_RANKINGS_PATH)
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
