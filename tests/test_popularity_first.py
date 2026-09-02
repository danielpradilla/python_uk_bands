"""Regression checks for catalogue identity and eligibility rules."""

import unittest

import pandas as pd

from python_uk_bands.matching import normalize_name
from python_uk_bands.popularity_first import (
    is_band_entity_eligible,
    select_top_groups,
)


class PopularityFirstTests(unittest.TestCase):
    def test_alias_symbols_and_entity_scope(self) -> None:
        self.assertEqual(
            normalize_name("Mike + The Mechanics"),
            normalize_name("Mike and the Mechanics"),
        )
        self.assertEqual(normalize_name("The Sweet"), normalize_name("Sweet"))
        self.assertTrue(is_band_entity_eligible("musical group"))
        self.assertTrue(is_band_entity_eligible("musical duo|rock band"))
        self.assertFalse(is_band_entity_eligible("symphony orchestra"))
        self.assertFalse(is_band_entity_eligible("musical group|solo musical project"))

    def test_same_wikidata_band_is_selected_once(self) -> None:
        candidates = pd.DataFrame(
            {
                "capture_key": ["Sweet", "The Sweet"],
                "spotify_id": ["popular", "duplicate"],
                "spotify_expected_name": ["Sweet", "The Sweet"],
                "wikidata_qid": ["Q487919", "Q487919"],
                "band_name": ["The Sweet", "The Sweet"],
                "instance_label": ["musical group", "musical group"],
                "formation_qid": ["Q84", "Q84"],
                "formation_label": ["London", "London"],
                "country_qid": ["Q145", "Q145"],
                "country_label": ["United Kingdom", "United Kingdom"],
            }
        )
        metrics = pd.DataFrame(
            {
                "band": ["Sweet", "The Sweet"],
                "spotify_id": ["popular", "duplicate"],
                "spotify_name": ["Sweet", "The Sweet"],
                "followers": [10, 5],
                "monthly_listeners": [100, 50],
                "stats_extracted_at_utc": ["2026-01-01T00:00:00Z"] * 2,
            }
        )
        overrides = pd.DataFrame(
            columns=[
                "spotify_id",
                "identity_decision",
                "origin_override",
                "reason",
                "source_url",
            ]
        )
        selected, audit = select_top_groups(
            candidates, metrics, overrides, top_n=1
        )
        self.assertEqual(selected["returned_spotify_id"].tolist(), ["popular"])
        self.assertEqual(int(audit["entity_duplicate"].sum()), 1)


if __name__ == "__main__":
    unittest.main()
