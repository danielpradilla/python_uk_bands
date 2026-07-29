"""Tests for the study-review follow-up experiment helpers."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from python_uk_bands.review_experiments import (
    attach_formation_years,
    rank_city_scores,
    summarize_formation_year_coverage,
    summarize_rank_stability,
    summarize_scene_depth,
)


class ReviewExperimentTests(unittest.TestCase):
    def test_rank_scores_preserves_ties_and_sorts_deterministically(self) -> None:
        scores = pd.DataFrame(
            {
                "study_city_label": ["Beta", "Alpha", "Gamma"],
                "score": [10, 10, 5],
            }
        )

        ranked = rank_city_scores(
            scores,
            specification="example",
            family="test",
            score_column="score",
        )

        self.assertEqual(
            ranked["study_city_label"].tolist(),
            ["Alpha", "Beta", "Gamma"],
        )
        self.assertEqual(ranked["rank"].tolist(), [1, 1, 3])

    def test_rank_stability_uses_only_included_specifications(self) -> None:
        ranked = pd.DataFrame(
            {
                "specification": ["a", "a", "b", "b", "c"],
                "study_city_label": ["Alpha", "Beta", "Alpha", "Beta", "Alpha"],
                "rank": [1, 2, 3, 1, 2],
            }
        )

        summary = summarize_rank_stability(ranked, top_n=1).set_index(
            "study_city_label"
        )

        self.assertEqual(int(summary.loc["Alpha", "specifications"]), 3)
        self.assertAlmostEqual(summary.loc["Alpha", "median_rank"], 2)
        self.assertAlmostEqual(summary.loc["Alpha", "top_finish_share"], 1 / 3)
        self.assertEqual(int(summary.loc["Beta", "specifications"]), 2)
        self.assertAlmostEqual(summary.loc["Beta", "top_finish_share"], 0.5)

    def test_scene_depth_matches_inverse_herfindahl(self) -> None:
        bands = pd.DataFrame(
            {
                "study_city_label": ["Alpha", "Alpha", "Alpha", "Beta"],
                "returned_spotify_id": ["a", "b", "c", "d"],
                "followers": [50, 30, 20, 100],
            }
        )

        depth = summarize_scene_depth(
            bands,
            threshold=25,
        ).set_index("study_city_label")

        self.assertAlmostEqual(
            depth.loc["Alpha", "effective_band_count"],
            1 / (0.5**2 + 0.3**2 + 0.2**2),
        )
        self.assertAlmostEqual(depth.loc["Alpha", "largest_band_share"], 0.5)
        self.assertEqual(int(depth.loc["Alpha", "bands_above_threshold"]), 2)
        self.assertAlmostEqual(depth.loc["Beta", "effective_band_count"], 1)

    def test_attach_years_prefers_musicbrainz_id_then_name(self) -> None:
        bands = pd.DataFrame(
            {
                "band_name": ["Alpha", "Beta", "Gamma"],
                "musicbrainz_id": ["id-alpha", "", "id-missing"],
                "study_city_label": ["One", "Two", "Three"],
            }
        )
        lookup = pd.DataFrame(
            {
                "musicbrainz_id": ["id-alpha", ""],
                "band_name_key": ["not alpha", "beta"],
                "formed_year": [1981, 1992],
                "formation_year_source": ["id source", "name source"],
            }
        )

        attached = attach_formation_years(bands, lookup)

        self.assertEqual(int(attached.loc[0, "formed_year"]), 1981)
        self.assertEqual(int(attached.loc[1, "formed_year"]), 1992)
        self.assertTrue(pd.isna(attached.loc[2, "formed_year"]))

    def test_formation_coverage_keeps_zero_coverage_cities(self) -> None:
        bands = pd.DataFrame(
            {
                "study_city_label": ["Alpha", "Alpha", "Beta"],
                "formed_year": pd.Series([1980, pd.NA, pd.NA], dtype="Int64"),
            }
        )

        coverage = summarize_formation_year_coverage(bands).set_index(
            "study_city_label"
        )

        self.assertAlmostEqual(coverage.loc["Alpha", "formation_year_coverage"], 0.5)
        self.assertEqual(coverage.loc["Beta", "formation_year_coverage"], 0)
        self.assertTrue(np.isfinite(coverage["formation_year_coverage"]).all())


if __name__ == "__main__":
    unittest.main()
