"""Integration checks for the saved exploratory shortlist."""

from __future__ import annotations

import unittest

from python_uk_bands.dataset import (
    build_match_review_queue,
    build_quality_summary,
    load_shortlist_dataset,
    validate_shortlist_shape,
)


class ShortlistDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bands = load_shortlist_dataset()

    def test_saved_shortlist_has_expected_shape(self) -> None:
        validate_shortlist_shape(self.bands)
        self.assertEqual(len(self.bands), 50)
        self.assertEqual(self.bands["city"].nunique(), 10)

    def test_quality_summary_has_no_missing_core_values(self) -> None:
        summary = build_quality_summary(self.bands).set_index("check")["result"]
        self.assertEqual(summary["Missing Spotify IDs"], 0)
        self.assertEqual(summary["Missing populations"], 0)
        self.assertEqual(summary["Missing popularity metrics"], 0)

    def test_review_queue_keeps_known_mismatch_visible(self) -> None:
        queue = build_match_review_queue(self.bands)
        self.assertIn("Dog Is Dead", queue["band_name"].tolist())


if __name__ == "__main__":
    unittest.main()
