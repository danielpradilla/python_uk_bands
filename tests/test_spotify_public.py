"""Tests for read-only public Spotify scene-depth helpers."""

from __future__ import annotations

import unittest

from python_uk_bands.spotify_public import (
    parse_public_spotify_artist_page,
    spotify_artist_id_from_url,
    spotify_artist_url_from_musicbrainz_payload,
)


class SpotifyPublicTests(unittest.TestCase):
    def test_extracts_artist_id_from_canonical_url(self) -> None:
        self.assertEqual(
            spotify_artist_id_from_url(
                "https://open.spotify.com/artist/2tRsMl4eGxwoNabM08Dm4I?si=test"
            ),
            "2tRsMl4eGxwoNabM08Dm4I",
        )
        self.assertIsNone(
            spotify_artist_id_from_url("https://open.spotify.com/album/example")
        )

    def test_selects_spotify_relationship_from_musicbrainz(self) -> None:
        payload = {
            "relations": [
                {"url": {"resource": "https://example.com/artist"}},
                {
                    "url": {
                        "resource": (
                            "https://open.spotify.com/artist/"
                            "2tRsMl4eGxwoNabM08Dm4I"
                        )
                    }
                },
            ]
        }
        self.assertEqual(
            spotify_artist_url_from_musicbrainz_payload(payload),
            "https://open.spotify.com/artist/2tRsMl4eGxwoNabM08Dm4I",
        )

    def test_parses_exact_public_monthly_listener_count(self) -> None:
        page = """
        <meta property="og:title" content="Judas Priest"/>
        <div data-testid="monthly-listeners-label">
          4,135,514 monthly listeners
        </div>
        <p class="metric">5,702,113</p>
        <p class="label">Followers</p>
        """
        self.assertEqual(
            parse_public_spotify_artist_page(page),
            {
                "spotify_name": "Judas Priest",
                "monthly_listeners": 4_135_514,
                "followers": 5_702_113,
            },
        )

    def test_parses_zero_listeners_from_metadata_fallback(self) -> None:
        page = """
        <meta property="og:title" content="Every 90&#x27;s Dog is Dead"/>
        <meta property="og:description"
              content="Artist · 0 monthly listeners."/>
        <p class="metric">174</p>
        <p class="label">Followers</p>
        """
        self.assertEqual(
            parse_public_spotify_artist_page(page),
            {
                "spotify_name": "Every 90's Dog is Dead",
                "monthly_listeners": 0,
                "followers": 174,
            },
        )


if __name__ == "__main__":
    unittest.main()
