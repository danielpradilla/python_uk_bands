# Analysis history

This is the short provenance record for the published study and its major
experimental branches. The executed notebooks use frozen local inputs and do
not refresh network data.

## 18–19 July 2026 — canonical study design

- Froze Spotify artist metrics at snapshot `20260718T204000Z` and established
  the Functional Urban Area population workflow.
- Standardized the final universe as the ten largest UK FUAs with ten reviewed
  bands per area. The canonical inputs are
  `data/processed/fua_top10_band_metrics_20260718T204000Z.csv` and
  `reference/uk_fua_top20_2024.csv`.
- Made summed global monthly listeners divided by FUA population the primary
  comparison. Removing each area's largest selected band is the sole
  dominant-band sensitivity calculation.
- Added composition, raw-total, population-normalized and rank-comparison
  charts to `notebooks/final/uk_bands_punching_above_weight.ipynb`.
- Saved the canonical ranking and build report under `data/processed/` with the
  same snapshot ID. A same-structure top-20 branch remains experiment 08.

## 19 July 2026 — popularity-first branches

- Experiments 06–10 reversed the editorial city-first design by selecting the
  top 100 and then top 200 eligible UK groups from frozen Spotify data.
- The top-200 branch retained reviewed identity and origin overrides, strict
  and extended FUA mappings, and stability views for places represented by
  multiple bands.
- These branches remain exploratory and do not replace the balanced final
  study.

## 22–23 July 2026 — top-1,000 mapping and scaling

- Expanded the frozen popularity-first universe to 1,000 bands and mapped 660
  bands to 61 of the 83 FUAs in the population denominator.
- Experiments 11–15 cover output share, count and follower scaling, and follower
  maps. They keep zero-output FUAs and unresolved origins explicit rather than
  redistributing them.
- Frozen geography, mapping evidence and map-asset attribution remain under
  `data/raw/`, `data/interim/` and `reference/`.

## 25 July 2026 — review follow-up experiments

- Experiments 16–23 test specification sensitivity, scene concentration,
  formation decades, genre history, infrastructure, band networks,
  longitudinal Spotify change and Wikipedia attention.
- Their claims remain descriptive and exploratory; none modifies the final
  notebook's ranking or interpretation.

## 22 August 2026 — final audit and selection sensitivity

- Published deterministic inclusion rules and the frozen data dictionary in
  `reference/final_study_methodology.md`.
- Audited every material origin assignment. The final catalogue records 99 as
  high-confidence and Chumbawamba's Leeds assignment as medium-confidence
  because credible histories disagree.
- Experiment 24 compared the editorial catalogue with popularity-selected
  ten-band catalogues. Fifty of 80 comparable selections overlap, while the
  first four primary-index ranks remain unchanged. This is a follow-up branch,
  not part of the first article's claim.

## 31 August 2026 — population refresh before publication

- Replaced the population denominator with the OECD's complete 2024 UK FUA
  observations, frozen from the official API at `20260830T221015Z` UTC.
- Preserved every Spotify value and its July 2026 capture timestamp; no Spotify
  source was queried during the population refresh.
- Rebuilt the final study and every active experiment against the 2024
  population data. The final top-ten universe and all ten primary ranks remain
  unchanged.
- Documented the two-year source mismatch explicitly: Spotify attention is
  measured in 2026 and the latest complete observed FUA population is from
  2024.

## Preservation

- The full experiment index is `notebooks/experiments/README.md`; generated
  outputs are under `artifacts/experiments/`.
- `data/snapshots/` retains checksummed historical data and reference files
  only. Git tag `archive/pre-data-snapshot-prune-2026-08-30` preserves the
  removed code, notebook, chart and task-ledger copies.
- The archived task ledger can be inspected with
  `git show archive/pre-data-snapshot-prune-2026-08-30:TASKS.md`.

## Working convention

Keep new analyses in the next numbered experiment notebook, use dated frozen
inputs, and record only publication-relevant milestones here. Promote no
experiment into `notebooks/final/` without a separate publication decision.
