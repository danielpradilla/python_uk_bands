"""Checks for official municipality-based origin-to-FUA mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from python_uk_bands.fua_mapping import (
    build_origin_fua_mapping,
    normalize_admin_name,
)


class FuaMappingTests(unittest.TestCase):
    def test_normalizes_uk_admin_labels(self) -> None:
        self.assertEqual(normalize_admin_name("London Borough of Merton"), "merton")
        self.assertEqual(normalize_admin_name("City of Edinburgh"), "edinburgh")
        self.assertEqual(
            normalize_admin_name("Caerphilly County Borough"), "caerphilly"
        )

    def test_maps_parent_municipality_and_retains_exclusions(self) -> None:
        bands = pd.DataFrame(
            [
                {
                    "origin_cluster": "Locality",
                    "formation_qid": "Q1",
                    "origin_override": "",
                    "returned_spotify_id": "a",
                    "spotify_name": "A",
                    "monthly_listeners": 100,
                },
                {
                    "origin_cluster": "",
                    "formation_qid": "",
                    "origin_override": "",
                    "returned_spotify_id": "b",
                    "spotify_name": "B",
                    "monthly_listeners": 50,
                },
            ]
        )
        population = pd.DataFrame(
            [
                {
                    "fua_code": "UK001F",
                    "official_fua_name": "Example",
                    "study_city_label": "Example",
                }
            ]
        )
        municipalities = pd.DataFrame(
            [
                {
                    "Country": "United Kingdom",
                    "ISO3 code": "GBR",
                    "Municipality name": "Example Borough",
                    "FUA ID": "UK001F",
                    "FUA name": "Example",
                }
            ]
        )
        entities = {
            "entities": {
                "Q1": {"label": "Locality", "located_in": ["Q2"]},
                "Q2": {"label": "Example Borough", "located_in": []},
            }
        }
        legacy = pd.DataFrame(
            [
                {
                    "origin_cluster": "",
                    "fua_code": "",
                    "mapping_tier": "excluded_no_defensible_fua",
                    "mapping_method": "no_resolved_origin",
                    "notes": "",
                }
            ]
        )

        mapping, evidence = build_origin_fua_mapping(
            bands, population, municipalities, entities, legacy
        )

        locality = mapping.loc[mapping["origin_cluster"].eq("Locality")].iloc[0]
        unresolved = mapping.loc[mapping["origin_cluster"].eq("")].iloc[0]
        self.assertEqual(locality["fua_code"], "UK001F")
        self.assertEqual(locality["mapping_tier"], "strict")
        self.assertEqual(
            locality["mapping_method"], "official_oecd_municipality_crosswalk"
        )
        self.assertEqual(unresolved["mapping_tier"], "excluded_no_defensible_fua")
        self.assertEqual(len(evidence), 2)


if __name__ == "__main__":
    unittest.main()
