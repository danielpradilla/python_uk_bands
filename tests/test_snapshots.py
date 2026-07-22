"""Tests for checksummed project snapshots."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from python_uk_bands.snapshots import (
    create_data_snapshot,
    load_snapshot_manifest,
)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project_directory = tempfile.TemporaryDirectory()
        self.snapshot_directory = tempfile.TemporaryDirectory()
        self.project_root = Path(self.project_directory.name)
        self.snapshot_root = Path(self.snapshot_directory.name)
        (self.project_root / "notebooks").mkdir()
        (self.project_root / "notebooks" / "analysis.ipynb").write_text(
            "frozen notebook"
        )

    def tearDown(self) -> None:
        self.project_directory.cleanup()
        self.snapshot_directory.cleanup()

    def test_preserves_explicit_files_with_checksums(self) -> None:
        snapshot = create_data_snapshot(
            label="analysis checkpoint",
            paths=(Path("notebooks/analysis.ipynb"),),
            project_root=self.project_root,
            snapshot_root=self.snapshot_root,
        )

        manifest = load_snapshot_manifest(snapshot)

        self.assertEqual(
            manifest["files"][0]["path"],
            "notebooks/analysis.ipynb",
        )
        self.assertEqual(
            (
                snapshot
                / "files"
                / "notebooks"
                / "analysis.ipynb"
            ).read_text(),
            "frozen notebook",
        )

    def test_rejects_paths_outside_the_repository(self) -> None:
        with self.assertRaisesRegex(ValueError, "repository-relative"):
            create_data_snapshot(
                label="invalid",
                paths=(Path("../outside"),),
                project_root=self.project_root,
                snapshot_root=self.snapshot_root,
            )


if __name__ == "__main__":
    unittest.main()
