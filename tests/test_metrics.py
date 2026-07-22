"""Unit checks for third-party metrics normalization and promotion gates."""

from __future__ import annotations

import unittest

from python_uk_bands.metrics import extract_spotscraper_artist, validate_metric_candidate


class MetricsTests(unittest.TestCase):
    def test_extracts_nested_response_without_treating_zero_as_missing(self) -> None:
        normalized = extract_spotscraper_artist(
            {
                "data": {
                    "name": "Example Band",
                    "statistics": {
                        "monthlyListeners": 1234,
                        "followers": 0,
                        "worldRank": 9000,
                    },
                }
            }
        )
        self.assertEqual(normalized["monthly_listeners"], 1234)
        self.assertEqual(normalized["followers"], 0)
        self.assertEqual(normalized["world_rank"], 9000)

    def test_partial_candidate_is_never_promotion_ready(self) -> None:
        identifiers = [
            {"band": "A", "spotify_id": "1"},
            {"band": "B", "spotify_id": "2"},
        ]
        candidate = [
            {
                "band": "A",
                "spotify_id": "1",
                "followers": 10,
                "monthly_listeners": 20,
                "stats_extracted_at": "2026-07-11",
                "match_quality": "exact",
            }
        ]
        report = validate_metric_candidate(candidate, identifiers, [])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["missing_bands"], ["B"])


if __name__ == "__main__":
    unittest.main()
