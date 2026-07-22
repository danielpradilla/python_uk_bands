"""Checks for resilient MusicBrainz area enrichment."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from python_uk_bands.musicbrainz import _resolve_city_from_area


class MusicBrainzTests(unittest.TestCase):
    def test_unavailable_area_enrichment_leaves_city_unresolved(self) -> None:
        area = {"id": "unavailable", "name": "West Yorkshire", "type": "County"}
        with patch(
            "python_uk_bands.musicbrainz._fetch_area_details",
            side_effect=requests.HTTPError("503 unavailable"),
        ):
            with self.assertWarns(RuntimeWarning):
                city = _resolve_city_from_area(area, "United Kingdom")
        self.assertIsNone(city)


if __name__ == "__main__":
    unittest.main()
