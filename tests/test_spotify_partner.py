"""Tests for the isolated Spotify web-player reader."""

from __future__ import annotations

import json
import unittest

from python_uk_bands.spotify_partner import (
    fetch_artist_overview,
    parse_embed_access_token,
    search_artist_candidates,
)
from python_uk_bands.matching import normalize_name


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class SpotifyPartnerTests(unittest.TestCase):
    def test_name_normalization_removes_diacritics(self) -> None:
        self.assertEqual(normalize_name("Maxïmo Park"), "maximopark")

    def test_parses_embed_session(self) -> None:
        payload = {
            "props": {
                "pageProps": {
                    "state": {
                        "settings": {
                            "session": {
                                "accessToken": "token",
                                "accessTokenExpirationTimestampMs": 123,
                            }
                        }
                    }
                }
            }
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps(payload)}</script>"
        )

        self.assertEqual(parse_embed_access_token(html), ("token", 123))

    def test_compacts_search_and_overview_payloads(self) -> None:
        search_payload = {
            "data": {
                "searchV2": {
                    "artists": {
                        "items": [
                            {
                                "data": {
                                    "uri": "spotify:artist:abc",
                                    "profile": {"name": "Example"},
                                }
                            }
                        ]
                    }
                }
            }
        }
        overview_payload = {
            "data": {
                "artist": {
                    "id": "abc",
                    "profile": {"name": "Example"},
                    "stats": {
                        "monthlyListeners": 1234,
                        "followers": 500,
                        "worldRank": 99,
                    },
                }
            }
        }
        responses = iter(
            [FakeResponse(search_payload), FakeResponse(overview_payload)]
        )

        def fake_get(*args, **kwargs):
            return next(responses)

        candidates, _ = search_artist_candidates(
            "Example",
            access_token="token",
            request_get=fake_get,
        )
        overview, _ = fetch_artist_overview(
            "abc",
            access_token="token",
            request_get=fake_get,
        )

        self.assertEqual(candidates[0]["spotify_id"], "abc")
        self.assertEqual(overview["monthly_listeners"], 1234)
        self.assertEqual(overview["world_rank"], 99)


if __name__ == "__main__":
    unittest.main()
