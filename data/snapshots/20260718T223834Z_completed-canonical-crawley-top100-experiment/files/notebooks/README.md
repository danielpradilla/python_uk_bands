# Notebook map

## Reader-facing analysis

[`final/uk_bands_punching_above_weight.ipynb`](final/uk_bands_punching_above_weight.ipynb)
is the leading, executed 100-band analysis. Its population-selected universe is
the ten largest UK OECD/EU Functional Urban Areas using frozen 2021 population
data. It introduces the study question, catalogue rules, sources, formulas and
assumptions before showing 100% band composition and raw FUA totals. It then
presents the all-ten FUA-population-normalized result as the primary ranking
and removes each FUA's largest band as one scene-depth test. The final rank
chart compares raw totals, normalized totals and scene depth.

## Reproducible experiments

[`experiments/snapshots/uk_bands_top20_fua_final_structure_20260718T204000Z.ipynb`](experiments/snapshots/uk_bands_top20_fua_final_structure_20260718T204000Z.ipynb)
mirrors the final notebook section for section while expanding the
population-selected universe to the twenty largest UK FUAs and the balanced
catalogue to 200 bands. All twenty areas remain in the tables, charts and
calculations. Its charts are isolated under
`artifacts/experiments/top20_fua_final_structure/20260718T204000Z/`.

[`experiments/uk_bands_scene_depth_10_per_city.ipynb`](experiments/uk_bands_scene_depth_10_per_city.ipynb) tests a frozen 100-band catalogue with ten bands per city. It compares all-ten, top-excluded and symmetric-trim rankings without changing the published notebook or charts.

[`experiments/snapshots/uk_bands_top20_city_first_20260718T204000Z.ipynb`](experiments/snapshots/uk_bands_top20_city_first_20260718T204000Z.ipynb)
is the dated primary-design experiment: the twenty largest UK OECD/EU
Functional Urban Areas, ten reviewed bands per area, and both all-ten and
population-normalized symmetric-trim rankings. It shows the top ten in the
narrative while retaining all twenty in the tables and calculations. It is
preserved as the earlier symmetric-trim branch; the final-structure mirror
above uses largest-band exclusion instead.

[`experiments/snapshots/uk_bands_top100_popularity_first_fua_20260718T204522Z.ipynb`](experiments/snapshots/uk_bands_top100_popularity_first_fua_20260718T204522Z.ipynb)
is the canonical popularity-first experiment. It starts with the reviewed top
100 from the frozen Wikidata/Spotify candidate universe, shows raw FUA reach,
then applies the 2021 OECD/EU FUA population denominator. Crawley leads the
complete strict result through The Cure; one-band FUAs are visibly marked, and
a separate minimum-two-band display acts as a stability diagnostic. Raw and
normalized ranks are compared on the same strict 20-FUA set. Its charts are
isolated under
`artifacts/experiments/top100_popularity_first_fua/20260718T204522Z/`.

The raw-only
[`experiments/snapshots/uk_bands_top100_popularity_first_20260718T204522Z.ipynb`](experiments/snapshots/uk_bands_top100_popularity_first_20260718T204522Z.ipynb)
and population-adjusted
[`experiments/snapshots/uk_bands_top100_popularity_first_population_adjusted_20260718T204522Z.ipynb`](experiments/snapshots/uk_bands_top100_popularity_first_population_adjusted_20260718T204522Z.ipynb)
notebooks are preserved predecessor branches. Their inputs and substantive
results are consolidated in the canonical notebook above; neither is deleted
or silently rewritten.

[`experiments/snapshots/`](experiments/snapshots/) contains executed,
timestamped current-data previews and snapshot comparisons. These notebooks are
sensitivity runs, not publication replacements; each reads explicit frozen
inputs and writes charts outside `artifacts/charts/`.

The checksummed rollback points and experiment lineage are listed in
[`../ANALYSIS_HISTORY.md`](../ANALYSIS_HISTORY.md).

## Superseded publication

[`archive/published-v1/uk_bands_punching_above_weight.ipynb`](archive/published-v1/uk_bands_punching_above_weight.ipynb)
preserves the September 2025 50-band publication and its executed outputs.
Its eight charts live under `artifacts/archive/published-v1/`.

## Original analysis archive

[`archive/original-analysis/python_uk_bands.ipynb`](archive/original-analysis/python_uk_bands.ipynb) is the preserved original scratchpad. It contains early API experiments, cached-data exploration and the first attempts at a broader MusicBrainz catalogue. It is useful as project history but is not the publication notebook and is not expected to execute cleanly from top to bottom.

## Archived route

[`archive/google-trends/`](archive/google-trends/) contains the abandoned Google Trends notebooks and their local inputs. That route was dropped because normalized search interest was too fragile for the main city comparison.
