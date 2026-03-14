# UK Cities Punching Above Their Weight

## Project status

This repository is being re-scoped around a narrower, more defensible question:

`Which UK cities punch above their population weight in producing globally popular bands?`

The earlier Google Trends notebooks remain as exploratory work, but they are not the primary analysis path for the main article.

## Decision log

### Agreed decisions

- Primary project question: `Which UK cities punch above their population weight in producing globally popular bands?`
- Google Trends is dropped as the main avenue of analysis.
- The project should support refreshing data before running the analysis.
- The final outcome should support both rigorous analysis and a later article.
- Inclusion scope: named `bands/groups` only.
- Duos are included if they are a named act that functions as a band.
- Solo artists are excluded.
- Editorial lane: stay close to the current shortlist and taste profile, centered on rock, indie, alternative, post-punk, new wave, pop-rock, and adjacent band-form acts.
- Electronic named acts are included when they are clearly group acts.
- Geographic unit: use `built-up area` rather than city proper or birthplace-level geography.
- Origin attribution rule: assign each band to the `built-up area where the band was formed or first became established`, with manual overrides for disputed or ambiguous cases.
- Metric stance: explore both `Spotify followers` and `monthly listeners`.
- City scoring plan: use `per-capita total popularity` as a main view, `top band per city` as a companion view, and `top 3 bands per city` as the preferred depth/sensitivity view.
- Inclusion threshold: yes, use a minimum popularity threshold so very small acts do not dilute city scores.
- Inclusion threshold should be configurable in code/workflow.
- Initial working default threshold: `100,000 Spotify followers`, subject to revision after inspecting the data distribution.
- Time scope: analyze the `current Spotify footprint of historically important eligible bands`, not only currently fashionable acts.
- London handling: include London in the main analysis, and also publish a sensitivity view excluding London.
- Dataset strategy: use a broader auto-collected catalogue with manual review for v1.
- Preserve the original hand-curated shortlist as part of the project record and later article narrative about initial intuition and selection bias.
- Publication stance: `rigorous-first with playful framing`.
- Ambiguous origin handling: keep bands in the dataset with a manual override and a note rather than excluding them by default.
- Dataset should explicitly track `origin_confidence`, `spotify_match_confidence`, and override notes/reasons.
- Bands that satisfy the formal inclusion rules should be included even if they sit outside the original taste lane.
- Add an informal editorial-review flag so out-of-lane but formally eligible bands can be reviewed separately for narrative framing.

### Open experiment-definition questions

1. Inclusion scope
- Which kinds of acts count for the study?
- Answered: UK `bands/groups` in the editorial lane suggested by the existing shortlist: rock, indie, alternative, new wave, post-punk, pop-rock, and adjacent named band formats.

2. Artist type boundary
- Do we include duos and electronic named acts if they function as bands?
- Do we exclude all solo artists without exception?
- Answered: yes to named duos that function as bands; yes, exclude solo artists.

### Rationale for excluding solo artists

- The analysis is intentionally about the output of `groups of minds`, not single star personalities.
- Band formation is part of the phenomenon being studied: scenes, collaboration, and local networks are more central to band creation than to solo celebrity careers.
- Excluding solo artists also avoids duplicate credit where a solo career follows an already-famous band career.
- This means the project is not trying to answer `which UK cities produce the biggest music stars overall`; it is answering a narrower and more coherent question about bands.

3. Geography unit
- What exact geographic unit should we use for "city"?
- Candidates: city proper, built-up area, metro area, combined authority area.
- Answered: `built-up area`.

4. Origin attribution rule
- How do we assign a band to a place?
- Candidates: place formed, most associated city, first common base, MusicBrainz origin with manual overrides.
- Answered: assign each band to the built-up area where the band was formed or first became established, with manual overrides.

5. Popularity metric
- What is the primary metric for "globally popular"?
- Candidates: Spotify monthly listeners, Spotify followers.
- Current answer: explore both metrics rather than collapsing immediately to one.

6. Secondary robustness metric
- What metric should be used as a check on the primary result?
- Current answer: also open because both followers and monthly listeners will be explored.

7. Inclusion threshold
- Should there be a minimum current popularity threshold for inclusion?
- Candidates: no threshold, minimum followers, minimum monthly listeners.
- Answered in principle: yes, a threshold should exist.
- Threshold basis: `Spotify followers`.
- Threshold level: make it configurable.
- Initial working default: `100,000 followers`, to be revisited after inspecting the distribution.

8. Time scope
- Is this analysis about current popularity only, or about historically important bands with current Spotify footprint?
- Answered: historically important eligible bands with current Spotify footprint.

9. City scoring method
- How should cities earn credit from their bands?
- Candidates: total monthly listeners, median monthly listeners, top-N listeners, per-capita total, per-capita top-N.
- Answered: use several views, centered on per-capita total popularity, top band per city, and top 3 bands per city.

10. London handling
- Should London be treated normally, or should we also publish a sensitivity view excluding London?
- Answered: include London normally, and also publish a view excluding London.

11. Dataset strategy
- Should v1 use a manually reviewed shortlist or attempt a broad auto-collected catalogue with review?
- Answered: broader auto-collected catalogue with manual review.
- Additional requirement: keep the original hand-curated list and use it later to discuss initial intuition and selection bias.

12. Publication stance
- What tone should the final article take?
- Candidates: playful with explicit caveats, rigorous-first with playful framing.
- Answered: rigorous-first with playful framing.

## Concrete tasks

### Definition and methodology

- [ ] Finalize inclusion criteria for eligible acts.
- [ ] Finalize the geographic unit and city standardization rules.
- [ ] Finalize the band-to-city attribution rule.
- [ ] Finalize the primary popularity metric.
- [ ] Finalize the robustness metric.
- [ ] Finalize the inclusion threshold and time scope.
- [ ] Finalize city-level scoring outputs for the article.
- [ ] Write a short methodology note suitable for reuse in the eventual article.

### Data model

- [ ] Create a canonical reviewed band metadata file.
- [ ] Create a standardized geography and population file.
- [ ] Define schemas for raw fetched data, reviewed matches, and analysis-ready outputs.
- [ ] Add timestamps/versioning rules for data snapshots.
- [ ] Add confidence and notes fields for disputed origin assignments and entity matches.
- [ ] Add an informal editorial-review flag for bands that are formally eligible but feel outside the original taste lane.

### Data collection

- [ ] Extract Spotify search and matching logic from notebooks into scripts/modules.
- [ ] Implement a refreshable Spotify ID resolution script.
- [ ] Implement a refreshable Spotify metrics fetch script.
- [ ] Add caching and timestamped raw snapshots.
- [ ] Add a review queue for low-confidence matches.

### Analysis

- [ ] Build a script that merges reviewed metadata, population, and latest Spotify metrics into one analysis dataset.
- [ ] Implement city ranking outputs using the chosen metrics.
- [ ] Add sensitivity analyses.
- [ ] Add chart generation for the final notebook/article.

### Repository cleanup

- [ ] Keep the Google Trends notebooks as exploratory dead ends with a short explanatory note.
- [ ] Refactor notebook logic so notebooks are presentation layers, not data pipelines.
- [ ] Expand the README with project purpose, workflow, and rerun instructions.

## Interview notes

This section will be updated with the user's answers so the repo contains a persistent record of analytical choices and editorial decisions for later writing.

### Interview round 1

- User confirmed the project should focus on named bands/groups only.
- User confirmed duos are allowed when they behave like a named act rather than a solo artist project.
- User confirmed the scope should stay close to the current taste/profile represented in the initial shortlist.
- Related note for later article framing: this choice intentionally excludes major solo artists that would otherwise loom large in a broad "UK music cities" analysis.
- User confirmed solo artists should stay excluded because the analysis is about collaborative groups rather than single personalities, and because solo careers can duplicate credit from prior bands.
- User confirmed electronic named acts should be included when they are clearly group acts.
- User selected `built-up area` as the geographic unit for city comparisons.
- User accepted the recommendation to assign bands to the built-up area where they were formed or first became established, with manual overrides when needed.
- User wants to explore both `Spotify followers` and `monthly listeners` rather than choosing only one upfront.
- User accepted a city scoring structure centered on per-capita total popularity, top band per city, and top 3 bands per city.
- User wants a minimum inclusion threshold so tiny acts do not add noise to city scores.
- User chose `Spotify followers` as the basis for the inclusion threshold.
- User wants the threshold level to remain configurable; `100,000 followers` is the current working default.
- User chose to study the current Spotify footprint of historically important eligible bands, not just currently fashionable acts.
- User wants London included in the main analysis, with a separate sensitivity view excluding London.
- User chose a broader auto-collected catalogue with manual review for v1.
- User explicitly wants to preserve the original shortlist as part of the project's narrative and selection-bias discussion.
- User wants the eventual article to be playful in tone while staying methodologically serious.
- User wants ambiguous origin cases kept via manual override rather than dropped.
- User wants explicit confidence fields for origin and Spotify matching decisions.
- User wants formally eligible bands included even if they fall outside the initial taste lane.
- User wants those cases flagged informally for later editorial review.

### Article notes

- The original hand-picked city/band list should not be deleted.
- It can serve as an opening narrative device: the project started from taste, memory, and intuition, then had to confront selection bias and methodology.

### Scoring notes

- `Top 3` was chosen instead of `top 5` because it captures depth beyond a single superstar without over-rewarding larger scenes with a longer tail of eligible acts.

### Metric notes for later article

- `Spotify followers` are more stable and come from Spotify's official API.
- `Monthly listeners` are closer to current reach, but are more volatile and require a third-party source in the current workflow.
- The project originally started from followers in the early notebook framing, then switched toward monthly listeners when trying to capture a more vivid current-reach story.
- A later article can use this as part of the narrative: the measurement question was itself part of the investigation.
