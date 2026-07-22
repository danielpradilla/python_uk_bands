# Analysis history

This file is the index of preserved analysis states. Timestamped notebooks read
explicit frozen inputs and do not refresh network data when executed. Each
completion snapshot contains a manifest with SHA-256 checksums for the notebook,
inputs, outputs, raw responses, and exported charts.

## 22 July 2026 — music-output-share versus population experiment

- Executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top200_output_share_vs_population_20260718T204522Z.ipynb`
- Scope: compare every represented FUA's share of the frozen selected top-200
  catalogue with its share of the complete 83-FUA population universe. The
  chart uses band share as position and follower share as bubble area; the
  notebook also reports follower and monthly-listener output quotients.
- Denominator policy: all 83 FUAs remain in the population denominator and all
  200 selected bands remain in the output denominators. Unmapped bands are not
  redistributed or removed when calculating shares.
- Mapping coverage: the primary strict-plus-reviewed-extended view maps 169 of
  200 bands, 93.9% of followers and 91.1% of monthly listeners to 35 FUAs.
- Exported outputs:
  `artifacts/experiments/top200_output_share_vs_population/20260718T204522Z/`.
- Publication status: separate exploratory analysis; it does not modify the
  final notebook or replace the canonical popularity-first experiment.

## 22 July 2026 — top-1,000 FUA mapping and follower-share experiment

- Expanded the frozen popularity-first selection to 1,000 eligible identities
  without refreshing Spotify data. The selection cutoff is 26,180 monthly
  listeners in the 18 July 2026 capture.
- Captured the official OECD UK municipality-to-FUA crosswalk: 267
  municipalities across 84 FUAs. The frozen population denominator contains 83
  of those FUAs; Carlisle (`UK575F`) is absent and is explicitly excluded from
  normalized results rather than silently dropped.
- Captured Wikidata formation-place labels and `located in the administrative
  territorial entity` ancestry for 235 seed entities and 575 entities in the
  complete ancestry snapshot.
- Generated the complete 218-origin decision file:
  `reference/popularity_first_top1000_origin_fua_mapping_20260718.csv`.
  Official municipality membership controls whenever available; only two
  reviewed-extended legacy assignments remain.
- Mapping coverage: 660 of 1,000 bands across 61 FUAs. This represents 66.0% of
  band count, 92.4% of followers and 90.5% of monthly listeners. Unresolved,
  regional, non-UK and non-FUA origins remain unallocated.
- Corrected the earlier Totnes sensitivity assignment: the official crosswalk
  places South Hams in Plymouth FUA, not Torbay.
- Executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top1000_output_share_vs_population_20260718T204522Z.ipynb`.
- Primary visual: follower share versus population share, with selected-band
  count encoded by bubble area. The band-share chart remains as a companion so
  its one-band row is explicit rather than mistaken for a plotting error.
- Publication status: separate exploratory analysis; the final notebook and
  canonical top-200 popularity-first notebook are unchanged.

## Preserved baseline before the top-20/top-100 work

- Snapshot:
  `data/snapshots/20260718T202259Z_baseline-before-top20-primary-and-top100-secondary/`
- Purpose: rollback point for the existing final notebook, earlier ten-band
  experiment, catalogues, geography, and identifiers.
- Existing final notebook checksum at that point:
  `bcfea250826692bcd935a62ae89d8d99121119f1358d4d2321285c2ca18fd859`.

## 18 July 2026 — city-first primary-design experiment

- Executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top20_city_first_20260718T204000Z.ipynb`
- Scope: the twenty largest UK OECD/EU Functional Urban Areas by 2021
  population, ten reviewed bands per area, all-ten result followed by a
  symmetric trim of one highest and one lowest band.
- Frozen reach capture:
  `data/processed/top20_city_spotify_metrics_20260718T204000Z.csv`
- Saved rankings:
  `data/processed/top20_city_rankings_20260718T204000Z.csv`
- Completion snapshot:
  `data/snapshots/20260718T204356Z_completed-top20-city-first-20260718t204000z/`
- Publication status: experiment; it does not modify or replace the final
  notebook.

## 18 July 2026 — popularity-first secondary experiment

- Executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top100_popularity_first_20260718T204522Z.ipynb`
- Scope: select the 100 largest monthly-listener counts from an archived
  Wikidata-derived UK musical-group candidate universe after identity,
  redirect, and group-type review; then map origins and measure concentration.
- Archived candidate query:
  `data/raw/wikidata/uk_group_candidates_with_spotify_20260718T201100Z.json`
- Frozen reach capture:
  `data/processed/uk_group_spotify_metrics_20260718T204522Z.csv`
- Saved selection and origin summary:
  `data/processed/popularity_first_top100_20260718T204522Z_bands.csv` and
  `data/processed/popularity_first_top100_20260718T204522Z_origins.csv`
- Completion snapshot:
  `data/snapshots/20260718T205319Z_completed-top100-popularity-first-20260718t204522z/`
- Publication status: separate exploratory analysis; it does not modify or
  replace the city-first or final notebooks.

## 18 July 2026 — methodology-first published narrative

- Revised notebook:
  `notebooks/final/uk_bands_punching_above_weight.ipynb`
- Change: reorganized the reader journey around the study question, fixed
  panel, band-selection rules, data definitions, formulas, assumptions,
  results, sensitivity tests and limitations.
- Project history moved to the end: the earlier five-band comparison is
  Appendix A and the useful dead ends are Appendix B.
- Data and calculations remain fixed to scene-depth snapshot
  `20260717T225650Z`; the notebook was rebuilt and executed top to bottom.
- Pre-edit rollback point:
  `data/snapshots/20260718T205602Z_before-methodology-first-published-notebook/`
- Completed-state snapshot:
  `data/snapshots/20260718T210021Z_methodology-first-published-notebook/`

## 18 July 2026 — population-adjusted popularity-first companion

- Executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top100_popularity_first_population_adjusted_20260718T204522Z.ipynb`
- Scope: preserve the raw top-100 origin concentration, then normalize both
  selected-band count and captured global listener reach by 2021 OECD/EU
  Functional Urban Area population.
- Strict mapping coverage: 87 of 100 bands and 89.0% of captured reach. An
  extended reviewed-mapping sensitivity covers 94 bands and 94.7% of reach.
- Stability diagnostic: retain the full ranking, then separately show FUAs
  represented by at least two selected bands so one-superstar cases remain
  visible without defining the broader comparison.
- Saved outputs:
  `data/processed/popularity_first_top100_20260718T204522Z_population_strict.csv`,
  `data/processed/popularity_first_top100_20260718T204522Z_population_extended.csv`
  and
  `data/interim/popularity_first_top100_20260718T204522Z_fua_mapping_audit.csv`.
- Publication status: separate exploratory sensitivity analysis; the original
  popularity-first notebook and final published notebook were not modified.
- Completion snapshot:
  `data/snapshots/20260718T214601Z_completed-top100-population-adjusted-20260718t204522z/`.

## 18 July 2026 — final hierarchy: primary result plus one scene-depth test

- Revised notebook:
  `notebooks/final/uk_bands_punching_above_weight.ipynb`
- Change: made the all-ten, population-normalized ranking the unambiguous
  primary result. The only alternative ranking in the final notebook now
  removes each city's largest band as a scene-depth sensitivity.
- The largest-band concentration chart remains as a diagnostic. The symmetric
  trim and three-method rank chart were removed from the final narrative and
  remain preserved in the earlier experiment and rollback snapshot.
- The final rank-comparison chart now compares only the primary all-ten result
  with the largest-band-excluded scene-depth result.
- Data remain fixed to scene-depth snapshot `20260717T225650Z`.
- Pre-edit rollback point:
  `data/snapshots/20260718T214740Z_before-final-primary-plus-largest-only/`.
- Intermediate executed-state snapshot before separating the published
  calculation path from the broader experiment function:
  `data/snapshots/20260718T215039Z_completed-final-primary-plus-largest-only/`.
- Completed-state snapshot:
  `data/snapshots/20260718T215248Z_completed-final-primary-plus-largest-only-v2/`.

## 19 July 2026 — add composition and raw-impact context to final

- Revised notebook:
  `notebooks/final/uk_bands_punching_above_weight.ipynb`
- Change: added a ten-band horizontal stacked bar for every city, followed by
  the raw combined city totals before the existing population-normalized
  primary result.
- The separate concentration and scene-depth score bars were consolidated:
  concentration is visible in the band stack, exact scene-depth results remain
  in the table, and chart 04 now compares raw, normalized and scene-depth
  ranks on one scale.
- The primary conclusion remains population-normalized all-ten reach; the raw
  total is descriptive context, and largest-band exclusion remains the only
  alternative scene-depth ranking.
- Data remain fixed to scene-depth snapshot `20260717T225650Z`.
- Pre-edit rollback point:
  `data/snapshots/20260718T220404Z_before-final-band-composition-and-raw-impact/`.
- Completed-state snapshot:
  `data/snapshots/20260718T221021Z_completed-final-band-composition-and-raw-impact/`.

## 19 July 2026 — show band composition as 100% bars

- Revised chart 04.01 so every city's horizontal bar has equal length and
  totals 100%. Segment widths now encode each band's share of its city's
  selected Spotify reach rather than absolute listener counts.
- Absolute scale remains available immediately afterward in chart 04.02, so
  the change separates the composition question from the city-impact question.
- Pre-edit rollback point:
  `data/snapshots/20260718T221510Z_before-100-percent-city-band-bars/`.
- Completed-state snapshot:
  `data/snapshots/20260718T221617Z_completed-100-percent-city-band-bars/`.

## 19 July 2026 — switch final denominator to OECD/EU FUAs

- The prior final used 2021 census built-up-area populations inherited from
  the original ten-city panel; it did not use Functional Urban Areas.
- The revised final starts from the ten largest UK OECD/EU FUAs in
  `reference/uk_fua_top20_2021.csv`, using 2021 OECD population observations.
  The top-ten panel is therefore London, Manchester, Birmingham, Leeds,
  Glasgow, Liverpool, Newcastle, Sheffield, Bristol and Leicester.
- Standardized frozen inputs:
  `data/processed/fua_top10_band_metrics_20260718T204000Z.csv` and
  `data/processed/fua_top10_rankings_20260718T204000Z.csv`.
- New same-structure top-20 experiment:
  `notebooks/experiments/snapshots/uk_bands_top20_fua_final_structure_20260718T204000Z.ipynb`.
- Its standardized frozen inputs are
  `data/processed/fua_top20_band_metrics_20260718T204000Z.csv` and
  `data/processed/fua_top20_rankings_20260718T204000Z.csv`.
- Both use the already captured Spotify snapshot `20260718T204000Z`; no new
  live collection was performed.
- Pre-edit rollback point:
  `data/snapshots/20260718T222231Z_before-final-switch-to-fua-and-top20-mirror/`.
- Completed-state snapshot:
  `data/snapshots/20260718T222922Z_completed-final-fua-and-top20-final-structure/`.

## 19 July 2026 — consolidate the Crawley-inclusive top-100 experiment

- Canonical executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top100_popularity_first_fua_20260718T204522Z.ipynb`.
- Resolution: the earlier raw-only and population-adjusted top-100 notebooks
  used the same frozen selection and both contained The Cure/Crawley. The
  second appeared different because only it applied the FUA denominator.
- The canonical narrative now presents selected bands, raw strict-FUA reach,
  the strict population-adjusted result, an at-least-two-band stability
  diagnostic and raw-versus-normalized rank movement in one sequence.
- Crawley remains first in the complete strict population-adjusted result,
  supported by The Cure alone. One-band FUAs are visibly hatched and labelled;
  the leading multi-band diagnostic is Oxford, Cambridge and Sheffield.
- Both predecessor notebooks remain unchanged and are explicitly documented
  as preserved branches rather than competing current experiments.
- Frozen data remain at Spotify snapshot `20260718T204522Z`; no live capture
  was performed, and the city-first final notebook was not modified.
- Pre-edit rollback point:
  `data/snapshots/20260718T223202Z_before-canonical-crawley-top100-experiment/`.
- Completed-state snapshot:
  `data/snapshots/20260718T223834Z_completed-canonical-crawley-top100-experiment/`.

## 19 July 2026 — prepare a top-200 popularity-first review list

- Re-ran the existing popularity-first selector with `top_n=200` against the
  same frozen Spotify snapshot `20260718T204522Z`; no live capture was
  performed.
- Full selected-band output:
  `data/processed/popularity_first_top200_20260718T204522Z_bands.csv`.
- Compact editorial review list:
  `data/interim/popularity_first_top200_20260718T204522Z_review.csv`.
  It retains rank, Spotify reach, identity and reported-origin fields, and
  flags unresolved origins plus the known Bee Gees/Los Hornos mismatch.
- At initial review-list generation, the first 100 selected rows exactly
  reproduced
  `data/processed/popularity_first_top100_20260718T204522Z_bands.csv`.
  The later canonical top-200 branch retained the same ranks, identities and
  metrics but corrected the Bee Gees origin from the erroneous archived
  Wikidata label `Los Hornos` to `Redcliffe`; the complete rows therefore no
  longer match byte for byte. The additional range begins with Stereophonics
  at rank 101 and ends with Amber Run at rank 200 (2,165,390 monthly listeners
  in the frozen capture).
- This is a review branch only: no top-200 notebook or population-adjusted
  result has been built or promoted.
- Pre-run rollback point:
  `data/snapshots/20260718T225712Z_before-top200-popularity-first-review-list/`.
- Completed-state snapshot:
  `data/snapshots/20260718T225853Z_completed-top200-popularity-first-review-list/`.

## 19 July 2026 — replace the canonical top-100 experiment with top 200

- New canonical executed notebook:
  `notebooks/experiments/snapshots/uk_bands_top200_popularity_first_fua_20260718T204522Z.ipynb`.
- The popularity-first selection now retains 200 groups from the same frozen
  Spotify snapshot `20260718T204522Z`; no live capture was performed.
- Added a top-200-specific override file:
  `reference/popularity_first_top200_overrides_20260718.csv`.
  It preserves the reviewed top-100 identity decisions and corrects three
  unreadable or erroneous origins: Bee Gees/Redcliffe, Wet Leg/Isle of Wight
  and The Cult/Bradford.
- Added the complete audited mapping universe:
  `reference/popularity_first_top200_origin_fua_mapping_20260718.csv`.
  The strict result maps 154 bands to 28 FUAs and covers 84.8% of selected
  captured reach. The reviewed-extended sensitivity maps 169 bands to 35 FUAs
  and covers 91.1% of reach.
- London remains the raw-reach leader. Crawley remains first in the complete
  strict population-adjusted result through The Cure alone. Bath and North
  East Somerset, Oxford and Cambridge lead the at-least-two-band stability
  diagnostic.
- Population-adjusted output columns now have catalogue-neutral
  `selected_*` names. The legacy `top100_*` aliases remain so the frozen
  top-100 notebooks are still rerunnable.
- The former canonical top-100 notebook and its raw-only and
  population-adjusted predecessors remain unchanged and linked from the new
  notebook appendix and notebook map.
- The city-first final notebook was not modified.
- Pre-edit rollback point:
  `data/snapshots/20260718T231256Z_before-replacing-top100-with-top200-popularity-first-study/`.
- Completed-state snapshot:
  `data/snapshots/20260718T232059Z_completed-canonical-top200-popularity-first-study/`.

## Working convention

Before a new capture or methodological branch, create a labeled snapshot. Keep
new analyses in a dated notebook under `notebooks/experiments/snapshots/`, use
dated raw and processed inputs, and add the completed state here. Promote no
experiment into `notebooks/final/` without a separate publication decision.
