# Experiment catalogue

These notebooks record the analytical development of the UK music-cities project in original creation order. They test alternative catalogues, geographic universes, metrics, models and source systems. They are reproducible research branches, not replacements for the [final study](../final/uk_bands_punching_above_weight.ipynb).

The two-digit filename prefix is the experiment number. Snapshot dates remain inside each notebook and in its frozen input and artifact paths rather than in the notebook filename.

## Phase 1 — catalogue depth and snapshot stability

### 01. [Scene-depth workbench](01_uk_bands_scene_depth_10_per_city.ipynb)

**What it tests:** Expands the original five-band city catalogue to ten bands per city and compares the untrimmed result, largest-band exclusion and symmetric trimming using the frozen 17 July 2026 snapshot.

**Why it matters:** It establishes that rankings can depend on catalogue breadth and superstar concentration. Manchester overtakes Sheffield when the largest band is excluded, while Liverpool falls after the Beatles are removed.

### 02. [Scene-depth later snapshot](02_uk_bands_scene_depth.ipynb)

**What it tests:** Repeats the same ten-band scene-depth analysis against a later frozen capture from 17 July 2026, with snapshot-specific inputs and chart outputs.

**Why it matters:** It separates substantive ranking changes from capture timing. The near-identical results show short-run reproducibility while preserving the later execution as a distinct audit state.

### 03. [Publication preview with current data](03_uk_bands_publication_preview.ipynb)

**What it tests:** Re-runs the original 50-band, five-per-city publication design using the July 2026 Spotify metrics while leaving the published September 2025 notebook untouched.

**Why it matters:** It shows whether the original story survives a newer platform snapshot and exposes the limits of the initial built-up-area geography and personal shortlist before those design choices are replaced.

### 04. [Snapshot comparison](04_uk_bands_snapshot_comparison.ipynb)

**What it tests:** Compares the fixed 50-band publication catalogue across September 2025 and July 2026, and separately checks two close scene-depth captures.

**Why it matters:** It distinguishes longitudinal movement from extraction consistency. The long-gap comparison shows band-level changes, while the 2.4-hour comparison is correctly treated as a capture check rather than a trend.

## Phase 2 — wider city universes and popularity-first selection

### 05. [Top-20 city-first analysis](05_uk_bands_top20_city_first.ipynb)

**What it tests:** Starts with the twenty largest UK FUAs, curates ten bands for each, and compares all-ten with symmetric-trim population-normalized rankings.

**Why it matters:** It expands the population-selected universe beyond the headline ten cities and tests whether a result survives when smaller major urban areas enter the comparison.

### 06. [Top-100 popularity-first origins](06_uk_bands_top100_popularity_first.ipynb)

**What it tests:** Selects the 100 UK groups with the largest captured monthly-listener counts first, then describes where those groups originated without applying a population denominator.

**Why it matters:** It reverses the city-first design and reveals the geographic concentration of the most popular selected acts. It also demonstrates that popularity-first selection measures successful output, not scene depth.

### 07. [Top-100 population-adjusted origins](07_uk_bands_top100_popularity_first_population_adjusted.ipynb)

**What it tests:** Adds OECD FUA population to the top-100 popularity-first catalogue and includes a minimum-two-band stability view.

**Why it matters:** It shows how a population denominator can elevate small places represented by one globally dominant act, making the difference between output per resident and a broad local scene explicit.

### 08. [Top-20 mirror of the final method](08_uk_bands_top20_fua_final_structure.ipynb)

**What it tests:** Applies the final notebook’s balanced ten-band method and largest-band-exclusion sensitivity to the twenty largest UK FUAs.

**Why it matters:** It is the cleanest scope extension of the final study. Because the method is held constant, differences from the top-ten result can be attributed to the broader geographic universe rather than a redesigned estimator.

### 09. [Canonical top-100 popularity-first FUA analysis](09_uk_bands_top100_popularity_first_fua.ipynb)

**What it tests:** Consolidates raw geographic concentration, strict FUA mapping, population-normalized output and multi-band stability for the top 100 selected groups.

**Why it matters:** It turns the earlier top-100 branches into one coherent analysis and makes the Crawley–The Cure case a clear example of a valid but single-band-dominated result.

### 10. [Canonical top-200 popularity-first FUA analysis](10_uk_bands_top200_popularity_first_fua.ipynb)

**What it tests:** Repeats the canonical popularity-first analysis with 200 groups and reviewed strict and extended origin mappings.

**Why it matters:** It tests whether the top-100 conclusions survive a broader catalogue and increases multi-band coverage without disguising areas whose rank still rests on one act.

## Phase 3 — output shares, scaling and geographic communication

### 11. [Top-200 output share versus population](11_uk_bands_top200_output_share_vs_population.ipynb)

**What it tests:** Reframes per-capita output as each FUA’s share of selected bands, followers and monthly listeners compared with its share of the complete 83-FUA population denominator.

**Why it matters:** The output quotient gives `1×` a clear proportional benchmark and keeps zero-output FUAs in the denominator, while showing that one-band results remain fragile.

### 12. [Top-1,000 output share versus population](12_uk_bands_top1000_output_share_vs_population.ipynb)

**What it tests:** Extends the share comparison to the first 1,000 eligible UK groups, mapping 660 of them to 61 FUAs and retaining all 83 FUAs in the population denominator.

**Why it matters:** The larger catalogue reduces dependence on a very small elite and provides the main descriptive foundation for later breadth, scaling, map and network experiments.

### 13. [Negative-binomial band-count scaling](13_uk_bands_top1000_negative_binomial_scaling.ipynb)

**What it tests:** Models mapped top-1,000 band counts as a function of FUA population with an NB2 log-link model, retaining all 83 FUAs including 22 with zero selected bands.

**Why it matters:** It provides the strongest model for scene breadth, handles overdispersed counts better than Poisson and identifies cities producing more selected bands than population alone predicts.

### 14. [Log–log follower scaling](14_uk_bands_top1000_loglog_follower_scaling.ipynb)

**What it tests:** Models summed Spotify followers against population for the 61 positive-output FUAs and checks HC3, Huber and leave-one-city-out sensitivity.

**Why it matters:** It addresses audience impact rather than band count and demonstrates both superlinear scaling and the instability caused by zero-output cities and superstar-dominated residuals.

### 15. [Top-1,000 follower maps](15_uk_bands_top1000_follower_maps.ipynb)

**What it tests:** Maps absolute follower totals, the leading selected band in each of the ten largest-output FUAs, and the population-relative follower output quotient.

**Why it matters:** It separates three ideas that league tables can blur: absolute reach, the identity and dominance of the leading act, and population-adjusted overperformance. Bubble area is proportional to the mapped quantity.

## Phase 4 — specification uncertainty and deeper mechanisms

### 16. [Specification multiverse](16_uk_bands_specification_multiverse.ipynb)

**What it tests:** Combines 32 defensible choices across catalogue design, catalogue size, Spotify metric, geographic mapping and scoring rule, then reports rank ranges and top-five frequencies.

**Why it matters:** It shows that the identity of the “winning” city depends materially on reasonable design choices. This is the strongest evidence that the published story should emphasize measurement uncertainty rather than one universal league table.

### 17. [Scene depth and concentration](17_uk_bands_scene_depth_and_concentration.ipynb)

**What it tests:** Measures inverse-Herfindahl effective-band counts, largest-band and top-three concentration, follower thresholds and population-adjusted output in the mapped top-1,000 catalogue.

**Why it matters:** It demonstrates that high output per resident and a deep multi-act scene are different phenomena: Crawley has the highest follower quotient but an effective-band count of one, while London has the broadest selected catalogue.

### 18. [Generations by decade](18_uk_bands_generations_by_decade.ipynb)

**What it tests:** Extracts MusicBrainz formation years for the balanced 200-band top-20 catalogue and audits coverage before attempting a generational comparison.

**Why it matters:** With only 54% year coverage and two FUAs with none, the notebook provides a useful negative result: the historical question is promising, but the available field is not yet adequate for a defensible city ranking.

### 19. [Genre-specific city histories](19_uk_bands_genre_city_histories.ipynb)

**What it tests:** Uses Wikidata genre and inception claims for the top 1,000, assigns fractional credit to multi-genre bands and compares broad genre families across formation decades and mapped FUAs.

**Why it matters:** It creates a feasible route toward historical and genre-specific studies while exposing the need for editorial review of automated genre families and formation dates.

### 20. [Scene infrastructure](20_uk_bands_scene_infrastructure.ipynb)

**What it tests:** Counts current OpenStreetMap music venues, nightclubs, arts centres, music shops, studios and universities within 15 km of twenty city centres, then compares the inventory with scene-depth measures.

**Why it matters:** Infrastructure aligns more strongly with scene scale than with per-capita overperformance, challenging the simple claim that present-day venue density explains musical success. The result is hypothesis-generating, not causal.

### 21. [Band networks](21_uk_bands_band_networks.ipynb)

**What it tests:** Links the 660 defensibly mapped top-1,000 bands through documented shared members and record labels, keeping the two edge types separate.

**Why it matters:** The much denser label network shows that network meaning depends on the relationship definition. Shared labels can describe national industry structure and should not be presented as local collaboration.

### 22. [Longitudinal platform reach](22_uk_bands_longitudinal_reach.ipynb)

**What it tests:** Compares the same 50 Spotify artist IDs between September 2025 and July 2026 using both followers and monthly listeners.

**Why it matters:** Followers behave like an accumulated stock while monthly listeners behave more like a volatile flow. The experiment motivates a future repeated-measures study but correctly avoids calling two observations a trend.

### 23. [Beyond-Spotify triangulation](23_uk_bands_beyond_spotify.ipynb)

**What it tests:** Compares Spotify followers with twelve months of English Wikipedia pageviews for the top 1,000 and examines descriptive log–log residuals.

**Why it matters:** The 0.78 rank correlation shows substantial overlap without equivalence. Wikipedia adds an independent attention measure and highlights cases that require identity, current-event and audience-context review rather than automatic interpretation as cultural impact.

## Source families

- **Spotify:** frozen artist-level monthly-listener and follower captures; each notebook records its exact snapshot and local input path.
- **Population and geography:** [OECD Functional Urban Area definition](https://www.oecd.org/en/data/datasets/oecd-definition-of-cities-and-functional-urban-areas.html), OECD FUA populations and the OECD municipality-to-FUA crosswalk.
- **Band identity and history:** [MusicBrainz](https://musicbrainz.org/) and [Wikidata](https://www.wikidata.org/) captures plus reviewed local overrides.
- **Infrastructure:** frozen [OpenStreetMap](https://www.openstreetmap.org/) Overpass responses.
- **Independent attention:** [Wikimedia Analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html) pageview captures for English Wikipedia articles.
- **Map assets:** frozen Natural Earth geography and locally stored Wikimedia Commons images with per-file attribution in experiment 15.

Generated figures and audit tables live under [`../../artifacts/experiments/`](../../artifacts/experiments/). Dated lineage, frozen inputs and rollback points are recorded in [`../../ANALYSIS_HISTORY.md`](../../ANALYSIS_HISTORY.md).
