"""Tests for the isolated scene-depth chart inputs."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.config import PROJECT_ROOT
from python_uk_bands.scene_depth_visuals import SCENE_DEPTH_CHART_DIR


class SceneDepthVisualTests(unittest.TestCase):
    def test_experiment_chart_directory_is_isolated(self) -> None:
        self.assertEqual(SCENE_DEPTH_CHART_DIR.name, "scene_depth")
        self.assertNotEqual(SCENE_DEPTH_CHART_DIR.name, "charts")

    def test_saved_rank_fields_support_all_three_variants(self) -> None:
        rankings = pd.read_csv(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "scene_depth_rankings_20260717T203002Z.csv"
        )
        self.assertTrue(
            {
                "untrimmed_rank",
                "top_excluded_rank",
                "rank",
            }.issubset(rankings.columns)
        )
