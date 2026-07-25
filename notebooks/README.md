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

The two-digit filename prefixes record original creation order across the
single experiment series.

Creation sequence:

1. [`01` scene-depth workbench](experiments/01_uk_bands_scene_depth_10_per_city.ipynb)
2. [`02` scene-depth snapshot](experiments/02_uk_bands_scene_depth.ipynb)
3. [`03` publication preview](experiments/03_uk_bands_publication_preview.ipynb)
4. [`04` snapshot comparison](experiments/04_uk_bands_snapshot_comparison.ipynb)
5. [`05` top-20 city-first](experiments/05_uk_bands_top20_city_first.ipynb)
6. [`06` top-100 popularity-first](experiments/06_uk_bands_top100_popularity_first.ipynb)
7. [`07` top-100 population-adjusted](experiments/07_uk_bands_top100_popularity_first_population_adjusted.ipynb)
8. [`08` top-20 FUA final structure](experiments/08_uk_bands_top20_fua_final_structure.ipynb)
9. [`09` top-100 canonical FUA](experiments/09_uk_bands_top100_popularity_first_fua.ipynb)
10. [`10` top-200 canonical FUA](experiments/10_uk_bands_top200_popularity_first_fua.ipynb)
11. [`11` top-200 output share](experiments/11_uk_bands_top200_output_share_vs_population.ipynb)
12. [`12` top-1,000 output share](experiments/12_uk_bands_top1000_output_share_vs_population.ipynb)
13. [`13` top-1,000 negative-binomial scaling](experiments/13_uk_bands_top1000_negative_binomial_scaling.ipynb)
14. [`14` top-1,000 log–log follower scaling](experiments/14_uk_bands_top1000_loglog_follower_scaling.ipynb)
15. [`15` top-1,000 follower maps](experiments/15_uk_bands_top1000_follower_maps.ipynb)

[`experiments/08_uk_bands_top20_fua_final_structure.ipynb`](experiments/08_uk_bands_top20_fua_final_structure.ipynb)
mirrors the final notebook section for section while expanding the
population-selected universe to the twenty largest UK FUAs and the balanced
catalogue to 200 bands. All twenty areas remain in the tables, charts and
calculations. Its charts are isolated under
`artifacts/experiments/top20_fua_final_structure/20260718T204000Z/`.

[`experiments/01_uk_bands_scene_depth_10_per_city.ipynb`](experiments/01_uk_bands_scene_depth_10_per_city.ipynb) tests a frozen 100-band catalogue with ten bands per city. It compares all-ten, top-excluded and symmetric-trim rankings without changing the published notebook or charts.

[`experiments/05_uk_bands_top20_city_first.ipynb`](experiments/05_uk_bands_top20_city_first.ipynb)
is the dated primary-design experiment: the twenty largest UK OECD/EU
Functional Urban Areas, ten reviewed bands per area, and both all-ten and
population-normalized symmetric-trim rankings. It shows the top ten in the
narrative while retaining all twenty in the tables and calculations. It is
preserved as the earlier symmetric-trim branch; the final-structure mirror
above uses largest-band exclusion instead.

[`experiments/10_uk_bands_top200_popularity_first_fua.ipynb`](experiments/10_uk_bands_top200_popularity_first_fua.ipynb)
is the canonical popularity-first experiment. It starts with the reviewed top
200 from the frozen Wikidata/Spotify candidate universe, shows raw FUA reach,
then applies the 2021 OECD/EU FUA population denominator. Crawley leads the
complete strict result through The Cure; one-band FUAs are visibly marked, and
a separate minimum-two-band display acts as a stability diagnostic. Raw and
normalized ranks are compared on the same strict 28-FUA set. Its charts are
isolated under
`artifacts/experiments/top200_popularity_first_fua/20260718T204522Z/`.

[`experiments/11_uk_bands_top200_output_share_vs_population.ipynb`](experiments/11_uk_bands_top200_output_share_vs_population.ipynb)
reframes the same frozen top-200 catalogue as a share comparison. It plots each
represented FUA's share of selected bands against its share of the complete
83-FUA population universe, sizes bubbles by follower share, keeps zero-output
FUAs in the denominator and reports band, follower and monthly-listener output
quotients. Its chart and full FUA table are isolated under
`artifacts/experiments/top200_output_share_vs_population/20260718T204522Z/`.

[`experiments/12_uk_bands_top1000_output_share_vs_population.ipynb`](experiments/12_uk_bands_top1000_output_share_vs_population.ipynb)
extends that experiment to the first 1,000 eligible groups in the same frozen
Spotify capture. Its primary chart compares follower share with population
share and sizes circles by selected-band count; a companion chart retains band
share as the vertical measure. The map uses the official OECD UK
municipality-to-FUA crosswalk plus captured Wikidata administrative ancestry,
with unresolved and non-FUA origins left unallocated. Its outputs are isolated
under
`artifacts/experiments/top1000_output_share_vs_population/20260718T204522Z/`.

[`experiments/15_uk_bands_top1000_follower_maps.ipynb`](experiments/15_uk_bands_top1000_follower_maps.ipynb)
maps the ten FUAs with the largest combined follower totals in the frozen
top-1,000 catalogue. Its first UK map uses follower-proportional circle areas;
its second keeps the same geography and scale while filling each circle with
the FUA's largest-followed selected band; its third maps the follower output
quotient, with a visible 1× population-share benchmark. The notebook uses a
frozen Natural Earth outline, Wikidata city-centre coordinates and locally
captured Wikimedia Commons photos with per-file attribution. Its outputs are isolated under
`artifacts/experiments/top1000_follower_maps/20260718T204522Z/`.

[`experiments/13_uk_bands_top1000_negative_binomial_scaling.ipynb`](experiments/13_uk_bands_top1000_negative_binomial_scaling.ipynb)
models mapped top-1,000 band counts for all 83 FUAs with an NB2 log link. It
retains 22 zero-band FUAs, estimates the population-scaling exponent, compares
negative binomial with Poisson and ranks cities by variance-standardized count
residuals.

[`experiments/14_uk_bands_top1000_loglog_follower_scaling.ipynb`](experiments/14_uk_bands_top1000_loglog_follower_scaling.ipynb)
models summed follower output against population for the 61 positive-output
FUAs. It reports HC3 uncertainty, Huber and leave-one-city-out sensitivity,
shows the empirical scaling line beside the proportional-output line and makes
the zero-city and superstar limitations explicit. Both model notebooks write
to `artifacts/experiments/top1000_scaling_models/20260718T204522Z/`.

The former canonical
[`experiments/09_uk_bands_top100_popularity_first_fua.ipynb`](experiments/09_uk_bands_top100_popularity_first_fua.ipynb)
is preserved as the immediately preceding branch.

The raw-only
[`experiments/06_uk_bands_top100_popularity_first.ipynb`](experiments/06_uk_bands_top100_popularity_first.ipynb)
and population-adjusted
[`experiments/07_uk_bands_top100_popularity_first_population_adjusted.ipynb`](experiments/07_uk_bands_top100_popularity_first_population_adjusted.ipynb)
notebooks are preserved predecessor branches. Their inputs and substantive
results are consolidated in the preserved top-100 canonical notebook; none is
deleted or silently rewritten.

All experiment notebooks now live directly under [`experiments/`](experiments/).
Snapshot identifiers remain recorded inside the notebooks and in their frozen
input and artifact paths rather than in the notebook filenames.

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
