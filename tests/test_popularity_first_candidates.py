import unittest

from scripts.build_popularity_first_candidates import build_candidates


def _binding(qid, spotify_id, name, formation_qid, formation_label):
    return {
        "item": {"value": f"http://www.wikidata.org/entity/{qid}"},
        "spotifyId": {"value": spotify_id},
        "itemLabel": {"value": name},
        "formation": {
            "value": f"http://www.wikidata.org/entity/{formation_qid}"
        },
        "formationLabel": {"value": formation_label},
        "instanceLabel": {"value": "rock band"},
        "countryLabel": {"value": "United Kingdom"},
    }


class BuildPopularityFirstCandidatesTests(unittest.TestCase):
    def test_deduplicates_identifier_and_aggregates_formation_places(self):
        payload = {
            "results": {
                "bindings": [
                    _binding("Q1", "spotify1", "Band", "Q10", "London"),
                    _binding("Q1", "spotify1", "Band", "Q11", "Manchester"),
                    _binding("Q1", "spotify2", "Band", "Q10", "London"),
                ]
            }
        }

        actual = build_candidates(payload)

        self.assertEqual(len(actual), 2)
        self.assertEqual(actual["spotify_id"].nunique(), 2)
        self.assertEqual(
            actual.loc[
                actual["spotify_id"].eq("spotify1"), "formation_label"
            ].item(),
            "London|Manchester",
        )
        self.assertTrue(actual["capture_key"].is_unique)


if __name__ == "__main__":
    unittest.main()
