import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

import {
  AREA_BAND_LIMIT,
  PLACE_LEADERBOARD_LIMIT,
  rankedAreaBands,
  rankedBands,
  rankedPlaces,
} from "../src/bar-chart.js";
import { resolveAssetUrl } from "../src/data.js";
import {
  DEFAULT_MAP_ZOOM,
  MAP_LABEL_PLACE_IDS,
  markerRadius,
  placeMetricValue,
  pointInBounds,
  pointerPairGesture,
  rectangleBounds,
  sharedMetricMaximum,
} from "../src/map.js";
import { normalizeSearch, searchExplorer } from "../src/search.js";
import {
  DEFAULT_COMPARISON,
  DEFAULT_METRIC,
  parseExplorerState,
} from "../src/state.js";

const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dashboard = JSON.parse(
  await readFile(path.join(projectDir, "public/data/dashboard.json"), "utf8"),
);

test("search normalization ignores punctuation, whitespace, case, and diacritics", () => {
  assert.equal(normalizeSearch("  Mötley—Crüe!!!  "), "motley crue");
  const result = searchExplorer(dashboard.bands, dashboard.places, "imar");
  assert.equal(result[0].type, "band");
  assert.equal(result[0].band.name, "Ímar");
});

test("omnisearch ranks exact bands and places and labels both result types", () => {
  const london = searchExplorer(dashboard.bands, dashboard.places, "London");
  assert.equal(london[0].type, "place");
  assert.equal(london[0].place.id, "London");
  assert.ok(london.some((result) => result.type === "band"));

  const radiohead = searchExplorer(dashboard.bands, dashboard.places, "Radiohead");
  assert.equal(radiohead[0].type, "band");
  assert.equal(radiohead[0].band.name, "Radiohead");

  const oxfordFua = searchExplorer(dashboard.bands, dashboard.fuas, "Oxford");
  assert.equal(oxfordFua[0].type, "place");
  assert.equal(oxfordFua[0].place.placeType, "fua");
  assert.equal(oxfordFua[0].place.label, "Oxford");
});

test("omnisearch results are deterministic and capped", () => {
  const results = searchExplorer(dashboard.bands, dashboard.places, "the", 10);
  assert.equal(results.length, 10);
  assert.deepEqual(
    results,
    searchExplorer(dashboard.bands, dashboard.places, "the", 10),
  );
});

test("URL state defaults safely and lets a valid explicit place win", () => {
  assert.deepEqual(parseExplorerState("?band=bad&place=bad&metric=bad", dashboard), {
    selectedBandId: null,
    selectedOrigin: null,
    selectedFua: null,
    metric: "monthly_listeners",
    comparison: "raw",
  });
  const radiohead = dashboard.bands.find((band) => band.name === "Radiohead");
  assert.equal(
    parseExplorerState(`?band=${radiohead.id}`, dashboard).selectedOrigin,
    radiohead.originCluster,
  );
  assert.equal(
    parseExplorerState(
      `?band=${radiohead.id}&comparison=population_normalized`,
      dashboard,
    ).selectedFua,
    radiohead.fuaCode,
  );
  assert.equal(
    parseExplorerState(`?band=${radiohead.id}&place=Manchester&metric=followers`, dashboard)
      .selectedOrigin,
    "Manchester",
  );
  const manchesterFua = dashboard.fuas.find((fua) => fua.label === "Manchester");
  assert.equal(
    parseExplorerState(
      `?band=${radiohead.id}&fua=${manchesterFua.id}&comparison=population_normalized`,
      dashboard,
    ).selectedFua,
    manchesterFua.id,
  );
});

test("the explorer defaults to monthly listeners and raw totals", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  assert.equal(DEFAULT_METRIC, "monthly_listeners");
  assert.equal(DEFAULT_COMPARISON, "raw");
  assert.match(
    html,
    /data-metric="monthly_listeners" aria-pressed="true">Monthly listeners<\/button>/,
  );
  assert.match(
    html,
    /data-metric="followers" aria-pressed="false">Followers<\/button>/,
  );
  assert.match(html, /data-comparison="raw"[^>]+aria-label="Raw totals"[^>]+>Totals<\/button>/);
  assert.match(
    html,
    /data-comparison="population_normalized"[^>]+aria-label="Population-normalized"[^>]+>Normalized<\/button>/,
  );
});

test("metric bubbles grow with place totals and obsolete map state is ignored", async () => {
  const parsed = parseExplorerState("?map=equal", dashboard);
  const stateSource = await readFile(path.join(projectDir, "src/state.js"), "utf8");
  assert.equal("mapView" in parsed, false);
  assert.doesNotMatch(stateSource, /DEFAULT_MAP_VIEW|MAP_VIEWS|searchParams\.set\("map"/);
  const london = dashboard.places.find((place) => place.id === "London");
  const manchester = dashboard.places.find((place) => place.id === "Manchester");
  const sharedMaximum = sharedMetricMaximum(dashboard.places);
  for (const metric of ["monthly_listeners", "followers"]) {
    const londonValue = placeMetricValue(london, metric);
    const manchesterValue = placeMetricValue(manchester, metric);
    assert.ok(londonValue > manchesterValue);
    assert.ok(markerRadius(londonValue, sharedMaximum) > markerRadius(manchesterValue, sharedMaximum));
  }
  assert.ok(
    markerRadius(london.monthlyListenersTotal, sharedMaximum)
      > markerRadius(london.followersTotal, sharedMaximum),
  );
  assert.equal(markerRadius(sharedMaximum, sharedMaximum), 24);

  const normalizedMaximum = sharedMetricMaximum(
    dashboard.fuas,
    "population_normalized",
  );
  const normalizedValues = dashboard.fuas.map((fua) =>
    placeMetricValue(fua, "monthly_listeners", "population_normalized"),
  );
  assert.equal(
    normalizedValues[0],
    dashboard.fuas[0].monthlyListenersTotal / dashboard.fuas[0].population,
  );
  assert.ok(normalizedMaximum >= Math.max(...normalizedValues));
  assert.ok(
    markerRadius(Math.max(...normalizedValues), normalizedMaximum)
      > markerRadius(Math.min(...normalizedValues), normalizedMaximum),
  );
});

test("two-pointer gestures expose a stable midpoint and pinch distance", () => {
  assert.equal(pointerPairGesture([{ x: 1, y: 2 }]), null);
  assert.deepEqual(
    pointerPairGesture([{ x: 10, y: 20 }, { x: 30, y: 60 }]),
    { center: { x: 20, y: 40 }, distance: Math.hypot(20, 40) },
  );
});

test("rectangle geometry is direction-independent and includes boundary points", () => {
  const bounds = rectangleBounds({ x: 30, y: 50 }, { x: 10, y: 20 });
  assert.deepEqual(bounds, { minX: 10, maxX: 30, minY: 20, maxY: 50 });
  assert.equal(pointInBounds({ x: 10, y: 50 }, bounds), true);
  assert.equal(pointInBounds({ x: 31, y: 40 }, bounds), false);
});

test("the default and reset map view use the approved tighter UK crop", async () => {
  const mapSource = await readFile(path.join(projectDir, "src/map.js"), "utf8");
  assert.equal(DEFAULT_MAP_ZOOM, 1.35 ** 2);
  assert.match(mapSource, /const DEFAULT_TRANSLATE_X = \(WIDTH \* \(1 - DEFAULT_MAP_ZOOM\)\) \/ 2/);
  assert.match(mapSource, /const DEFAULT_TRANSLATE_Y = HEIGHT - \(HEIGHT - PADDING\) \* DEFAULT_MAP_ZOOM/);
  assert.match(mapSource, /this\.zoom = DEFAULT_MAP_ZOOM/);
  assert.match(mapSource, /reset\(\)[\s\S]+?this\.zoom = DEFAULT_MAP_ZOOM/);
  assert.match(mapSource, /zoomIn\(\)[\s\S]+?this\.zoomAt\(ZOOM_STEP\)/);
  assert.match(mapSource, /zoomOut\(\)[\s\S]+?this\.zoomAt\(1 \/ ZOOM_STEP\)/);
});

test("the omnibox is the only text control for selecting a place", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  assert.match(html, /<label class="visually-hidden" for="band-search">Search bands or formation places<\/label>/);
  assert.match(html, /id="band-search-clear"[^>]+aria-label="Clear search"[^>]+hidden/);
  assert.match(main, /function setSearchValue\(value\)/);
  assert.match(main, /elements\.searchClear\.hidden = !value/);
  assert.match(main, /elements\.searchClear\.addEventListener\("click", \(\) => \{/);
  assert.match(main, /setSearchValue\(""\);[\s\S]+?restartExplorer\(\);[\s\S]+?elements\.search\.focus\(\)/);
  assert.doesNotMatch(html, /place-select/);
  assert.doesNotMatch(main, /placeSelect/);
});

test("clearing the omnibox restarts band state without unselecting the place", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const stateSource = await readFile(path.join(projectDir, "src/state.js"), "utf8");
  assert.match(main, /function restartExplorer\(\)/);
  assert.match(main, /const selectedOrigin = placesById\.has\(state\.selectedOrigin\)/);
  assert.match(main, /const selectedFua = fuasById\.has\(state\.selectedFua\)/);
  assert.match(main, /const comparison = state\.comparison/);
  assert.match(main, /const defaultState = parseExplorerState\("", dashboard\)/);
  assert.match(main, /selectedOrigin: selectedOrigin \|\| defaultState\.selectedOrigin/);
  assert.match(main, /selectedFua: selectedFua \|\| defaultState\.selectedFua/);
  assert.match(main, /comparison,/);
  assert.match(main, /updateUrl\(state, "replace"\)/);
  assert.match(stateSource, /url\.search = ""/);
  assert.match(stateSource, /url\.searchParams\.set\("place", state\.selectedOrigin\)/);
  assert.match(stateSource, /url\.searchParams\.set\("fua", state\.selectedFua\)/);
  assert.match(stateSource, /window\.history\[method\]\(null, "", url\)/);
  assert.match(main, /map\.reset\(\)/);
  assert.match(
    main,
    /function updateSuggestions\(\)[\s\S]+?if \(!elements\.search\.value\.trim\(\)\) \{[\s\S]+?restartExplorer\(\);[\s\S]+?return;/,
  );
});

test("the map Reset control changes the viewport without clearing its place selection", async () => {
  const mapSource = await readFile(path.join(projectDir, "src/map.js"), "utf8");
  const resetBody = mapSource.match(/reset\(\) \{([\s\S]+?)\n  \}/)?.[1] || "";
  assert.match(resetBody, /this\.zoom = DEFAULT_MAP_ZOOM/);
  assert.match(resetBody, /this\.applyTransform\(\)/);
  assert.doesNotMatch(resetBody, /selectedPlace|setSelection/);
});

test("the selected formation place lives in the map header instead of the band card", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(html, /id="map-place-label"[^>]*>Formation place<\/p>/);
  assert.match(html, /id="map-place-title">United Kingdom<\/h2>/);
  assert.doesNotMatch(html, /Formation places in the catalog/);
  assert.match(main, /elements\.mapPlaceTitle\.textContent = place\.label/);
  assert.match(main, /place\.placeType === "region" \? "Formation region" : "Formation place"/);
  assert.match(main, /elements\.mapPlaceTitle\.textContent = "United Kingdom"/);
  assert.match(main, /return count;/);
  assert.doesNotMatch(main, /location-status|location\.textContent/);
  assert.match(styles, /\.card-header \.map-place-label[^}]+text-transform: uppercase/s);
  assert.doesNotMatch(styles, /\.location-status/);
});

test("production builds content-version browser code while keeping the data URL stable", async () => {
  const build = await readFile(path.join(projectDir, "scripts/build_frontend.mjs"), "utf8");
  const data = await readFile(path.join(projectDir, "src/data.js"), "utf8");
  assert.match(build, /createHash\("sha256"\)/);
  assert.match(build, /\?v=\$\{assetVersion\}/);
  assert.match(data, /DASHBOARD_DATA_URL = "\/data\/dashboard\.json"/);
  assert.doesNotMatch(data, /dashboard\.json\?v=/);
});

test("the interface uses the canonical Daniel Pradilla app-style primitives", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(styles, /--page: rgb\(255, 253, 249\)/);
  assert.match(
    styles,
    /font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif/,
  );
  assert.match(styles, /--warning: #7a6100/);
  assert.doesNotMatch(
    styles,
    /--(?:background|surface|surface-raised|text|faint|border|border-strong|blue-dark|gold|gold-soft|focus|radius):/,
  );
  assert.match(styles, /\.intro h1[^}]+font-weight: 300[^}]+letter-spacing: 0/s);
  assert.match(
    styles,
    /\.intro[^}]+grid-template-columns: minmax\(660px, 0\.96fr\) minmax\(420px, 1\.04fr\)/s,
  );
  assert.match(styles, /\.intro[^}]+align-items: start/s);
  assert.match(styles, /main[^}]+padding: 24px 0 48px/s);
  assert.match(styles, /\.intro[^}]+gap: 32px[^}]+margin-bottom: 18px/s);
  assert.match(styles, /\.intro h1[^}]+margin: 0 0 10px/s);
  assert.match(html, /Search the popularity-first catalog, map band origins, and compare frozen Spotify reach by place\./);
  assert.doesNotMatch(styles, /\.search-control label,/);
  assert.match(styles, /\.intro h1[^}]+white-space: nowrap/s);
  assert.match(
    styles,
    /@media \(max-width: 1200px\)[\s\S]+?\.intro h1\s*\{[^}]+white-space: normal/s,
  );
  assert.doesNotMatch(styles, /\bInter\b/);
  assert.doesNotMatch(styles, /letter-spacing: -/);
  assert.doesNotMatch(styles, /border-radius: 999/);
  assert.doesNotMatch(styles, /box-shadow:/);
});

test("the stylesheet keeps canonical tokens and consolidated responsive rules", async () => {
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(styles, /\.chart-header > \.chart-note[^}]+color: var\(--warning\)/s);
  assert.doesNotMatch(styles, /color:[^;]+!important/);
  assert.doesNotMatch(styles, /\.bar-row\.is-selected \.bar-fill/);
  assert.doesNotMatch(
    styles,
    /@media \(max-width: 470px\)[\s\S]+?\.map-frame\s*\{/,
  );
  assert.doesNotMatch(styles, /\.map-frame[^}]+min-height:/s);
});

test("the map follows the Daniel Pradilla geographic style guidance", async () => {
  const mapSource = await readFile(path.join(projectDir, "src/map.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(styles, /\.explorer-grid[^}]+align-items: start/s);
  assert.match(styles, /\.map-card[^}]+display: flex[^}]+flex-direction: column/s);
  assert.match(styles, /\.map-frame[^}]+flex: none[^}]+height: 540px/s);
  assert.match(
    styles,
    /@media \(max-width: 1050px\)[\s\S]+?\.explorer-grid\s*\{[^}]+display: flex;[^}]+flex-direction: column;[^}]+align-items: stretch;/,
  );
  assert.match(styles, /@media \(max-width: 1050px\)[\s\S]+?\.map-frame\s*\{[^}]+height: 600px;/);
  assert.match(styles, /@media \(max-width: 790px\)[\s\S]+?\.map-frame\s*\{[^}]+height: 480px;/);
  assert.doesNotMatch(styles, /\.map-frame[^}]+min-height:/s);
  assert.match(styles, /\.marker-dot[^}]+fill: var\(--secondary\)[^}]+stroke: var\(--paper\)/s);
  assert.match(styles, /\.map-tooltip[^}]+padding: 6px 8px[^}]+background: rgba\(255, 253, 249, 0\.96\)/s);
  assert.match(styles, /\.map-attribution[^}]+font-size: 0\.5rem[^}]+font-weight: 300/s);
  assert.match(styles, /\.uk-map[^}]+touch-action: none/s);
  assert.match(mapSource, /currentGesture\.distance \/ previousGesture\.distance/);
  assert.match(mapSource, /point\.matrixTransform\(this\.svg\.getScreenCTM\(\)\.inverse\(\)\)/);
  assert.doesNotMatch(styles, /\.detail-card\s*\{[^}]+order: -1/s);
});

test("the map provides restrained orientation labels and labels the selection", async () => {
  const mapSource = await readFile(path.join(projectDir, "src/map.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.deepEqual(MAP_LABEL_PLACE_IDS, [
    "London",
    "Manchester",
    "Liverpool",
    "Birmingham",
    "Glasgow",
    "Edinburgh",
    "Cardiff",
    "Belfast",
  ]);
  MAP_LABEL_PLACE_IDS.forEach((placeId) => {
    const place = dashboard.places.find((candidate) => candidate.id === placeId);
    assert.equal(place?.locationStatus, "uk");
    assert.equal(place?.placeType, "locality");
  });
  assert.match(mapSource, /group\.classList\.toggle\("is-selected", id === placeId\)/);
  assert.match(mapSource, /MAP_LABEL_FONT_SIZE = 8\.5/);
  assert.match(mapSource, /text\.style\.fontSize = `\$\{MAP_LABEL_FONT_SIZE \/ this\.zoom\}px`/);
  assert.match(styles, /\.map-city-label\.is-base,[\s\S]+\.map-city-label\.is-selected[^}]+display: block/s);
  assert.match(styles, /\.map-city-label text[^}]+font-size: 8\.5px[^}]+paint-order: stroke/s);
  assert.match(styles, /\.map-city-label[^}]+pointer-events: none/s);
});

test("an unresolved band does not receive a fallback map place", () => {
  const unresolved = dashboard.bands.find((band) => band.locationStatus === "unresolved");
  const parsed = parseExplorerState(`?band=${unresolved.id}`, dashboard);
  assert.equal(parsed.selectedBandId, unresolved.id);
  assert.equal(parsed.selectedOrigin, null);
});

test("a selected band below the leading ten is appended with its true rank", () => {
  const londonBands = dashboard.bands
    .filter((band) => band.originCluster === "London")
    .sort((a, b) => a.placeRankMonthlyListeners - b.placeRankMonthlyListeners);
  const selected = londonBands.find((band) => band.placeRankMonthlyListeners > 10);
  const rows = rankedBands(
    dashboard.bands,
    "London",
    "monthly_listeners",
    selected.id,
  );
  assert.equal(rows.length, 11);
  assert.equal(rows.at(-1).band.id, selected.id);
  assert.equal(rows.at(-1).comparison, true);
  assert.equal(rows.at(-1).band.placeRankMonthlyListeners, selected.placeRankMonthlyListeners);
});

test("the initial overview ranks 10 raw places or normalized FUAs by the active metric", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const monthly = rankedPlaces(dashboard.places, "monthly_listeners", "raw");
  const followers = rankedPlaces(dashboard.places, "followers", "raw");
  const normalized = rankedPlaces(
    dashboard.fuas,
    "monthly_listeners",
    "population_normalized",
  );
  assert.equal(PLACE_LEADERBOARD_LIMIT, 10);
  assert.equal(monthly.length, PLACE_LEADERBOARD_LIMIT);
  assert.equal(followers.length, PLACE_LEADERBOARD_LIMIT);
  assert.ok(monthly.every((place) => place.locationStatus === "uk" && place.placeType === "locality"));
  assert.ok(monthly.every((place, index) => index === 0 || monthly[index - 1].monthlyListenersTotal >= place.monthlyListenersTotal));
  assert.ok(followers.every((place, index) => index === 0 || followers[index - 1].followersTotal >= place.followersTotal));
  assert.equal(normalized.length, PLACE_LEADERBOARD_LIMIT);
  assert.ok(normalized.every((place) => place.placeType === "fua" && place.population > 0));
  assert.ok(normalized.every((place, index) =>
    index === 0
    || normalized[index - 1].monthlyListenersPerResident >= place.monthlyListenersPerResident,
  ));
  assert.match(main, /const geographyLabel = isPopulationNormalized\(\) \? "FUAs" : "formation places"/);
  assert.match(main, /`Top \$\{PLACE_LEADERBOARD_LIMIT\} \$\{geographyLabel\} — \$\{metricLabel\}`/);
  assert.match(main, /renderPlaceChart\([\s\S]+?places,[\s\S]+?state\.metric,[\s\S]+?state\.comparison/);
});

test("activating the selected city again returns to the unselected overview", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  assert.match(main, /function clearPlaceSelection\(source = "push"\)/);
  assert.match(main, /state\.selectedBandId = null;[\s\S]+?state\.selectedOrigin = null/);
  assert.match(main, /setSearchValue\(""\)/);
  assert.match(main, /map\.reset\(\);[\s\S]+?render\(false\)/);
  assert.match(
    main,
    /function selectPlace\([\s\S]+?const stateField = normalized \? "selectedFua" : "selectedOrigin";[\s\S]+?if \(state\[stateField\] === placeId\) \{[\s\S]+?clearPlaceSelection\(source\);[\s\S]+?return;/,
  );
});

test("a rectangular map selection ranks its top ten bands by the active metric", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const mapSource = await readFile(path.join(projectDir, "src/map.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  const placeIds = ["London", "Manchester", "Liverpool"];
  const rows = rankedAreaBands(dashboard.bands, placeIds, "monthly_listeners", "raw", dashboard.places);
  assert.equal(AREA_BAND_LIMIT, 10);
  assert.equal(rows.length, 10);
  assert.ok(rows.every((band) => placeIds.includes(band.originCluster)));
  assert.ok(rows.every((band, index) => index === 0 || rows[index - 1].monthlyListeners >= band.monthlyListeners));
  assert.match(html, /id="map-select-area"[^>]+aria-pressed="false">Area<\/button>/);
  assert.match(main, /selectedAreaPlaceIds = placeIds/);
  assert.match(main, /Top 10 bands in selected area — \$\{metricLabel\}/);
  assert.match(main, /renderAreaBandChart\(/);
  assert.match(mapSource, /completeAreaSelection\(\)/);
  assert.match(mapSource, /pointInBounds\(marker, bounds\)/);
  assert.match(styles, /\.map-area-selection[^}]+stroke: var\(--blue\)/s);
  assert.match(styles, /\.map-marker\.is-area-selected \.marker-dot/);

  const fuaIds = dashboard.fuas.slice(0, 3).map((fua) => fua.id);
  const normalizedRows = rankedAreaBands(
    dashboard.bands,
    fuaIds,
    "monthly_listeners",
    "population_normalized",
    dashboard.fuas,
  );
  assert.ok(normalizedRows.every((band) => fuaIds.includes(band.fuaCode)));
});

test("the dense ten-row leaderboard is integrated beneath band information", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const chartSource = await readFile(path.join(projectDir, "src/bar-chart.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(
    html,
    /<aside class="detail-card">[\s\S]+id="band-detail"[\s\S]+class="chart-section"[\s\S]+<\/aside>/,
  );
  assert.doesNotMatch(html, /id="band-links"/);
  assert.match(chartSource, /LEADERBOARD_LIMIT = 10/);
  assert.match(chartSource, /identity\.append\(name, selected\)/);
  assert.match(styles, /\.chart-section[^}]+border-top: 1px solid var\(--rule\)/s);
  assert.match(styles, /\.bar-list[^}]+grid-template-columns: 1fr/s);
  assert.match(styles, /\.bar-button[^}]+grid-template-rows: auto 5px[^}]+min-height: 34px/s);
  assert.doesNotMatch(styles, /\.external-links[^}]+margin-top: auto/s);
});

test("map controls and band links use the compact integrated layout", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.doesNotMatch(html, /class="explorer-controls"/);
  assert.match(
    html,
    /class="map-header-tools">[\s\S]+class="metric-toggle"/,
  );
  assert.doesNotMatch(html, /map-view-toggle|data-map-view|Equal markers|Metric bubbles/);
  assert.doesNotMatch(main, /mapView|renderMapViewToggle|setView|data-map-view/);
  assert.doesNotMatch(styles, /map-view-toggle|map-view-buttons|is-bubble-view/);
  assert.match(
    html,
    /id="map" class="map-frame">\s*<div class="map-controls" aria-label="Map controls">/,
  );
  assert.match(
    styles,
    /\.map-controls\s*\{[^}]+position: absolute;[^}]+top: 12px;[^}]+right: 12px;[^}]+z-index: 6;/s,
  );
  assert.doesNotMatch(main, /detailLinks|external-arrow/);
  assert.match(main, /links\.className = "external-links"/);
  assert.match(main, /header\.append\(title, headerMeta\)/);
  assert.match(main, /link\.dataset\.label = label/);
  assert.match(styles, /\.external-link::after[^}]+content: attr\(data-label\)/s);
  assert.match(styles, /\.external-link:hover::after,[\s\S]+\.external-link:focus-visible::after/);
});

test("the narrow map header keeps compact comparison and metric selectors while controls stay overlaid", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(html, /<div class="map-heading">[\s\S]+id="map-place-title"/);
  assert.match(
    styles,
    /@media \(max-width: 790px\)[\s\S]+?\.card-header\s*\{[^}]+position: relative;[^}]+display: block;/,
  );
  assert.match(
    styles,
    /@media \(max-width: 790px\)[\s\S]+?\.map-header-tools\s*\{[^}]+display: flex;[^}]+width: auto;[^}]+margin: 8px 0 0 auto;/,
  );
  assert.doesNotMatch(styles, /@media \(max-width: 790px\)[\s\S]+?\.map-controls\s*\{/);
  assert.doesNotMatch(styles, /\.map-heading[^}]+padding-right:/s);
  assert.match(
    styles,
    /@media \(max-width: 470px\)[\s\S]+?\.map-header-tools\s*\{[^}]+display: grid;[^}]+width: 100%;/,
  );
});

test("the desktop map and band-title dividers share one alignment line", async () => {
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(styles, /\.explorer-grid[^}]+--workspace-header-height: 120px/s);
  assert.match(styles, /\.card-header[^}]+min-height: var\(--workspace-header-height\)/s);
  assert.match(
    styles,
    /\.detail-header[^}]+min-height: calc\(var\(--workspace-header-height\) - 18px\)/s,
  );
  assert.match(
    styles,
    /@media \(max-width: 1050px\)[\s\S]+?\.card-header,[\s\S]+?\.detail-header\s*\{[^}]+min-height: 0/s,
  );
});

test("the explorer opens directly on the working surface without top navigation", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.doesNotMatch(html, /class="site-header"|class="header-inner"|class="project-mark"|class="method-link"/);
  assert.doesNotMatch(styles, /\.site-header|\.header-inner|\.project-mark|\.method-link/);
  assert.match(html, /<main id="explorer-main">\s*<section class="intro"/);
  assert.match(html, /Read the post ↗/);
});

test("band detail keeps catalog rank beneath the links and exposes only supported Spotify metrics", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.match(main, /metric\("Monthly listeners"/);
  assert.match(main, /metric\("Followers"/);
  assert.doesNotMatch(main, /metric\("Catalog rank"/);
  assert.match(main, /rank\.className = "catalog-rank"/);
  assert.match(main, /rankLabel\.textContent = "Catalog rank"/);
  assert.match(main, /headerMeta\.append\(links, rank\)/);
  assert.doesNotMatch(main, /Spotify world rank|band\.worldRank/);
  assert.ok(dashboard.bands.every((band) => !("worldRank" in band)));
  assert.match(styles, /\.detail-header-meta[^}]+justify-items: end[^}]+gap: 8px/s);
  assert.match(styles, /\.catalog-rank dd[^}]+font-variant-numeric: tabular-nums/s);
  assert.doesNotMatch(styles, /\.metric:last-child:nth-child\(odd\)/);
  assert.match(styles, /\.metrics-grid[^}]+margin: 0/s);
  assert.match(styles, /\.metric[^}]+padding: 13px 8px 15px 0/s);
});

test("genre enrichment remains packaged but is not rendered", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  const builder = await readFile(path.join(projectDir, "scripts/build_dashboard_data.py"), "utf8");
  assert.ok(dashboard.bands.some((band) => band.genres.length));
  assert.ok(dashboard.bands.some((band) => band.genreFamilies.length));
  assert.equal(dashboard.meta.bandsWithGenre, 928);
  assert.doesNotMatch(main, /renderGenres|band\.genres|genre available/);
  assert.doesNotMatch(styles, /\.genre-|\.unavailable/);
  assert.doesNotMatch(html, /Missing locations and genres/);
  assert.match(main, /genres: "Wikipedia titles \(Wikidata\)"/);
  assert.match(builder, /"label": "English Wikipedia titles \(Wikidata\)"/);
});

test("snapshot freshness is not repeated inside the band card", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const styles = await readFile(path.join(projectDir, "src/styles.css"), "utf8");
  assert.doesNotMatch(main, /snapshot\.className = "snapshot-date"/);
  assert.doesNotMatch(main, /band\.spotifyExtractedAtUtc/);
  assert.doesNotMatch(html, /id="chart-subtitle"/);
  assert.doesNotMatch(main, /chartSubtitle/);
  assert.doesNotMatch(styles, /\.snapshot-date/);
  assert.match(main, /elements\.footerProvenance\.textContent = `Snapshot \$\{dashboard\.meta\.snapshotId\}/);
});

test("leaderboard titles combine the active geography, comparison, and metric", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  assert.match(
    main,
    /elements\.chartTitle\.textContent = `Bands from \$\{placeLabel\} — \$\{metricLabel\}`/,
  );
  assert.match(main, /elements\.chartTitle\.textContent = `Top \$\{PLACE_LEADERBOARD_LIMIT\} \$\{geographyLabel\} — \$\{metricLabel\}`/);
  assert.match(main, /\? `Normalized \$\{config\.label\.toLowerCase\(\)\}`/);
  assert.doesNotMatch(main, /Leading bands from/);
});

test("the packaged population-normalized view uses strict FUA assignments", () => {
  assert.equal(dashboard.schemaVersion, 3);
  assert.equal(dashboard.fuas.length, dashboard.meta.strictFuaCount);
  assert.equal(dashboard.meta.strictFuaMappedBands, 663);
  assert.equal(dashboard.meta.fuaPopulationYear, 2024);
  assert.ok(dashboard.meta.strictFuaMonthlyListenerShare > 0.9);
  const fuaIds = new Set(dashboard.fuas.map((fua) => fua.id));
  assert.equal(fuaIds.size, dashboard.fuas.length);
  dashboard.fuas.forEach((fua) => {
    assert.ok(fua.population > 0);
    assert.equal(fua.populationYear, 2024);
    assert.equal(fua.monthlyListenersPerResident, fua.monthlyListenersTotal / fua.population);
    assert.equal(fua.followersPerResident, fua.followersTotal / fua.population);
  });
  dashboard.bands.forEach((band) => {
    if (band.fuaCode) assert.ok(fuaIds.has(band.fuaCode));
  });
});

test("mapped, outside-UK, region, and unresolved states are packaged", () => {
  const statuses = new Set(dashboard.bands.map((band) => band.locationStatus));
  assert.deepEqual(statuses, new Set(["uk", "outside_uk", "unresolved"]));
  assert.ok(dashboard.bands.some((band) => band.placeType === "region"));
  assert.ok(
    dashboard.bands
      .filter((band) => band.locationStatus === "outside_uk")
      .every((band) => band.latitude === null && band.longitude === null),
  );
});

test("frontend provenance has no timestamp fallback literals", async () => {
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const data = await readFile(path.join(projectDir, "src/data.js"), "utf8");
  assert.match(data, /DASHBOARD_DATA_URL = "\/data\/dashboard\.json"/);
  assert.doesNotMatch(data, /\.csv/);
  assert.doesNotMatch(main, /20260718T204522Z/);
  assert.doesNotMatch(main, /popularity_first_top1000_\d+/);
  assert.match(main, /dashboard\.meta\.freshness/);
  assert.match(main, /dashboard\.meta\.sourceFilename/);
});

test("project links target the published post and canonical master branch", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const main = await readFile(path.join(projectDir, "src/main.js"), "utf8");
  const explorerReadme = await readFile(path.join(projectDir, "README.md"), "utf8");
  const post = await readFile(path.join(projectDir, "../POST.md"), "utf8");
  for (const source of [html, main, explorerReadme, post]) {
    assert.doesNotMatch(source, /github\.com\/danielpradilla\/uk-music-cities\/blob\/main\//);
  }
  assert.match(
    html,
    /https:\/\/www\.danielpradilla\.info\/blog\/which-british-music-city-punches-furthest-above-its-weight\//,
  );
  assert.match(html, />Read the post ↗<\/a>/);
  assert.match(explorerReadme, /\[main study methodology\]\(\.\.\/README\.md#study-design\)/);
  assert.match(main, /uk-music-cities\/blob\/master\//);
  assert.match(post, /uk-music-cities\/blob\/master\/notebooks\//);
});

test("explorer uses the project-aligned public title", async () => {
  const html = await readFile(path.join(projectDir, "index.html"), "utf8");
  const explorerReadme = await readFile(path.join(projectDir, "README.md"), "utf8");
  assert.match(html, /<title>UK Music Cities Explorer<\/title>/);
  assert.match(html, /<h1 id="page-title">UK Music Cities Explorer<\/h1>/);
  assert.match(explorerReadme, /^# UK Music Cities Explorer/m);
  const formerTitle = ["UK", "Band", "Origins", "Explorer"].join(" ");
  assert.doesNotMatch(html, new RegExp(formerTitle));
});

test("stable packaged URLs resolve beneath a deployment base path", () => {
  assert.equal(resolveAssetUrl("/data/dashboard.json"), "/data/dashboard.json");
  assert.equal(
    resolveAssetUrl("/data/dashboard.json", "/uk-music-cities/"),
    "/uk-music-cities/data/dashboard.json",
  );
});
