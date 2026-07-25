"""Checks for the top-city follower map helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.follower_maps import (
    FOLLOWERS_PER_POINT_SQUARED,
    QUOTIENT_POINTS_SQUARED_PER_UNIT,
    prepare_top_city_map_data,
)


class FollowerMapTests(unittest.TestCase):
    def _inputs(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        shares = pd.DataFrame(
            [
                {
                    "fua_code": "A",
                    "study_city_label": "Alpha",
                    "band_count": 2,
                    "followers_total": 300,
                    "follower_share": 0.30,
                    "follower_output_quotient": 1.5,
                    "largest_band_by_followers": "Band A",
                    "largest_band_followers": 200,
                    "largest_band_follower_share": 2 / 3,
                },
                {
                    "fua_code": "B",
                    "study_city_label": "Beta",
                    "band_count": 1,
                    "followers_total": 600,
                    "follower_share": 0.60,
                    "follower_output_quotient": 3.0,
                    "largest_band_by_followers": "Band B",
                    "largest_band_followers": 600,
                    "largest_band_follower_share": 1.0,
                },
                {
                    "fua_code": "C",
                    "study_city_label": "Gamma",
                    "band_count": 0,
                    "followers_total": 0,
                    "follower_share": 0.0,
                    "follower_output_quotient": 0.0,
                    "largest_band_by_followers": "",
                    "largest_band_followers": 0,
                    "largest_band_follower_share": 0.0,
                },
            ]
        )
        coordinates = pd.DataFrame(
            [
                {
                    "fua_code": "A",
                    "study_city_label": "Alpha",
                    "latitude": 51.0,
                    "longitude": -1.0,
                    "coordinate_source_url": "https://example.com/A",
                },
                {
                    "fua_code": "B",
                    "study_city_label": "Beta",
                    "latitude": 52.0,
                    "longitude": -2.0,
                    "coordinate_source_url": "https://example.com/B",
                },
            ]
        )
        manifest = pd.DataFrame(
            [
                {
                    "fua_code": "A",
                    "study_city_label": "Alpha",
                    "band_name": "Band A",
                    "commons_page_url": "https://example.com/photo-a",
                    "local_path": "photo-a.jpg",
                    "artist": "Artist A",
                    "license_short_name": "CC BY 4.0",
                    "license_url": "https://example.com/license",
                    "attribution_text": "Artist A · CC BY 4.0",
                },
                {
                    "fua_code": "B",
                    "study_city_label": "Beta",
                    "band_name": "Band B",
                    "commons_page_url": "https://example.com/photo-b",
                    "local_path": "photo-b.jpg",
                    "artist": "Artist B",
                    "license_short_name": "CC BY 4.0",
                    "license_url": "https://example.com/license",
                    "attribution_text": "Artist B · CC BY 4.0",
                },
            ]
        )
        return shares, coordinates, manifest

    def test_ranks_positive_cities_and_keeps_exact_area_scale(self) -> None:
        shares, coordinates, manifest = self._inputs()

        result = prepare_top_city_map_data(
            shares,
            coordinates,
            manifest,
            top_city_count=2,
        )

        self.assertEqual(result["study_city_label"].tolist(), ["Beta", "Alpha"])
        self.assertEqual(result["rank_by_followers"].tolist(), [1, 2])
        self.assertAlmostEqual(result.iloc[0]["share_of_mapped_followers"], 2 / 3)
        area_ratio = (
            result.iloc[0]["circle_area_points2"]
            / result.iloc[1]["circle_area_points2"]
        )
        self.assertAlmostEqual(area_ratio, 2.0)
        self.assertAlmostEqual(
            result.iloc[0]["circle_area_points2"],
            600 / FOLLOWERS_PER_POINT_SQUARED,
        )
        quotient_area_ratio = (
            result.iloc[0]["quotient_circle_area_points2"]
            / result.iloc[1]["quotient_circle_area_points2"]
        )
        self.assertAlmostEqual(quotient_area_ratio, 2.0)
        self.assertAlmostEqual(
            result.iloc[0]["quotient_circle_area_points2"],
            3.0 * QUOTIENT_POINTS_SQUARED_PER_UNIT,
        )

    def test_rejects_a_photo_for_the_wrong_band(self) -> None:
        shares, coordinates, manifest = self._inputs()
        manifest.loc[manifest["fua_code"].eq("B"), "band_name"] = "Wrong band"

        with self.assertRaisesRegex(ValueError, "Photo band must match"):
            prepare_top_city_map_data(
                shares,
                coordinates,
                manifest,
                top_city_count=2,
            )

    def test_rejects_missing_assets(self) -> None:
        shares, coordinates, manifest = self._inputs()
        coordinates = coordinates.loc[coordinates["fua_code"].ne("B")]

        with self.assertRaisesRegex(ValueError, "requires coordinates"):
            prepare_top_city_map_data(
                shares,
                coordinates,
                manifest,
                top_city_count=2,
            )


if __name__ == "__main__":
    unittest.main()
