"""Tests for selecting frozen scene-depth snapshots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from python_uk_bands.scene_depth_snapshots import (
    list_scene_depth_snapshot_ids,
    resolve_scene_depth_snapshot,
)


class SceneDepthSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.processed_dir = Path(self.temporary_directory.name)
        for snapshot_id in ("20260717T120000Z", "20260717T180000Z", "20260718T090000Z"):
            (
                self.processed_dir
                / f"scene_depth_band_metrics_{snapshot_id}.csv"
            ).touch()
            (
                self.processed_dir
                / f"scene_depth_rankings_{snapshot_id}.csv"
            ).touch()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lists_only_complete_snapshots(self) -> None:
        incomplete = self.processed_dir / "scene_depth_band_metrics_20260719T090000Z.csv"
        incomplete.touch()

        self.assertEqual(
            list_scene_depth_snapshot_ids(self.processed_dir),
            [
                "20260717T120000Z",
                "20260717T180000Z",
                "20260718T090000Z",
            ],
        )

    def test_resolves_latest_exact_and_date(self) -> None:
        self.assertEqual(
            resolve_scene_depth_snapshot(
                "latest",
                processed_dir=self.processed_dir,
            ).snapshot_id,
            "20260718T090000Z",
        )
        self.assertEqual(
            resolve_scene_depth_snapshot(
                "20260717T120000Z",
                processed_dir=self.processed_dir,
            ).snapshot_id,
            "20260717T120000Z",
        )
        self.assertEqual(
            resolve_scene_depth_snapshot(
                "2026-07-17",
                processed_dir=self.processed_dir,
            ).snapshot_id,
            "20260717T180000Z",
        )
