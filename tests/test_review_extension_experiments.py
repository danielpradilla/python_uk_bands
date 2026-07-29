"""Tests for study-review extension experiments 19–23."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from python_uk_bands.review_extension_experiments import (
    _genre_family,
    _infrastructure_categories,
    _normalized_artist_name,
    build_band_networks,
    build_beyond_spotify,
    build_genre_history,
    build_longitudinal_reach,
    build_scene_infrastructure,
    extract_wikidata_band_features,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIKIDATA_PATH = (
    PROJECT_ROOT
    / "data/raw/wikidata/review_extension_entities_20260725.json"
)
MUSICBRAINZ_PATH = (
    PROJECT_ROOT
    / "data/raw/musicbrainz/review_extension_artists_20260725.json"
)
OSM_PATH = (
    PROJECT_ROOT
    / "data/raw/openstreetmap/music_infrastructure_20260725.json"
)
PAGEVIEWS_PATH = (
    PROJECT_ROOT
    / "data/raw/wikimedia/top1000_enwiki_pageviews_20250701_20260630_20260725.json"
)


class ReviewExtensionExperimentTests(unittest.TestCase):
    def test_extract_wikidata_features_preserves_provenance_fields(self) -> None:
        payload = {
            "entities": {
                "Q1": {
                    "labels": {"en": {"value": "Example Band"}},
                    "claims": {
                        "P136": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {"entity-type": "item", "id": "Q2"}
                                    }
                                }
                            }
                        ],
                        "P264": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {"entity-type": "item", "id": "Q3"}
                                    }
                                }
                            }
                        ],
                        "P527": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {"entity-type": "item", "id": "Q4"}
                                    }
                                }
                            }
                        ],
                        "P571": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {"time": "+1983-01-01T00:00:00Z"}
                                    }
                                }
                            }
                        ],
                    },
                    "sitelinks": {"enwiki": {"title": "Example Band"}},
                }
            },
            "referenced_labels": {
                "Q2": "heavy metal",
                "Q3": "Example Records",
                "Q4": "Example Musician",
            },
        }

        row = extract_wikidata_band_features(payload).iloc[0]

        self.assertEqual(row["inception_year"], 1983)
        self.assertEqual(row["genre_families"], "Metal")
        self.assertEqual(row["record_label_names"], "Example Records")
        self.assertEqual(row["member_names"], "Example Musician")
        self.assertEqual(row["enwiki_title"], "Example Band")

    def test_genre_family_uses_specific_metal_rule_before_rock(self) -> None:
        self.assertEqual(_genre_family("heavy metal rock"), "Metal")
        self.assertEqual(_genre_family("trip hop"), "Electronic and dance")
        self.assertEqual(_genre_family("soul music"), "Pop, soul and R&B")

    def test_artist_name_normalization_handles_display_variants(self) -> None:
        self.assertEqual(
            _normalized_artist_name("The Sweet"),
            _normalized_artist_name("Sweet"),
        )
        self.assertEqual(
            _normalized_artist_name("Katrina & The Waves"),
            _normalized_artist_name("Katrina and the Waves"),
        )
        self.assertNotEqual(
            _normalized_artist_name("Radiohead"),
            _normalized_artist_name("On a Friday"),
        )

    def test_infrastructure_classification_allows_multiple_source_tags(self) -> None:
        categories = _infrastructure_categories(
            {"amenity": "arts_centre", "studio": "audio"}
        )
        self.assertEqual(categories, ["Arts centre", "Audio studio"])

    def test_frozen_genre_capture_has_high_coverage(self) -> None:
        audit, city_genre, decade_genre, coverage = build_genre_history(
            PROJECT_ROOT,
            wikidata_path=WIKIDATA_PATH,
        )

        self.assertEqual(len(audit), 1000)
        self.assertGreaterEqual(coverage["genre_coverage"], 0.90)
        self.assertFalse(city_genre.empty)
        self.assertFalse(decade_genre.empty)

    def test_frozen_infrastructure_capture_is_complete_for_twenty_cities(self) -> None:
        places, city, coverage = build_scene_infrastructure(
            PROJECT_ROOT,
            osm_path=OSM_PATH,
        )

        self.assertEqual(len(city), 20)
        self.assertTrue((city["radius_metres"] == 15_000).all())
        self.assertFalse(places.empty)
        self.assertEqual(coverage["cities"], 20)

    def test_network_edges_are_distinct_band_pairs(self) -> None:
        nodes, _, edges, city, _, coverage = build_band_networks(
            PROJECT_ROOT,
            wikidata_path=WIKIDATA_PATH,
            musicbrainz_path=MUSICBRAINZ_PATH,
        )

        self.assertEqual(coverage["selected_bands"], 1000)
        self.assertEqual(len(nodes), coverage["mapped_bands"])
        self.assertGreaterEqual(len(city), 50)
        self.assertTrue((edges["band_a"] != edges["band_b"]).all())
        self.assertTrue(
            (
                (edges["shared_member_count"] > 0)
                | (edges["shared_label_count"] > 0)
            ).all()
        )
        self.assertEqual(coverage["band_edges"], len(edges))

    def test_longitudinal_comparison_keeps_the_fixed_catalogue(self) -> None:
        changes, city, summary = build_longitudinal_reach(PROJECT_ROOT)

        self.assertEqual(len(changes), 50)
        self.assertEqual(len(city), 10)
        self.assertEqual(summary["bands_with_follower_growth"], 50)
        self.assertTrue((city["bands"] == 5).all())

    def test_pageview_triangulation_has_one_row_per_selected_band(self) -> None:
        audit, city, summary = build_beyond_spotify(
            PROJECT_ROOT,
            pageviews_path=PAGEVIEWS_PATH,
        )

        self.assertEqual(len(audit), 1000)
        self.assertGreaterEqual(summary["pageview_coverage"], 0.90)
        self.assertGreater(summary["rank_correlation_followers_vs_pageviews"], 0.6)
        self.assertAlmostEqual(city["follower_share"].sum(), 1.0)
        self.assertAlmostEqual(city["pageview_share"].sum(), 1.0)

    def test_frozen_capture_files_parse_as_json(self) -> None:
        for path in (WIKIDATA_PATH, MUSICBRAINZ_PATH, OSM_PATH, PAGEVIEWS_PATH):
            self.assertIsInstance(json.loads(path.read_text()), dict)


if __name__ == "__main__":
    unittest.main()
