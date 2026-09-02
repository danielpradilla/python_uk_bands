# Current global Spotify reach across the UK’s largest music cities

This repository’s final study asks a deliberately narrow question: among the ten largest UK Functional Urban Areas, which places have the greatest current global Spotify reach across ten selected bands relative to population?

The reader-facing result is the executed [final study notebook](notebooks/final/uk_bands_punching_above_weight.ipynb). It uses a balanced catalogue of 100 bands—ten reviewed bands for each area—a frozen Spotify snapshot captured on 18 July 2026, and 2024 OECD Functional Urban Area populations.

The numerator and denominator have a documented two-year mismatch: Spotify attention is frozen in 2026, while 2024 is the latest complete OECD population year available for UK FUAs. The study uses the observed 2024 values instead of projecting a 2026 population.

## Main finding

Before population normalization, London, Manchester and Sheffield have the largest combined monthly-listener counts in the selected catalogue. After the same ten-band totals are divided by Functional Urban Area population, Sheffield ranks first, followed by Liverpool and Manchester.

![Current global Spotify reach across ten selected bands, divided by FUA population](artifacts/charts/chart_03_fua_population_normalized_total.png)

> **What this does not mean:** This is not a measure of local listening,
> evidence that a city caused a band's success, a ranking of historical
> cultural importance, or a complete census of each area's music. It is a
> comparison of one frozen, selected-band catalogue.

Removing each area’s largest selected band provides a separate scene-depth sensitivity test. Sheffield remains first, Manchester moves to second and Liverpool moves to third. The Beatles supply 53% of Liverpool’s selected monthly-listener total; Arctic Monkeys supply 56% of Sheffield’s total, while Oasis supplies 29% of Manchester’s.

![Raw, population-normalized and largest-band-excluded ranks](artifacts/charts/chart_04_raw_normalized_scene_depth_fua_ranks.png)

The primary result is the all-ten population-normalized ranking. Largest-band exclusion answers a narrower robustness question and does not replace the main ranking.

## Study design

- **Geographic unit:** an OECD/EU Functional Urban Area (FUA), meaning an urban centre plus its economically connected commuting zone.
- **Study universe:** the ten largest UK FUAs by the OECD’s 2024 population observations.
- **Catalogue:** ten reviewed bands per FUA, producing 100 band–area assignments. Solo artists are outside scope.
- **Origin rule:** a band is assigned to the FUA containing its reviewed formation place.
- **Reach measure:** current global Spotify monthly listeners captured on 18 July 2026 in two batches 5 minutes 22 seconds apart.
- **Primary calculation:** the sum of the ten selected bands’ monthly-listener counts divided by FUA population.
- **Sensitivity calculation:** the same population-normalized total after removing each FUA’s largest selected band.

For FUA \(c\), with monthly-listener count \(L_{ic}\) for selected band \(i\) and 2024 population \(P_c\):

- Raw selected reach: \(\sum_{i=1}^{10} L_{ic}\)
- Population-normalized selected reach: \(\sum_{i=1}^{10} L_{ic} / P_c\)
- Largest-band-excluded reach: \((\sum L_{ic} - \max L_{ic}) / P_c\)

Monthly-listener counts are summed artist-level platform metrics, not unique people: the same person can listen to more than one selected band.

## What the result does and does not show

The result describes this fixed 100-band catalogue across the ten largest UK FUAs. It is evidence about selected current global Spotify reach relative to a consistent population denominator.

It is not a census of British bands, a measure of historical cultural importance, a local listening rate, or an estimate of how many residents listen to bands from their area. The catalogue is manually curated and genre-influenced; all 100 formation-place assignments have reviewed evidence, but that does not make the selection representative. An independent audit records 99 assignments as high-confidence and retains Chumbawamba's Leeds assignment as medium-confidence because credible histories disagree between Leeds and Burnley. The audit also records the 14 later catalogue replacements and their resolved FUA assignments. Dividing global reach by local population adjusts for area size but does not imply that the listeners live there. The appropriate publication status is therefore **share with caveats**.

## Sources

### Geography and population

- [OECD definition of cities and Functional Urban Areas](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html)
- [OECD Data Explorer: Population by age and sex — Cities and FUAs](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_FUA_DEMO%40DF_AGE_SEX&lc=en)
- [Frozen UK FUA population universe](reference/uk_fua_top20_2024.csv), containing the official FUA codes, 2024 populations, source URL and capture timestamp used by the study
- [Frozen raw OECD extract](data/raw/geography/oecd_fua_population_2024_20260830T221015Z.csv) and [capture report](data/raw/geography/oecd_fua_population_2024_20260830T221015Z_report.json), preserving the exact API response and request used for the denominator

### Band identities, formation places and Spotify reach

- [Final 100-band analysis table](data/processed/fua_top10_band_metrics_20260718T204000Z.csv), containing the reviewed formation place, row-level origin evidence URL, confidence, Spotify artist ID, captured monthly listeners, followers, population and source fields for every selected band
- [Final origin-confidence audit](reference/final_origin_confidence_audit_20260822.md) and its [34-record evidence table](data/processed/final_origin_confidence_audit_20260822.csv), independently reviewing every band contributing at least 10% of an FUA's selected total plus all pre-audit medium-confidence records, with a documented addendum for the 14 later replacements
- [Primary Spotify capture report](data/raw/spotify/top20_city_spotify_metrics_20260718T204000Z_report.json) and [replacement-row capture report](data/raw/spotify/uk_group_spotify_metrics_20260718T204522Z_report.json), recording completeness and provenance for the two same-day batches
- Formation-place sources are linked at row level from the final analysis table and include official artist histories, MusicBrainz, Wikidata and established music-reference sources.

The Spotify values were captured from Spotify’s web-player artist overview. That read-only endpoint is undocumented, so the frozen local snapshot—not a live request—is the reproducible source for this study.

### Saved calculations

- [Final ranking table](data/processed/fua_top10_rankings_20260718T204000Z.csv), containing the raw, population-normalized and largest-band-excluded values and ranks
- [Final study build report](data/processed/fua_top10_study_20260718T204000Z_report.json), recording the snapshot, input paths, catalogue dimensions and three leading areas under each calculation
- [Inclusion rules and frozen data dictionary](reference/final_study_methodology.md), defining every published field and the exact row, calculation and tie rules
- [Final study notebook](notebooks/final/uk_bands_punching_above_weight.ipynb), which contains the narrative, formulas, validations and chart calls

## Reproduce the final study

The published result can be reproduced from the frozen files in this
repository. No Spotify credentials or network requests are needed after the
Python dependencies are installed.

Use Python 3.10 or newer and run every command below from the repository root.
For a fresh checkout:

```bash
git clone git@github.com:danielpradilla/uk-music-cities.git
cd uk-music-cities
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

First, verify the calculations and frozen outputs:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

The command should finish with `OK`. Then execute the versioned notebook
against the exact frozen snapshot:

```bash
python -m jupyter nbconvert \
  --execute \
  --to notebook \
  --inplace notebooks/final/uk_bands_punching_above_weight.ipynb \
  --ExecutePreprocessor.timeout=180
```

Notebook execution reads only local frozen inputs. It cannot silently refresh
Spotify values. It updates the executed notebook in place and rewrites these
four reader-facing charts:

- `artifacts/charts/chart_01_fua_band_share_stack.png`
- `artifacts/charts/chart_02_raw_fua_totals.png`
- `artifacts/charts/chart_03_fua_population_normalized_total.png`
- `artifacts/charts/chart_04_raw_normalized_scene_depth_fua_ranks.png`

Review the regenerated files with:

```bash
git status --short notebooks/final artifacts/charts
```

If Python cannot import `python_uk_bands`, confirm that the command is running
from the repository root and includes `PYTHONPATH=src`. Data-refresh and
capture scripts are separate historical workflows and are not required to
reproduce the published result.

## Final study files

- [Executed final notebook](notebooks/final/uk_bands_punching_above_weight.ipynb)
- [Frozen band-level input](data/processed/fua_top10_band_metrics_20260718T204000Z.csv)
- [Frozen ranking output](data/processed/fua_top10_rankings_20260718T204000Z.csv)
- [Reader-facing charts](artifacts/charts/)

## Repository map

- `notebooks/final/` contains the supported reader-facing study.
- `notebooks/experiments/` contains numbered research branches that may become
  later publications.
- `src/python_uk_bands/` contains calculations and chart code shared by the
  notebooks.
- `scripts/` contains data-capture and dataset-building commands.
- `data/` progresses from frozen raw captures through interim review tables to
  processed analysis inputs and outputs.
- `reference/` contains reviewed catalogues, overrides and methodology.
- `artifacts/` contains generated charts, audit tables and experiment outputs.
