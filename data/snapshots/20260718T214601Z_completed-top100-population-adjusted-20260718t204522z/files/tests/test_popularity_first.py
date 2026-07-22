import unittest

import pandas as pd

from python_uk_bands.popularity_first import (
    attach_fua_population,
    build_origin_concentration,
    build_population_adjusted_metrics,
    resolve_origin,
    select_top_groups,
)


class PopularityFirstTests(unittest.TestCase):
    def test_resolve_origin_handles_cluster_override_and_generic(self):
        self.assertEqual(
            resolve_origin("Abingdon-on-Thames"),
            ("Oxford", "editorial_city_cluster"),
        )
        self.assertEqual(
            resolve_origin("England", "London"),
            ("London", "reviewed_override"),
        )
        self.assertEqual(
            resolve_origin("England"),
            ("", "unresolved_generic_or_missing"),
        )

    def test_selection_audits_alias_deduplicates_and_excludes_orchestra(self):
        candidates = pd.DataFrame(
            [
                {
                    "capture_key": "A [id1]",
                    "spotify_id": "id1",
                    "spotify_expected_name": "A",
                    "formation_label": "London",
                    "instance_label": "rock band",
                },
                {
                    "capture_key": "Alias [old]",
                    "spotify_id": "old",
                    "spotify_expected_name": "Alias",
                    "formation_label": "Manchester",
                    "instance_label": "musical group",
                },
                {
                    "capture_key": "Alias [id2]",
                    "spotify_id": "id2",
                    "spotify_expected_name": "Alias",
                    "formation_label": "Manchester",
                    "instance_label": "musical group",
                },
                {
                    "capture_key": "C [id3]",
                    "spotify_id": "id3",
                    "spotify_expected_name": "C",
                    "formation_label": "Leeds",
                    "instance_label": "orchestra",
                },
            ]
        )
        metrics = pd.DataFrame(
            [
                {
                    "band": "A [id1]",
                    "spotify_id": "id1",
                    "spotify_name": "A",
                    "monthly_listeners": 30,
                },
                {
                    "band": "Alias [old]",
                    "spotify_id": "id2",
                    "spotify_name": "Alias",
                    "monthly_listeners": 20,
                },
                {
                    "band": "Alias [id2]",
                    "spotify_id": "id2",
                    "spotify_name": "Alias",
                    "monthly_listeners": 20,
                },
                {
                    "band": "C [id3]",
                    "spotify_id": "id3",
                    "spotify_name": "C Orchestra",
                    "monthly_listeners": 40,
                },
            ]
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
            candidates, metrics, overrides, top_n=2
        )

        self.assertEqual(selected["spotify_name"].tolist(), ["A", "Alias"])
        self.assertEqual(selected["returned_spotify_id"].nunique(), 2)
        self.assertEqual(audit["redirect_duplicate"].sum(), 1)
        self.assertEqual(
            audit["eligibility_status"].eq("excluded_orchestra").sum(), 1
        )
        concentration = build_origin_concentration(selected)
        self.assertEqual(concentration["band_count"].sum(), 2)

    def test_population_adjustment_has_coverage_and_per_capita_metrics(self):
        selected = pd.DataFrame(
            [
                {
                    "origin_cluster": "A",
                    "returned_spotify_id": "a1",
                    "monthly_listeners": 100,
                },
                {
                    "origin_cluster": "A",
                    "returned_spotify_id": "a2",
                    "monthly_listeners": 50,
                },
                {
                    "origin_cluster": "B",
                    "returned_spotify_id": "b1",
                    "monthly_listeners": 200,
                },
                {
                    "origin_cluster": "Outside",
                    "returned_spotify_id": "o1",
                    "monthly_listeners": 50,
                },
            ]
        )
        mapping = pd.DataFrame(
            [
                {
                    "origin_cluster": "A",
                    "fua_code": "UK001F",
                    "mapping_tier": "strict",
                    "mapping_method": "exact",
                    "notes": "",
                },
                {
                    "origin_cluster": "B",
                    "fua_code": "UK002F",
                    "mapping_tier": "reviewed_extended",
                    "mapping_method": "reviewed",
                    "notes": "",
                },
                {
                    "origin_cluster": "Outside",
                    "fua_code": "",
                    "mapping_tier": "excluded_non_uk",
                    "mapping_method": "outside",
                    "notes": "",
                },
            ]
        )
        population = pd.DataFrame(
            [
                {
                    "fua_code": "UK001F",
                    "official_fua_name": "Area A",
                    "study_city_label": "A",
                    "population_year": 2021,
                    "population": 1000,
                },
                {
                    "fua_code": "UK002F",
                    "official_fua_name": "Area B",
                    "study_city_label": "B",
                    "population_year": 2021,
                    "population": 100,
                },
            ]
        )

        attached = attach_fua_population(selected, mapping, population)
        strict, strict_coverage = build_population_adjusted_metrics(
            attached,
            included_tiers={"strict"},
        )
        extended, extended_coverage = build_population_adjusted_metrics(
            attached,
            included_tiers={"strict", "reviewed_extended"},
        )

        self.assertEqual(strict["study_city_label"].tolist(), ["A"])
        self.assertEqual(strict.iloc[0]["band_count"], 2)
        self.assertEqual(
            strict.iloc[0]["top100_bands_per_million_residents"], 2000
        )
        self.assertEqual(
            strict.iloc[0]["top100_monthly_listeners_per_resident"], 0.15
        )
        self.assertEqual(strict_coverage["mapped_bands"], 2)
        self.assertEqual(extended_coverage["mapped_bands"], 3)
        self.assertEqual(extended.iloc[0]["study_city_label"], "B")

    def test_population_mapping_requires_exact_origin_coverage(self):
        selected = pd.DataFrame(
            [
                {
                    "origin_cluster": "A",
                    "returned_spotify_id": "a1",
                    "monthly_listeners": 100,
                }
            ]
        )
        mapping = pd.DataFrame(
            columns=[
                "origin_cluster",
                "fua_code",
                "mapping_tier",
                "mapping_method",
                "notes",
            ]
        )
        population = pd.DataFrame(
            columns=[
                "fua_code",
                "official_fua_name",
                "study_city_label",
                "population_year",
                "population",
            ]
        )

        with self.assertRaisesRegex(ValueError, "cover.*exactly"):
            attach_fua_population(selected, mapping, population)


if __name__ == "__main__":
    unittest.main()
