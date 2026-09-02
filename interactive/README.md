# UK Band Origins Explorer

Static explorer for the popularity-first top-1,000 band catalog. It switches between raw totals for reviewed `origin_cluster` assignments and population-normalized results for strict FUA mappings. It does not use the balanced final-study 100-band dataset.

For the formal study's definitions of Functional Urban Areas, band assignment, Spotify reach, population normalization, and analytical limitations, see the [main study methodology](../README.md#study-design). The sections below document where this larger explorer intentionally differs.

## Requirements

- Python 3.10 or newer
- Node.js 20 or newer
- No npm packages or runtime APIs

## Build and test

From `interactive/`:

```sh
npm run build:data
npm test
npm run build
```

`npm run check` runs all three steps. The production output is `interactive/dist/`. To preview it locally:

```sh
npm run preview
```

The app’s canonical browser pointers remain `/data/dashboard.json` and `/data/uk-outline.geojson`. The production build can prefix those stable paths for a subdirectory deployment without changing the source pointers:

```sh
PUBLIC_BASE=/uk-music-cities npm run build
```

`npm run build:deploy` is the configured equivalent for `danielpradilla.info/uk-music-cities/`.

Run the repository’s Python suite from the repository root:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## Canonical catalog promotion

The explorer imports `POPULARITY_FIRST_TOP1000_BANDS_PATH` and `POPULARITY_FIRST_SNAPSHOT_ID` from `src/python_uk_bands/config.py`. To promote a catalog snapshot:

1. Review and preserve the new timestamped top-1,000 CSV.
2. Change `POPULARITY_FIRST_SNAPSHOT_ID` deliberately in `config.py`.
3. Run `npm run build:data` and review `public/data/dashboard.validation.json`.
4. Run `npm run check` and the repository test suite.

Do not create a `current` CSV, symlink, manifest, or newest-file selection rule.

## Explorer-only inputs

Timestamped enrichment inputs are declared once near the top of `scripts/build_dashboard_data.py`:

- genre and captured English Wikipedia title audit;
- Wikidata capture used to date that audit;
- reviewed origin-coordinate capture;
- strict reviewed formation-place/FUA mapping;
- Natural Earth UK outline.

Move a path to shared project configuration only if another study or tool begins using that pointer.

## Coordinate review

`data/origin_coordinates_20260902.csv` contains one record for every resolved `origin_cluster`: 214 UK points and six outside-UK locations. The capture is immutable and was created from reviewed formation QIDs in the canonical catalog using `scripts/capture_origin_coordinates.py` and the official Wikidata API.

UK coordinates are representative formation-place points rather than formation addresses. County, constituent-country, and other coarse assignments use `place_type=region`. Outside-UK records have `location_status=outside_uk` and deliberately blank coordinates. To add or correct a location, review the source QID, create a new timestamped capture, change the one coordinate pointer in the builder, then rebuild and validate.

## Map and visual treatment

The map uses the bundled Natural Earth outline, a fitted Mercator projection, and local SVG metric bubbles. It defaults to `Totals` and monthly listeners; followers remain an optional metric. `Normalized` switches the entire geography to strict OECD FUA assignments and divides each FUA's catalog total by its 2024 population. Formation places and FUAs are linked, but they are not identical: an FUA combines a city with its commuting zone and can contain several formation places. The band card always keeps the raw artist counts. The normalized number is a comparative index of global Spotify reach, not a local listening rate.

Raw mode covers all 749 resolved catalog bands and displays exact formation-place markers. The strict FUA mode covers 663 bands across 59 FUAs, representing 90.7% of the catalog's monthly-listener reach; unmapped bands remain searchable and are explicitly excluded rather than assigned by guesswork. Search results, overview rankings, band leaderboards, area selections, map bubbles, legends, tooltips, and shareable URL state all follow the active comparison. The unselected view ranks the top 10 formation places or FUAs. Clearing the omnibox preserves the selected active geography and comparison while resetting the metric and map crop. The map's Reset button is viewport-only.

There is no separate equal-marker mode or map-view URL state. The app makes no runtime tile, geocoding, tracking, or authentication request. Active-geography results in the omnibox are the keyboard and text equivalent of marker selection, so there is no separate place selector.

The map also follows `danielpradilla-app-style/references/maps.md`: quiet neutral geography, restrained square-root bubbles, blue focal selection, compact header controls, off-white square tooltips, and small metadata. The bundled Natural Earth asset contains outline geometry but no place-name layer, so eight subdued labels use the catalog's reviewed formation-place coordinates; the selected formation place is always labeled. Their effective CSS size is held at 8.5 px while zooming. The map uses an independent height—540 px on wide desktop, 600 px in the stacked tablet layout at 1,050 px and below, and 480 px at 790 px and below—so the primary wide-screen workspace fits above the fold without returning to automatic card stretching. The bundled outline intentionally takes precedence over the guide's default Stadia Outdoors tiles because this explorer requires a local, resilient, no-runtime-request basemap.

The default and Reset views use the approved tighter `1.35²×` crop. It centres the country horizontally and shifts the fitted outline upward, keeping the dense central and southern formation-place field prominent while deliberately clipping northern Scotland. Selecting a band or formation place can still focus more closely on its reviewed origin.

Zoom, Reset, and the compact `Area` control are overlaid at the map's top-right perimeter; the comparison and Spotify-metric selectors remain in the header. `Area` arms a one-shot pointer or touch drag. The resulting projected rectangle remains anchored while the map moves, highlights every included active geography, and ranks the top ten catalog bands across those geographies for the active metric and comparison. Selecting a result opens its normal band/geography view; `Clear` returns to the active top-10 overview. Rectangle state is intentionally session-only rather than encoded in the URL.

The formation-place comparison is a dense ten-row ranked leaderboard integrated beneath the selected band information. It keeps exact zero-based proportional bars and appends the selected band as an eleventh comparison row when its true place rank is below ten. This uses the detail panel's available space and removes the separate full-width chart section.

Production builds derive a short content hash from the HTML and browser source. The build appends that version to local CSS and JavaScript requests, including ES-module imports, so a deployment cannot combine new HTML with month-cached executable code. The canonical dashboard continues to load through the stable `/data/dashboard.json` URL.

The interface follows the canonical `danielpradilla-app-style` sources at `/Users/dpradilla/agentic-skills/danielpradilla-app-style/` and `/Users/dpradilla/dev/danielpradilla-app-style/`: off-white page and paper surfaces, direct canonical token names, the prescribed system sans stack and light weights, zero negative tracking, hairline rules, square controls and panels, no decorative elevation, restrained blue selection, compact data displays, and visible focus states. Circular map marks remain circular because their shape encodes quantitative geography rather than general component styling.

## Link icons

Spotify and Wikipedia links are deterministic, open in a new tab, and use local SVG marks beside the band name. They have accessible names and reveal their labels on hover or keyboard focus. Asset provenance and licence notes are in `public/icons/README.md`. Wikipedia links exist only for captured `enwiki_title` values; the browser never searches or guesses a page.
