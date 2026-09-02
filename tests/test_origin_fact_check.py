"""Small checks for origin comparison edge cases."""

import unittest

from scripts.audit_top1000_origins import _places_match, _plain_wikitext


class OriginFactCheckTests(unittest.TestCase):
    def test_place_aliases_and_wikitext_cleanup(self) -> None:
        self.assertTrue(_places_match("Skye", "Isle of Skye, Scotland"))
        self.assertTrue(_places_match("London", "Croydon, London, England"))
        self.assertEqual(_plain_wikitext("[[Oxford]], {{flag|England}}"), "Oxford, England")
        self.assertEqual(_plain_wikitext("{{plainlist|\n* [[York]], England"), "York, England")


if __name__ == "__main__":
    unittest.main()
