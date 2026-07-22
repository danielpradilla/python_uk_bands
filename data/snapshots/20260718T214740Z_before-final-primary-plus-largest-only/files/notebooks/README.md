# Notebook map

## Reader-facing analysis

[`final/uk_bands_punching_above_weight.ipynb`](final/uk_bands_punching_above_weight.ipynb)
is the leading, executed 100-band analysis. It introduces the study question,
fixed panel, catalogue rules, data, formulas and assumptions before presenting
current global Spotify reach and the two scene-depth sensitivity tests. The
earlier five-band comparison and the Google Trends, automated-MusicBrainz and
50-band dead ends are retained as appendices rather than reader onboarding.

## Reproducible experiments

[`experiments/uk_bands_scene_depth_10_per_city.ipynb`](experiments/uk_bands_scene_depth_10_per_city.ipynb) tests a frozen 100-band catalogue with ten bands per city. It compares all-ten, top-excluded and symmetric-trim rankings without changing the published notebook or charts.

[`experiments/snapshots/uk_bands_top20_city_first_20260718T204000Z.ipynb`](experiments/snapshots/uk_bands_top20_city_first_20260718T204000Z.ipynb)
is the dated primary-design experiment: the twenty largest UK OECD/EU
Functional Urban Areas, ten reviewed bands per area, and both all-ten and
population-normalized symmetric-trim rankings. It shows the top ten in the
narrative while retaining all twenty in the tables and calculations.

[`experiments/snapshots/uk_bands_top100_popularity_first_20260718T204522Z.ipynb`](experiments/snapshots/uk_bands_top100_popularity_first_20260718T204522Z.ipynb)
is the separate popularity-first experiment: a reviewed top 100 from a frozen
Wikidata/Spotify candidate universe, followed by origin mapping and geographic
concentration analysis.

[`experiments/snapshots/uk_bands_top100_popularity_first_population_adjusted_20260718T204522Z.ipynb`](experiments/snapshots/uk_bands_top100_popularity_first_population_adjusted_20260718T204522Z.ipynb)
preserves that raw concentration result and adds two OECD/EU FUA
population-normalized views: selected bands per million residents and captured
global monthly listeners per resident. It keeps strict origin-to-FUA coverage
as the main result, an extended mapping as sensitivity analysis, and a
minimum-two-band display as a stability diagnostic.

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
