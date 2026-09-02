# Final-study inclusion rules and frozen data dictionary

This document applies only to the final study frozen at Spotify snapshot
`20260718T204000Z`. Its two published tables are:

- `data/processed/fua_top10_band_metrics_20260718T204000Z.csv`
- `data/processed/fua_top10_rankings_20260718T204000Z.csv`

## Inclusion decision tree

The catalogue is a frozen editorial selection, not a representative sample.
The rules below make inclusion in this published snapshot auditable and
repeatable; they do not claim that another editor would independently choose
the same 100 bands.

1. **FUA in scope?** Keep only the first ten rows, ordered by
   `uk_population_rank`, in `reference/uk_fua_top20_2024.csv`. Otherwise stop.
2. **In the frozen catalogue?** The act must be one of the ten recorded acts
   for that FUA. Membership was assembled from the original shortlist,
   database candidates and documented editorial additions or replacements.
   Otherwise stop.
3. **Eligible act type?** Include named collaborative groups, including duos
   and electronic acts that operate as groups. Exclude solo artists. Otherwise
   stop.
4. **Reviewed formation origin?** Require a reviewed formation place, an
   evidence URL and accepted `origin_confidence`. Map that place to the FUA
   directly or through the frozen OECD municipality-to-FUA crosswalk. An
   unresolved or unmappable origin stops inclusion.
5. **Resolved Spotify identity?** Require one nonblank Spotify artist ID that
   is unique within the study. An unresolved or duplicate identity stops
   inclusion.
6. **Complete frozen observation?** Require a nonnegative monthly-listener
   value from the single `20260718T204000Z` capture and the FUA's positive 2024
   population. Otherwise stop.
7. **Balanced output?** Accept the row only if the completed table contains
   exactly ten unique bands for each of ten FUAs. The final result must contain
   exactly 100 rows.

### Deterministic calculation and tie rules

- Raw selected reach is the sum of all ten `monthly_listeners` values.
- The primary index is that sum divided by the FUA's 2024 `population`.
- The sensitivity index removes the row with the greatest
  `monthly_listeners`, then divides the remaining nine-band sum by population.
- If bands tie for the greatest value, sorting is by `monthly_listeners` and
  then `band` in ascending order; the last row is removed. This means the
  alphabetically later band is removed in an exact tie.
- City ranks use descending values and `method="min"`: tied cities receive the
  same lowest numerical rank. City name is the final display-order tie-break.

## Band-level table

One row represents one selected band assigned to one FUA. Blank values are
allowed only where stated.

| Field | Type | Definition | Domain or unit |
|---|---|---|---|
| `band_name` | text | Canonical catalogue label for the act. | Unique; nonblank. |
| `study_city_label` | text | Reader-facing label for the assigned FUA. | One of the ten selected FUAs. |
| `claimed_formation_place` | text | Reviewed place where the group formed. | Place name; nonblank. |
| `origin_review_status` | text | Editorial review state for the origin assignment. | `reviewed` in this snapshot. |
| `origin_alignment` | text | How the accepted evidence entered the catalogue. | `existing_catalogue` or `exact`. |
| `origin_evidence_url` | text | Row-level source supporting the formation place. | URL; nonblank. |
| `origin_confidence` | text | Accepted confidence in the origin assignment. | `high` or `medium` in this snapshot. |
| `spotify_id` | text | Spotify artist identifier used for the capture. | Unique; nonblank. |
| `spotify_name_prior` | text | Artist name from the upstream identity record before capture. | May be blank. |
| `spotify_expected_name` | text | Name expected when validating the Spotify identity. | Nonblank. |
| `musicbrainz_id` | text | MusicBrainz artist identifier, when available. | UUID; may be blank. |
| `wikidata_id` | text | Wikidata entity identifier, when available. | QID; may be blank. |
| `catalogue_source` | text | Catalogue branch from which the row was assembled. | Frozen provenance label. |
| `selection_source` | text | More specific editorial or database selection provenance. | Frozen provenance label. |
| `notes` | text | Identity, origin or editorial qualification. | May be blank. |
| `uk_population_rank` | integer | Rank in the frozen UK FUA population universe. | 1–10. |
| `fua_code` | text | OECD FUA identifier. | Nonblank; one per FUA. |
| `official_fua_name` | text | OECD name for the FUA. | Nonblank. |
| `population_year` | integer | Year of the population denominator. | `2024`. |
| `population` | integer | OECD FUA population used as denominator. | Residents; positive. |
| `territorial_definition` | text | Geographic definition applied to the denominator. | `OECD/EU Functional Urban Area`. |
| `source_dataset_url` | text | OECD source page for the population observation. | URL; nonblank. |
| `catalogue_review_ready` | boolean | Whether review status and Spotify identity passed the catalogue gate. | `True` for every included row. |
| `band` | text | Analysis-compatible alias of `band_name`. | Exact duplicate. |
| `city` | text | Analysis-compatible alias of `study_city_label`. | Exact duplicate. |
| `spotify_name` | text | Artist name returned by Spotify at capture. | Nonblank. |
| `monthly_listeners` | integer | Spotify listeners during the platform's rolling 28-day window. | Global artist-level count; nonnegative. |
| `followers` | integer | Spotify followers at capture. | Global artist-level count; nonnegative. |
| `world_rank` | integer | Spotify world-rank value returned at capture. | `0` denotes no positive rank returned. |
| `stats_extracted_at_utc` | timestamp | UTC time shared by the frozen capture. | ISO 8601; one value for all rows. |
| `source` | text | Metric source operation. | `Spotify web-player queryArtistOverview`. |
| `source_access` | text | Access-path qualification. | Undocumented read-only web-client endpoint. |

## FUA ranking table

One row represents one of the ten selected FUAs.

| Field | Type | Definition | Domain or unit |
|---|---|---|---|
| `city` | text | Reader-facing FUA label. | Unique; nonblank. |
| `population` | integer | 2024 OECD FUA population. | Residents; positive. |
| `input_bands` | integer | Bands included in the primary calculation. | `10`. |
| `top_excluded_retained_bands` | integer | Bands retained after the dominant-band exclusion. | `9`. |
| `highest_excluded_bands` | text | Band removed in the sensitivity calculation. | One selected band. |
| `all_ten_value` | integer | Sum of all ten selected bands' monthly listeners. | Artist-listener counts summed; not unique people. |
| `all_ten_ratio` | number | `all_ten_value / population`. | Comparative index. |
| `top_excluded_value` | integer | Nine-band sum after removing the largest selected band. | Artist-listener counts summed. |
| `top_excluded_ratio` | number | `top_excluded_value / population`. | Comparative sensitivity index. |
| `top_band_concentration` | number | Largest selected band's share of `all_ten_value`. | Proportion from 0 to 1. |
| `metric` | text | Artist-level audience field used in the calculations. | `monthly_listeners`. |
| `raw_total_rank` | integer | Descending rank of `all_ten_value`. | 1 is largest. |
| `all_ten_rank` | integer | Descending rank of `all_ten_ratio`. | Primary rank; 1 is largest. |
| `top_excluded_rank` | integer | Descending rank of `top_excluded_ratio`. | Sensitivity rank; 1 is largest. |

## Interpretation boundary

The numerator is global Spotify attention in July 2026 and the denominator is
local FUA population in 2024, the latest complete observed OECD year available
for UK FUAs. This documented two-year mismatch is preferable to presenting a
projected 2026 population as observed. Summed artist audiences can count the same person
more than once. These fields therefore define a comparative selected-band
index, not local listening, causal cultural output, historical importance or a
complete census of an area's music.
