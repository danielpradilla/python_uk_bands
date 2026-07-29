# Current global Spotify reach across the UK’s largest music cities

This repository’s final study asks a deliberately narrow question: among the ten largest UK Functional Urban Areas, which places have the greatest current global Spotify reach across ten selected bands relative to population?

The reader-facing result is the executed [final study notebook](notebooks/final/uk_bands_punching_above_weight.ipynb). It uses a balanced catalogue of 100 bands—ten reviewed bands for each area—a frozen Spotify snapshot captured on 18 July 2026, and 2021 OECD Functional Urban Area populations.

## Main finding

Before population normalization, London, Manchester and Sheffield have the largest combined monthly-listener counts in the selected catalogue. After the same ten-band totals are divided by Functional Urban Area population, Sheffield ranks first, followed by Liverpool and Manchester.

![Current global Spotify reach across ten selected bands, divided by FUA population](artifacts/charts/chart_03_fua_population_normalized_total.png)

Removing each area’s largest selected band provides a separate scene-depth sensitivity test. Sheffield remains first, Manchester moves to second and Birmingham moves to third. Liverpool falls from second to fifth because the Beatles supply 59% of its selected monthly-listener total; Arctic Monkeys supply 57% of Sheffield’s total, while Oasis supplies 32% of Manchester’s.

![Raw, population-normalized and largest-band-excluded ranks](artifacts/charts/chart_04_raw_normalized_scene_depth_fua_ranks.png)

The primary result is the all-ten population-normalized ranking. Largest-band exclusion answers a narrower robustness question and does not replace the main ranking.

## Study design

- **Geographic unit:** an OECD/EU Functional Urban Area (FUA), meaning an urban centre plus its economically connected commuting zone.
- **Study universe:** the ten largest UK FUAs by the OECD’s 2021 population observations.
- **Catalogue:** ten reviewed bands per FUA, producing 100 band–area assignments. Solo artists are outside scope.
- **Origin rule:** a band is assigned to the FUA containing its reviewed formation place.
- **Reach measure:** current global Spotify monthly listeners captured once on 18 July 2026.
- **Primary calculation:** the sum of the ten selected bands’ monthly-listener counts divided by FUA population.
- **Sensitivity calculation:** the same population-normalized total after removing each FUA’s largest selected band.

For FUA \(c\), with monthly-listener count \(L_{ic}\) for selected band \(i\) and 2021 population \(P_c\):

- Raw selected reach: \(\sum_{i=1}^{10} L_{ic}\)
- Population-normalized selected reach: \(\sum_{i=1}^{10} L_{ic} / P_c\)
- Largest-band-excluded reach: \((\sum L_{ic} - \max L_{ic}) / P_c\)

Monthly-listener counts are summed artist-level platform metrics, not unique people: the same person can listen to more than one selected band.

## What the result does and does not show

The result describes this fixed 100-band catalogue across the ten largest UK FUAs. It is evidence about selected current global Spotify reach relative to a consistent population denominator.

It is not a census of British bands, a measure of historical cultural importance, a local listening rate, or an estimate of how many residents listen to bands from their area. The catalogue is manually curated and genre-influenced; two formation-place assignments are marked low confidence and require review. Dividing global reach by local population adjusts for area size but does not imply that the listeners live there. The appropriate publication status is therefore **share with caveats**.

## Sources

### Geography and population

- [OECD definition of cities and Functional Urban Areas](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html)
- [OECD Data Explorer: Population by age and sex — Cities and FUAs](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en)
- [Frozen UK FUA population universe](reference/uk_fua_top20_2021.csv), containing the official FUA codes, 2021 populations, source URL and capture timestamp used by the study

### Band identities, formation places and Spotify reach

- [Final 100-band analysis table](data/processed/fua_top10_band_metrics_20260718T204000Z.csv), containing the reviewed formation place, row-level origin evidence URL, confidence, Spotify artist ID, captured monthly listeners, followers, population and source fields for every selected band
- [Spotify capture report](data/raw/spotify/top20_city_spotify_metrics_20260718T204000Z_report.json), recording completeness and capture provenance for the frozen source snapshot
- [MusicBrainz](https://musicbrainz.org/) and [Wikidata](https://www.wikidata.org/) records, linked at row level from the final analysis table and used as evidence for band identity and formation place

The Spotify values were captured from Spotify’s web-player artist overview. That read-only endpoint is undocumented, so the frozen local snapshot—not a live request—is the reproducible source for this study.

### Saved calculations

- [Final ranking table](data/processed/fua_top10_rankings_20260718T204000Z.csv), containing the raw, population-normalized and largest-band-excluded values and ranks
- [Final study build report](data/processed/fua_top10_study_20260718T204000Z_report.json), recording the snapshot, input paths, catalogue dimensions and three leading areas under each calculation
- [Notebook generator](scripts/build_final_notebook.py) and [shared FUA study builder](scripts/build_fua_study_notebook.py), which define the notebook narrative, formulas, validations and charts

## Reproduce the final study

Create an environment and install the project dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Rebuild the notebook from its versioned cell definitions and execute it against the exact frozen snapshot:

```bash
python scripts/build_final_notebook.py --snapshot 20260718T204000Z
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace notebooks/final/uk_bands_punching_above_weight.ipynb \
  --ExecutePreprocessor.timeout=180
```

Notebook execution reads only local frozen inputs and rewrites the four reader-facing charts under [`artifacts/charts/`](artifacts/charts/). It cannot silently refresh Spotify values.

Run the calculation and saved-data checks with:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## Final study files

- [Executed final notebook](notebooks/final/uk_bands_punching_above_weight.ipynb)
- [Frozen band-level input](data/processed/fua_top10_band_metrics_20260718T204000Z.csv)
- [Frozen ranking output](data/processed/fua_top10_rankings_20260718T204000Z.csv)
- [Reader-facing charts](artifacts/charts/)
- [Notebook generator](scripts/build_final_notebook.py)
