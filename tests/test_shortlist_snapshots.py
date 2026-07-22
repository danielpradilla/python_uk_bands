"""Tests for selecting frozen 50-band Spotify snapshots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from python_uk_bands.shortlist_snapshots import (
    list_shortlist_snapshot_ids,
    resolve_shortlist_snapshot,
)


class ShortlistSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.processed_dir = Path(self.temporary_directory.name)
        self.publication_path = self.processed_dir / "shortlist_spotify_metrics.json"
        self.publication_path.touch()
        for snapshot_id in (
            "20260717T120000Z",
            "20260717T180000Z",
            "20260718T090000Z",
        ):
            (
                self.processed_dir
                / f"shortlist_spotify_metrics_{snapshot_id}.json"
            ).touch()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lists_timestamped_candidates(self) -> None:
        self.assertEqual(
            list_shortlist_snapshot_ids(self.processed_dir),
            [
                "20260717T120000Z",
                "20260717T180000Z",
                "20260718T090000Z",
            ],
        )

    def test_resolves_publication_latest_exact_and_date(self) -> None:
        publication = resolve_shortlist_snapshot(
            "publication",
            processed_dir=self.processed_dir,
            publication_path=self.publication_path,
        )
        self.assertTrue(publication.is_publication)
        self.assertEqual(
            resolve_shortlist_snapshot(
                "latest",
                processed_dir=self.processed_dir,
                publication_path=self.publication_path,
            ).snapshot_id,
            "20260718T090000Z",
        )
        self.assertEqual(
            resolve_shortlist_snapshot(
                "20260717T120000Z",
                processed_dir=self.processed_dir,
                publication_path=self.publication_path,
            ).snapshot_id,
            "20260717T120000Z",
        )
        self.assertEqual(
            resolve_shortlist_snapshot(
                "2026-07-17",
                processed_dir=self.processed_dir,
                publication_path=self.publication_path,
            ).snapshot_id,
            "20260717T180000Z",
        )
