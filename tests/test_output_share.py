"""Checks for the share-of-output experiment."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.output_share import build_output_share_metrics


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bands = pd.DataFrame(
        [
            {
                "returned_spotify_id": "a1",
                "spotify_name": "A1",
                "monthly_listeners": 100,
                "followers": 10,
            },
            {
                "returned_spotify_id": "a2",
                "spotify_name": "A2",
                "monthly_listeners": 200,
                "followers": 20,
            },
            {
                "returned_spotify_id": "b1",
                "spotify_name": "B1",
                "monthly_listeners": 300,
                "followers": 30,
            },
            {
                "returned_spotify_id": "x1",
                "spotify_name": "Outside",
                "monthly_listeners": 400,
                "followers": 40,
            },
        ]
    )
    mapping = pd.DataFrame(
        [
            {
                "returned_spotify_id": "a1",
                "mapping_tier": "strict",
                "fua_code": "UK001F",
            },
            {
                "returned_spotify_id": "a2",
                "mapping_tier": "strict",
                "fua_code": "UK001F",
            },
            {
                "returned_spotify_id": "b1",
                "mapping_tier": "reviewed_extended",
                "fua_code": "UK002F",
            },
            {
                "returned_spotify_id": "x1",
                "mapping_tier": "excluded_non_uk",
                "fua_code": "",
            },
        ]
    )
    population = pd.DataFrame(
        [
            {
                "fua_code": "UK001F",
                "official_fua_name": "Area A",
                "study_city_label": "A",
                "population_year": 2021,
                "population": 100,
            },
            {
                "fua_code": "UK002F",
                "official_fua_name": "Area B",
                "study_city_label": "B",
                "population_year": 2021,
                "population": 100,
            },
            {
                "fua_code": "UK003F",
                "official_fua_name": "Area C",
                "study_city_label": "C",
                "population_year": 2021,
                "population": 200,
            },
        ]
    )
    return bands, mapping, population


class OutputShareTests(unittest.TestCase):
    def test_keeps_full_denominators_and_zero_fuas(self) -> None:
        bands, mapping, population = _inputs()

        result, coverage = build_output_share_metrics(
            bands,
            mapping,
            population,
            included_tiers={"strict", "reviewed_extended"},
        )

        area_a = result.loc[result["study_city_label"].eq("A")].iloc[0]
        area_b = result.loc[result["study_city_label"].eq("B")].iloc[0]
        area_c = result.loc[result["study_city_label"].eq("C")].iloc[0]
        self.assertAlmostEqual(area_a["band_share"], 0.5)
        self.assertAlmostEqual(area_a["population_share"], 0.25)
        self.assertAlmostEqual(area_a["band_output_quotient"], 2.0)
        self.assertAlmostEqual(area_a["follower_output_quotient"], 1.2)
        self.assertEqual(area_a["largest_band_by_followers"], "A2")
        self.assertAlmostEqual(area_a["largest_band_follower_share"], 2 / 3)
        self.assertAlmostEqual(area_b["band_output_quotient"], 1.0)
        self.assertEqual(area_c["band_count"], 0)
        self.assertEqual(area_c["band_output_quotient"], 0)
        self.assertEqual(
            area_c["representation_status"], "zero selected bands"
        )
        self.assertAlmostEqual(coverage["mapped_band_share"], 0.75)
        self.assertAlmostEqual(coverage["mapped_follower_share"], 0.60)
        self.assertEqual(coverage["population_fuas"], 3)
        self.assertEqual(coverage["zero_band_fuas"], 1)

    def test_quotient_equals_per_capita_rate_relative_to_average(self) -> None:
        bands, mapping, population = _inputs()
        result, _ = build_output_share_metrics(
            bands,
            mapping,
            population,
            included_tiers={"strict", "reviewed_extended"},
        )

        national_rate = len(bands) / population["population"].sum()
        relative_rate = (
            result["band_count"] / result["population"] / national_rate
        )
        for quotient, expected in zip(
            result["band_output_quotient"], relative_rate
        ):
            self.assertAlmostEqual(quotient, expected)

    def test_rejects_invalid_mapping_tier_selection(self) -> None:
        bands, mapping, population = _inputs()
        with self.assertRaisesRegex(ValueError, "included_tiers"):
            build_output_share_metrics(
                bands,
                mapping,
                population,
                included_tiers={"excluded_non_uk"},
            )


if __name__ == "__main__":
    unittest.main()
