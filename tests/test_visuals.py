"""Tests for stable categorical encodings in reader-facing charts."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.visuals import (
    HOUSE,
    TOP_CITY_COLORS,
    _colors_for_highlighted_cities,
)


class CityHighlightTests(unittest.TestCase):
    def test_top_three_palette_is_unique_repeatable_and_focused(self) -> None:
        self.assertEqual(len(TOP_CITY_COLORS), 3)
        self.assertEqual(len(set(TOP_CITY_COLORS)), 3)

        colors = _colors_for_highlighted_cities(
            pd.Series(["London", "Liverpool", "Manchester", "London"]),
            ["London", "Sheffield", "Manchester"],
        )
        self.assertEqual(colors[0], colors[3])
        self.assertEqual(colors[1], HOUSE["gray_blue"])
        self.assertNotEqual(colors[0], colors[2])

    def test_exactly_three_highlighted_cities_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "Exactly three unique"):
            _colors_for_highlighted_cities(
                pd.Series(["Liverpool"]),
                ["Liverpool", "Manchester"],
            )


if __name__ == "__main__":
    unittest.main()
