# UK cities punching above their weight in bands

This project asks a deliberately narrow question: which of the largest UK
Functional Urban Areas (FUAs) have produced bands with an unusually large
global Spotify footprint relative to population?

The current result is exploratory. It uses a balanced, manually curated
100-band catalogue—ten bands for each of the ten largest UK FUAs—and a frozen
Spotify snapshot from 18 July 2026. “Reach” means current global Spotify
monthly-listener reach, not historical or cultural impact, record sales,
influence, live audiences or listening by local residents.

## Current deliverables

- [Executed analysis notebook](notebooks/final/uk_bands_punching_above_weight.ipynb)
- [Top-20 FUA experiment with the same structure](notebooks/experiments/08_uk_bands_top20_fua_final_structure.ipynb)
- [Ten-band scene-depth experiment](notebooks/experiments/01_uk_bands_scene_depth_10_per_city.ipynb)
- [Earlier top-20 symmetric-trim experiment](notebooks/experiments/05_uk_bands_top20_city_first.ipynb)
- [Canonical top-200 popularity-first FUA experiment](notebooks/experiments/10_uk_bands_top200_popularity_first_fua.ipynb)
- [Top-200 music-output-share versus population experiment](notebooks/experiments/11_uk_bands_top200_output_share_vs_population.ipynb)
- [Top-1,000 follower-share versus population experiment](notebooks/experiments/12_uk_bands_top1000_output_share_vs_population.ipynb)
- [Top-1,000 UK follower bubble, leading-band photo and output-quotient maps](notebooks/experiments/15_uk_bands_top1000_follower_maps.ipynb)
- [Top-1,000 negative-binomial band-count scaling model](notebooks/experiments/13_uk_bands_top1000_negative_binomial_scaling.ipynb)
- [Top-1,000 log–log follower scaling model](notebooks/experiments/14_uk_bands_top1000_loglog_follower_scaling.ipynb)
- [Current reader-facing charts](artifacts/charts/)
- [Archived 50-band publication](notebooks/archive/published-v1/uk_bands_punching_above_weight.ipynb)
- [Scene-depth experiment charts](artifacts/scene_depth/)

The [notebook map](notebooks/README.md) distinguishes the executed final
analysis, reproducible experiments and preserved historical work.
The [analysis history](ANALYSIS_HISTORY.md) records the dated notebooks,
frozen inputs and checksummed rollback points.

The dated 18 July 2026 notebooks are design experiments, not replacements for
the current final analysis. The top-20 mirror applies the final method to the
twenty largest UK FUAs. The canonical top-200 popularity-first notebook combines raw
geographic concentration, population-adjusted output and a multi-band
stability diagnostic in one narrative. The former canonical top-100 notebook
and its two earlier branches remain preserved in the notebook map.

## Current finding

Before population normalization, London, Manchester and Sheffield have the
largest combined reach across the selected catalogue. Across all ten selected
bands per FUA after normalization, Sheffield has the greatest current global
Spotify reach relative to 2021 OECD FUA population; Liverpool and Manchester
follow. This is the primary result. As an additional scene-depth test,
Sheffield ranks first after each FUA's largest selected act is removed,
Manchester ranks second and Birmingham third. The analysis status is **share
with caveats** because the catalogue is curated, genre-influenced and not a
census of British music.

The population universe comes from the
[OECD definition of cities and Functional Urban Areas](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html)
and the
[OECD Data Explorer population dataset](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en).

## Rebuild the notebook

Create an environment and install the project dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Generate the notebook from its versioned cell definitions, then execute it from the repository root:

```bash
python scripts/build_final_notebook.py
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace notebooks/final/uk_bands_punching_above_weight.ipynb \
  --ExecutePreprocessor.timeout=180
```

Execution reads only the selected frozen local snapshot and rewrites four PNGs
in `artifacts/charts/`. Live data capture remains a separate step, so notebook
execution cannot silently refresh Spotify values.

Build and execute the top-20 FUA experiment with the identical narrative and
calculation structure:

```bash
python scripts/build_top20_fua_experiment_notebook.py
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace \
  notebooks/experiments/08_uk_bands_top20_fua_final_structure.ipynb \
  --ExecutePreprocessor.timeout=240
```

Build and execute the isolated ten-band scene-depth experiment:

```bash
python scripts/build_scene_depth_notebook.py
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace notebooks/experiments/01_uk_bands_scene_depth_10_per_city.ipynb \
  --ExecutePreprocessor.timeout=180
```

The experiment reads the frozen 17 July 2026 snapshot and writes its three charts only to `artifacts/scene_depth/`.

Build and execute the canonical popularity-first experiment:

```bash
python scripts/build_popularity_first_canonical_notebook.py --force
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace \
  notebooks/experiments/10_uk_bands_top200_popularity_first_fua.ipynb \
  --ExecutePreprocessor.timeout=240
```

It reads the frozen top-200 selection, strict and extended FUA mappings, and
2021 population outputs. Its five charts are isolated under
`artifacts/experiments/top200_popularity_first_fua/20260718T204522Z/`.

## Select and compare frozen snapshots

The canonical 100-band notebook can use an exact FUA-study timestamp, a UTC
date or `latest`. The executed notebook records the exact resolved snapshot:

```bash
# Canonical top-10 FUA analysis
python scripts/build_final_notebook.py --snapshot 20260718T204000Z
python scripts/build_final_notebook.py --snapshot latest

# Archived September 2025 50-band publication
python scripts/build_published_v1_notebook.py --metrics-snapshot publication

# Companion method-first experiment
python scripts/build_scene_depth_notebook.py --snapshot 20260717T203002Z
python scripts/build_scene_depth_notebook.py --snapshot latest
```

Build the offline side-by-side snapshot comparison with:

```bash
python scripts/build_snapshot_comparison_notebook.py \
  --baseline-shortlist publication \
  --candidate-shortlist latest \
  --baseline-scene 20260717T203002Z \
  --candidate-scene latest
```

Snapshot timestamps are UTC. A date selector such as `2026-07-17` chooses the
latest complete snapshot on that UTC date.

## Refresh and rollback data

Create a checksummed rollback point before any live collection:

```bash
python scripts/create_data_snapshot.py --label before-refresh
```

Refresh the broad MusicBrainz catalogue into timestamped raw files:

```bash
python scripts/fetch_musicbrainz_artists.py
```

Fetch a timestamped Spotify-metrics candidate and promote it only if every
completeness and identity-stability check passes:

```bash
python scripts/refresh_spotify_metrics.py --promote
```

For a read-only public-page capture that can never promote the 50-band cache:

```bash
python scripts/capture_shortlist_public_snapshot.py
```

Refresh the fixed 100-band scene-depth catalogue while reusing its reviewed
artist IDs:

```bash
python scripts/run_scene_depth_experiment.py \
  --reuse-identifiers data/interim/scene_depth_spotify_ids_20260717T203002Z.csv
```

The refresh command never replaces
`data/processed/shortlist_spotify_metrics.json` with a partial response. Reports
and candidates are retained under `data/raw/spotify/`. Verify a rollback
snapshot without changing files, then restore it explicitly if needed:

```bash
python scripts/restore_data_snapshot.py data/snapshots/SNAPSHOT_DIRECTORY
python scripts/restore_data_snapshot.py data/snapshots/SNAPSHOT_DIRECTORY --apply
```

## Main inputs

- `reference/uk_fua_top20_2021.csv`: frozen official OECD/EU top-20 UK FUA universe and 2021 population denominators
- `data/processed/fua_top10_band_metrics_*.csv`: final balanced 100-band FUA catalogue and frozen Spotify reach
- `data/processed/fua_top10_rankings_*.csv`: final raw, normalized and scene-depth rankings
- `data/processed/fua_top20_band_metrics_*.csv`: experimental balanced 200-band FUA catalogue and frozen Spotify reach
- `data/processed/fua_top20_rankings_*.csv`: experimental top-20 rankings using the final method
- `reference/scene_depth_bands.csv` and `reference/built_up_areas.csv`: preserved inputs for the earlier built-up-area analysis
- `reference/popularity_first_top200_overrides_20260718.csv`: reviewed identity and origin exceptions for the current popularity-first experiment
- `reference/popularity_first_top200_origin_fua_mapping_20260718.csv`: audited strict, sensitivity and excluded origin-to-FUA decisions for the top 200
- `reference/popularity_first_top1000_origin_fua_mapping_20260718.csv`: official municipality-crosswalk mapping and explicit exclusions for the frozen top 1,000
- `data/processed/scene_depth_band_metrics_*.csv`: frozen current-global-reach snapshots
- `data/processed/scene_depth_rankings_*.csv`: reproducible saved ranking outputs
- `data/processed/top20_city_rankings_*.csv`: frozen twenty-area scene-depth results
- `data/processed/popularity_first_top200_*`: current frozen popularity-first selection, origin summaries and population-adjusted outputs
- `data/processed/popularity_first_top1000_*`: frozen top-1,000 selection and population/share experiment outputs
- `data/processed/popularity_first_top100_*`: preserved predecessor popularity-first outputs
- `reference/original_shortlist.csv` and `data/processed/shortlist_spotify_metrics.json`: archived v1 inputs

Project decisions, unresolved questions and pipeline work are recorded in [TASKS.md](TASKS.md).

## Repository layout

```text
notebooks/
  final/                              reader-facing executed analysis
  experiments/                        reproducible companion analyses
  archive/published-v1/               superseded September 2025 publication
  archive/original-analysis/          preserved original scratchpad
  archive/google-trends/              abandoned route and its saved inputs
reference/                            curated lists, geography and reviewed IDs
data/
  raw/                                timestamped source responses
  interim/                            reviewable pipeline output
  processed/                          canonical analysis-ready data
  snapshots/                          checksummed rollback points
artifacts/
  charts/                             exported reader-facing figures
  archive/published-v1/               superseded 50-band figures
  scene_depth/                        companion-experiment figures
  experiments/                        isolated charts from dated experiments
src/python_uk_bands/
  analysis.py                         ranking and sensitivity calculations
  dataset.py                          deterministic input loading and checks
  visuals.py                          canonical house style, tables and charts
scripts/
  build_final_notebook.py             versioned notebook source
  build_fua_study_notebook.py         shared top-10/top-20 FUA notebook source
  build_fua_study_inputs.py           standardized frozen FUA inputs
  build_top20_fua_experiment_notebook.py top-20 mirror entry point
  build_popularity_first_canonical_notebook.py canonical top-200 experiment
  build_output_share_notebook.py       output-share versus population experiment
  build_published_v1_notebook.py      archived 50-band notebook source
  fetch_musicbrainz_artists.py        broad-catalogue collection
  refresh_spotify_metrics.py          guarded, dated metrics refresh
  resolve_spotify_artists.py          Spotify candidate matching
  create_data_snapshot.py             checksummed rollback point
  restore_data_snapshot.py            verify or restore a rollback point
tests/                                calculation and saved-data checks
```
