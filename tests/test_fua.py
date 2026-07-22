"""Tests for the population-selected Functional Urban Area universe."""

from __future__ import annotations

import unittest

from python_uk_bands.fua import (
    build_uk_fua_universe,
    validate_top_fua_universe,
)


RAW_FIXTURE = """REF_AREA,Reference area,TERRITORIAL_LEVEL,TIME_PERIOD,OBS_VALUE,OBS_STATUS
UK002F,West Midlands urban area,FUA,2021,300,A
UK001F,London,FUA,2021,1000,A
UK008F,Manchester,FUA,2021,500,A
UK008C,Manchester,CITY,2021,200,A
FR001F,Paris,FUA,2021,800,A
UK003F,Leeds,FUA,2020,250,A
"""


class FunctionalUrbanAreaTests(unittest.TestCase):
    def test_builds_population_rank_before_selecting_top_n(self) -> None:
        universe = build_uk_fua_universe(
            RAW_FIXTURE,
            year=2021,
            top_n=2,
            captured_at_utc="2026-07-18T00:00:00+00:00",
        )

        self.assertEqual(
            universe["study_city_label"].tolist(),
            ["London", "Manchester"],
        )
        self.assertEqual(universe["uk_population_rank"].tolist(), [1, 2])
        self.assertEqual(universe["population"].tolist(), [1000, 500])

    def test_validates_a_frozen_top_n_universe(self) -> None:
        universe = build_uk_fua_universe(
            RAW_FIXTURE,
            year=2021,
            top_n=3,
            captured_at_utc="2026-07-18T00:00:00+00:00",
        )

        validate_top_fua_universe(
            universe,
            expected_rows=3,
            year=2021,
        )


if __name__ == "__main__":
    unittest.main()
