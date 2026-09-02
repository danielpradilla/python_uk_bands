import { assetUrl, loadExplorerData } from "./data.js";
import { BandMap } from "./map.js";
import {
  METRIC_CONFIG,
  PLACE_LEADERBOARD_LIMIT,
  renderAreaBandChart,
  renderBarChart,
  renderPlaceChart,
} from "./bar-chart.js";
import { searchExplorer } from "./search.js";
import { parseExplorerState, updateUrl } from "./state.js";

const numberFormat = new Intl.NumberFormat("en-GB");
const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});
const REPOSITORY_BASE = "https://github.com/danielpradilla/uk-music-cities/blob/main/";

const elements = {
  app: document.querySelector("#app"),
  loading: document.querySelector("#loading"),
  error: document.querySelector("#error"),
  search: document.querySelector("#band-search"),
  searchClear: document.querySelector("#band-search-clear"),
  searchResults: document.querySelector("#band-search-results"),
  searchStatus: document.querySelector("#band-search-status"),
  detail: document.querySelector("#band-detail"),
  map: document.querySelector("#map"),
  mapPlaceLabel: document.querySelector("#map-place-label"),
  mapPlaceTitle: document.querySelector("#map-place-title"),
  mapStatus: document.querySelector("#map-status"),
  mapSelectArea: document.querySelector("#map-select-area"),
  chart: document.querySelector("#bar-chart"),
  chartTitle: document.querySelector("#chart-title"),
  chartNote: document.querySelector("#chart-note"),
  footerFreshness: document.querySelector("#footer-freshness"),
  footerCoverage: document.querySelector("#footer-coverage"),
  footerProvenance: document.querySelector("#footer-provenance"),
  footerSources: document.querySelector("#footer-sources"),
};

let dashboard;
let bandsById;
let placesById;
let fuasById;
let state;
let map;
let suggestions = [];
let activeSuggestion = -1;
let selectedAreaPlaceIds = null;

function formattedDate(value) {
  return dateFormat.format(new Date(value));
}

function metricButton(metric) {
  return document.querySelector(`[data-metric="${metric}"]`);
}

function comparisonButton(comparison) {
  return document.querySelector(`[data-comparison="${comparison}"]`);
}

function isPopulationNormalized() {
  return state.comparison === "population_normalized";
}

function activeGeographies() {
  return isPopulationNormalized() ? dashboard.fuas : dashboard.places;
}

function selectedGeography() {
  return isPopulationNormalized()
    ? fuasById.get(state.selectedFua)
    : placesById.get(state.selectedOrigin);
}

function matchingFormationPlace(fuaId) {
  const fua = fuasById.get(fuaId);
  if (!fua) return null;
  const place = placesById.get(fua.label);
  return place?.fuaCode === fua.id ? place.id : null;
}

function setSearchValue(value) {
  elements.search.value = value;
  elements.searchClear.hidden = !value;
}

function selectBand(bandId, source = "push") {
  const band = bandsById.get(bandId);
  if (!band) return;
  clearAreaFilter(false);
  state.selectedBandId = band.id;
  state.selectedOrigin = band.originCluster || null;
  state.selectedFua = band.fuaCode || null;
  setSearchValue(band.name);
  closeSuggestions();
  updateUrl(state, source);
  render(true);
}

function clearPlaceSelection(source = "push") {
  clearAreaFilter(false);
  state.selectedBandId = null;
  state.selectedOrigin = null;
  state.selectedFua = null;
  setSearchValue("");
  closeSuggestions();
  updateUrl(state, source);
  map.reset();
  render(false);
}

function selectPlace(placeId, source = "push", focusMap = true) {
  const normalized = isPopulationNormalized();
  const geographiesById = normalized ? fuasById : placesById;
  const stateField = normalized ? "selectedFua" : "selectedOrigin";
  if (!geographiesById.has(placeId)) return;
  if (state[stateField] === placeId) {
    clearPlaceSelection(source);
    return;
  }
  clearAreaFilter(false);
  state[stateField] = placeId;
  if (!state.selectedBandId) {
    if (normalized) state.selectedOrigin = matchingFormationPlace(placeId);
    else state.selectedFua = placesById.get(placeId)?.fuaCode || null;
  }
  updateUrl(state, source);
  render(focusMap);
}

function renderAreaControl() {
  const hasArea = selectedAreaPlaceIds !== null;
  const isSelecting = map?.areaSelectionMode || false;
  elements.mapSelectArea.textContent = hasArea ? "Clear" : isSelecting ? "Cancel" : "Area";
  elements.mapSelectArea.setAttribute("aria-pressed", String(hasArea || isSelecting));
  elements.mapSelectArea.setAttribute(
    "aria-label",
    hasArea
      ? "Clear rectangular map area"
      : isSelecting
        ? "Cancel rectangular map area selection"
        : "Select a rectangular map area",
  );
}

function clearAreaFilter(renderOverview = true) {
  selectedAreaPlaceIds = null;
  map?.clearAreaSelection();
  renderAreaControl();
  if (!renderOverview) return;
  state.selectedBandId = null;
  state.selectedOrigin = null;
  state.selectedFua = null;
  setSearchValue("");
  closeSuggestions();
  updateUrl(state, "push");
  render(false);
}

function selectArea(placeIds) {
  selectedAreaPlaceIds = placeIds;
  state.selectedBandId = null;
  state.selectedOrigin = null;
  state.selectedFua = null;
  setSearchValue("");
  closeSuggestions();
  updateUrl(state, "push");
  render(false);
}

function selectSearchPlace(placeId) {
  const place = (isPopulationNormalized() ? fuasById : placesById).get(placeId);
  if (!place) return;
  clearAreaFilter(false);
  state.selectedBandId = null;
  if (isPopulationNormalized()) {
    state.selectedFua = place.id;
    state.selectedOrigin = matchingFormationPlace(place.id);
  } else {
    state.selectedOrigin = place.id;
    state.selectedFua = place.fuaCode || null;
  }
  setSearchValue(place.label);
  closeSuggestions();
  updateUrl(state, "push");
  render(true);
}

function contextForBand(band) {
  if (isPopulationNormalized()) {
    const fua = fuasById.get(band.fuaCode);
    return fua ? `${fua.label} FUA` : "No strict FUA mapping";
  }
  if (band.locationStatus === "outside_uk") return `${band.originCluster} · Outside UK map`;
  if (band.locationStatus === "unresolved") return "Location unavailable";
  return band.originCluster;
}

function contextForPlace(place) {
  if (place.placeType === "fua") {
    return `${numberFormat.format(place.bandCount)} mapped catalog ${place.bandCount === 1 ? "band" : "bands"} · ${numberFormat.format(place.population)} residents`;
  }
  const count = `${numberFormat.format(place.bandCount)} catalog ${place.bandCount === 1 ? "band" : "bands"}`;
  if (place.locationStatus === "outside_uk") return `${count} · Outside UK map`;
  if (place.placeType === "region") return `${count} · Region`;
  return count;
}

function selectSuggestion(result) {
  if (result.type === "band") {
    selectBand(result.band.id);
  } else {
    selectSearchPlace(result.place.id);
  }
}

function renderSuggestions() {
  elements.searchResults.replaceChildren();
  suggestions.forEach((result, index) => {
    const option = document.createElement("li");
    option.id = `search-option-${index}`;
    option.className = "search-option";
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(index === activeSuggestion));
    const type = document.createElement("span");
    type.className = `search-option-type type-${result.type}`;
    type.textContent = result.type === "band"
      ? "Band"
      : result.place.placeType === "fua" ? "FUA" : "Place";
    const name = document.createElement("strong");
    name.textContent = result.type === "band" ? result.band.name : result.place.label;
    const context = document.createElement("span");
    context.className = "search-option-context";
    context.textContent = result.type === "band"
      ? contextForBand(result.band)
      : contextForPlace(result.place);
    option.append(type, name, context);
    option.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      selectSuggestion(result);
    });
    elements.searchResults.append(option);
  });
  const open = suggestions.length > 0;
  elements.searchResults.hidden = !open;
  elements.search.setAttribute("aria-expanded", String(open));
  elements.search.setAttribute(
    "aria-activedescendant",
    activeSuggestion >= 0 ? `search-option-${activeSuggestion}` : "",
  );
  if (suggestions.length) {
    const bandCount = suggestions.filter((result) => result.type === "band").length;
    const placeCount = suggestions.length - bandCount;
    const counts = [];
    if (bandCount) counts.push(`${bandCount} ${bandCount === 1 ? "band" : "bands"}`);
    if (placeCount) counts.push(`${placeCount} ${placeCount === 1 ? "place" : "places"}`);
    elements.searchStatus.textContent = `${suggestions.length} ${suggestions.length === 1 ? "result" : "results"}: ${counts.join(" and ")}`;
  } else {
    elements.searchStatus.textContent = elements.search.value.trim()
      ? `No matching bands or ${isPopulationNormalized() ? "FUAs" : "formation places"}`
      : "";
  }
}

function closeSuggestions() {
  suggestions = [];
  activeSuggestion = -1;
  renderSuggestions();
}

function restartExplorer() {
  clearAreaFilter(false);
  const selectedOrigin = placesById.has(state.selectedOrigin) ? state.selectedOrigin : null;
  const selectedFua = fuasById.has(state.selectedFua) ? state.selectedFua : null;
  const comparison = state.comparison;
  const defaultState = parseExplorerState("", dashboard);
  state = {
    ...defaultState,
    selectedOrigin: selectedOrigin || defaultState.selectedOrigin,
    selectedFua: selectedFua || defaultState.selectedFua,
    comparison,
  };
  updateUrl(state, "replace");
  map.reset();
  closeSuggestions();
  render(false);
}

function updateSuggestions() {
  elements.searchClear.hidden = !elements.search.value;
  if (!elements.search.value.trim()) {
    restartExplorer();
    return;
  }
  suggestions = searchExplorer(dashboard.bands, activeGeographies(), elements.search.value);
  activeSuggestion = suggestions.length ? 0 : -1;
  renderSuggestions();
}

function externalLink(url, icon, label) {
  const link = document.createElement("a");
  link.className = "external-link";
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.setAttribute("aria-label", `Open ${label} in a new tab`);
  const image = document.createElement("img");
  image.src = assetUrl(`/icons/${icon}`);
  image.alt = "";
  image.width = 18;
  image.height = 18;
  link.dataset.label = label;
  link.append(image);
  return link;
}

function metric(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "metric";
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value;
  wrapper.append(term, description);
  return wrapper;
}

function renderDetail() {
  elements.detail.replaceChildren();
  const band = bandsById.get(state.selectedBandId);
  if (!band) {
    const empty = document.createElement("div");
    empty.className = "detail-empty";
    const title = document.createElement("h2");
    title.textContent = selectedAreaPlaceIds === null ? "Search for a band" : "Selected map area";
    const copy = document.createElement("p");
    copy.textContent = selectedAreaPlaceIds === null
      ? "Select any band in the catalog to see its reviewed origin, Spotify snapshot, and place rank."
      : `${numberFormat.format(selectedAreaPlaceIds.length)} ${isPopulationNormalized() ? (selectedAreaPlaceIds.length === 1 ? "FUA" : "FUAs") : (selectedAreaPlaceIds.length === 1 ? "formation place" : "formation places")} selected. Choose a band from the ranking below.`;
    empty.append(title, copy);
    elements.detail.append(empty);
    return;
  }

  const header = document.createElement("header");
  header.className = "detail-header";
  const title = document.createElement("h2");
  title.textContent = band.name;
  const links = document.createElement("div");
  links.className = "external-links";
  links.append(externalLink(band.spotifyUrl, "spotify.svg", "Spotify"));
  if (band.wikipediaUrl) {
    links.append(externalLink(band.wikipediaUrl, "wikipedia.svg", "Wikipedia"));
  }
  const rank = document.createElement("dl");
  rank.className = "catalog-rank";
  const rankLabel = document.createElement("dt");
  rankLabel.textContent = "Catalog rank";
  const rankValue = document.createElement("dd");
  rankValue.textContent = `#${numberFormat.format(band.catalogRank)}`;
  rank.append(rankLabel, rankValue);
  const headerMeta = document.createElement("div");
  headerMeta.className = "detail-header-meta";
  headerMeta.append(links, rank);
  header.append(title, headerMeta);

  const metrics = document.createElement("dl");
  metrics.className = "metrics-grid";
  metrics.append(
    metric("Monthly listeners", numberFormat.format(band.monthlyListeners)),
    metric("Followers", numberFormat.format(band.followers)),
  );

  elements.detail.append(header, metrics);
}

function renderMap(focus) {
  const places = activeGeographies();
  const place = selectedGeography();
  map.setPlaces(places, state.comparison);
  map.setMetric(state.metric);
  map.setSelection(place?.locationStatus === "uk" ? place.id : null, focus);
  if (selectedAreaPlaceIds !== null) {
    elements.mapPlaceLabel.textContent = "Map selection";
    elements.mapPlaceTitle.textContent = "Selected area";
    const geography = isPopulationNormalized() ? "FUA" : "formation place";
    elements.mapStatus.textContent = `${numberFormat.format(selectedAreaPlaceIds.length)} ${selectedAreaPlaceIds.length === 1 ? geography : `${geography}s`}`;
  } else if (!place) {
    elements.mapPlaceLabel.textContent = isPopulationNormalized() ? "FUA overview" : "Overview";
    elements.mapPlaceTitle.textContent = "United Kingdom";
    elements.mapStatus.textContent = isPopulationNormalized()
      ? `${numberFormat.format(dashboard.meta.strictFuaCount)} FUAs · ${numberFormat.format(dashboard.meta.strictFuaMappedBands)} strictly mapped bands`
      : `${numberFormat.format(dashboard.meta.ukOriginPlaces)} reviewed formation places`;
  } else if (isPopulationNormalized()) {
    elements.mapPlaceLabel.textContent = "Functional urban area";
    elements.mapPlaceTitle.textContent = place.label;
    elements.mapStatus.textContent = `${numberFormat.format(place.bandCount)} mapped catalog ${place.bandCount === 1 ? "band" : "bands"} · ${numberFormat.format(place.population)} residents (${place.populationYear})`;
  } else if (place.locationStatus === "outside_uk") {
    elements.mapPlaceLabel.textContent = "Formation place";
    elements.mapPlaceTitle.textContent = place.label;
    elements.mapStatus.textContent = `Outside UK map · ${place.bandCount} catalog ${place.bandCount === 1 ? "band" : "bands"}`;
  } else {
    elements.mapPlaceLabel.textContent = place.placeType === "region" ? "Formation region" : "Formation place";
    elements.mapPlaceTitle.textContent = place.label;
    elements.mapStatus.textContent = `${place.bandCount} catalog ${place.bandCount === 1 ? "band" : "bands"}`;
  }
}

function renderChart() {
  const places = activeGeographies();
  const place = selectedGeography() || null;
  const selectedBand = bandsById.get(state.selectedBandId) || null;
  const config = METRIC_CONFIG[state.metric];
  const metricLabel = isPopulationNormalized()
    ? `Normalized ${config.label.toLowerCase()}`
    : config.label;
  if (selectedAreaPlaceIds !== null) {
    elements.chartTitle.textContent = `Top 10 bands in selected area — ${metricLabel}`;
    elements.chartNote.hidden = true;
    elements.chartNote.textContent = "";
    renderAreaBandChart(
      elements.chart,
      dashboard.bands,
      selectedAreaPlaceIds,
      places,
      state.metric,
      state.comparison,
      (bandId) => selectBand(bandId),
    );
    return;
  }
  if (!place) {
    const geographyLabel = isPopulationNormalized() ? "FUAs" : "formation places";
    elements.chartTitle.textContent = `Top ${PLACE_LEADERBOARD_LIMIT} ${geographyLabel} — ${metricLabel}`;
    const unmappedBand = isPopulationNormalized() && selectedBand && !selectedBand.fuaCode;
    elements.chartNote.hidden = !unmappedBand;
    elements.chartNote.textContent = unmappedBand
      ? `${selectedBand.name} has no strict reviewed FUA assignment and is excluded from this view.`
      : "";
    renderPlaceChart(
      elements.chart,
      places,
      state.metric,
      state.comparison,
      (placeId) => selectPlace(placeId),
    );
    return;
  } else {
    const placeLabel = isPopulationNormalized() ? `${place.label} FUA` : place.label;
    elements.chartTitle.textContent = `Bands from ${placeLabel} — ${metricLabel}`;
  }
  const bandGeography = isPopulationNormalized()
    ? selectedBand?.fuaCode
    : selectedBand?.originCluster;
  if (selectedBand && place && bandGeography !== place.id) {
    const assignment = isPopulationNormalized()
      ? fuasById.get(selectedBand.fuaCode)?.label || "no strictly mapped FUA"
      : selectedBand.originCluster;
    elements.chartNote.textContent = `${selectedBand.name} is assigned to ${assignment}, not ${place.label}.`;
    elements.chartNote.hidden = false;
  } else {
    elements.chartNote.hidden = true;
    elements.chartNote.textContent = "";
  }
  renderBarChart(
    elements.chart,
    dashboard.bands,
    place,
    state.metric,
    state.selectedBandId,
    state.comparison,
    (bandId) => selectBand(bandId),
  );
}

function renderMetricToggle() {
  ["monthly_listeners", "followers"].forEach((metric) => {
    metricButton(metric).setAttribute("aria-pressed", String(metric === state.metric));
  });
}

function renderComparisonToggle() {
  ["raw", "population_normalized"].forEach((comparison) => {
    comparisonButton(comparison).setAttribute(
      "aria-pressed",
      String(comparison === state.comparison),
    );
  });
}

function sourceLink(source) {
  const item = document.createElement("li");
  const link = document.createElement("a");
  link.href = source.sourceUrl || `${REPOSITORY_BASE}${source.path}`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = source.label;
  item.append(link);
  return item;
}

function renderFooter() {
  const freshnessLabels = {
    spotify: "Catalog and Spotify snapshot",
    coordinates: "Origin coordinates",
    genres: "Wikipedia titles (Wikidata)",
    fuaMapping: "Formation-place to FUA mapping",
    population: "OECD FUA population capture",
  };
  elements.footerFreshness.replaceChildren();
  Object.entries(dashboard.meta.freshness).forEach(([key, value]) => {
    if (!value || !freshnessLabels[key]) return;
    const item = document.createElement("li");
    item.textContent = `${freshnessLabels[key]}: ${formattedDate(value)}`;
    elements.footerFreshness.append(item);
  });
  elements.footerCoverage.textContent = `${numberFormat.format(dashboard.meta.catalogBands)} bands · ${numberFormat.format(dashboard.meta.resolvedOriginBands)} with a resolved formation place · ${numberFormat.format(dashboard.meta.ukLocatedBands)} located in the UK · ${numberFormat.format(dashboard.meta.strictFuaMappedBands)} strictly mapped to ${numberFormat.format(dashboard.meta.strictFuaCount)} FUAs`;
  elements.footerProvenance.textContent = `Snapshot ${dashboard.meta.snapshotId} · ${dashboard.meta.sourceFilename} · dashboard built ${dateTimeFormat.format(new Date(dashboard.meta.builtAtUtc))}`;
  elements.footerSources.replaceChildren(...dashboard.meta.sources.map(sourceLink));
}

function render(focusMap = false) {
  renderMetricToggle();
  renderComparisonToggle();
  renderDetail();
  renderMap(focusMap);
  renderChart();
  renderAreaControl();
}

function syncSearchFromState() {
  const band = bandsById.get(state.selectedBandId);
  setSearchValue(band?.name || selectedGeography()?.label || "");
}

function bindEvents() {
  elements.search.addEventListener("input", updateSuggestions);
  elements.search.addEventListener("focus", () => {
    if (elements.search.value.trim()) updateSuggestions();
  });
  elements.search.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && suggestions.length) {
      event.preventDefault();
      activeSuggestion = (activeSuggestion + 1) % suggestions.length;
      renderSuggestions();
    } else if (event.key === "ArrowUp" && suggestions.length) {
      event.preventDefault();
      activeSuggestion = (activeSuggestion - 1 + suggestions.length) % suggestions.length;
      renderSuggestions();
    } else if (event.key === "Enter" && activeSuggestion >= 0) {
      event.preventDefault();
      selectSuggestion(suggestions[activeSuggestion]);
    } else if (event.key === "Escape") {
      closeSuggestions();
    }
  });
  elements.search.addEventListener("blur", () => window.setTimeout(closeSuggestions, 120));
  elements.searchClear.addEventListener("click", () => {
    setSearchValue("");
    restartExplorer();
    elements.search.focus();
  });
  document.querySelectorAll("[data-metric]").forEach((button) => {
    button.addEventListener("click", () => {
      state.metric = button.dataset.metric;
      updateUrl(state, "replace");
      render(false);
    });
  });
  document.querySelectorAll("[data-comparison]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.comparison === state.comparison) return;
      clearAreaFilter(false);
      state.comparison = button.dataset.comparison;
      const band = bandsById.get(state.selectedBandId);
      if (isPopulationNormalized()) {
        state.selectedFua = placesById.get(state.selectedOrigin)?.fuaCode
          || band?.fuaCode
          || null;
      } else {
        state.selectedOrigin = matchingFormationPlace(state.selectedFua)
          || band?.originCluster
          || state.selectedOrigin
          || null;
      }
      syncSearchFromState();
      updateUrl(state, "replace");
      render(Boolean(selectedGeography()));
    });
  });
  document.querySelector("#map-zoom-in").addEventListener("click", () => map.zoomIn());
  document.querySelector("#map-zoom-out").addEventListener("click", () => map.zoomOut());
  document.querySelector("#map-reset").addEventListener("click", () => map.reset());
  elements.mapSelectArea.addEventListener("click", () => {
    if (selectedAreaPlaceIds !== null) {
      clearAreaFilter();
    } else if (map.areaSelectionMode) {
      map.cancelAreaSelection();
      render(false);
    } else {
      map.startAreaSelection();
      renderAreaControl();
      elements.mapStatus.textContent = "Drag across the map to select an area";
    }
  });
  window.addEventListener("popstate", () => {
    clearAreaFilter(false);
    state = parseExplorerState(window.location.search, dashboard);
    syncSearchFromState();
    render(false);
  });
}

async function init() {
  try {
    const loaded = await loadExplorerData();
    dashboard = loaded.dashboard;
    bandsById = new Map(dashboard.bands.map((band) => [band.id, band]));
    placesById = new Map(dashboard.places.map((place) => [place.id, place]));
    fuasById = new Map(dashboard.fuas.map((fua) => [fua.id, fua]));
    state = parseExplorerState(window.location.search, dashboard);
    syncSearchFromState();
    map = new BandMap(
      elements.map,
      loaded.outline,
      dashboard,
      (placeId) => selectPlace(placeId),
      (placeIds) => selectArea(placeIds),
    );
    bindEvents();
    renderFooter();
    render(false);
    elements.loading.hidden = true;
    elements.app.hidden = false;
  } catch (error) {
    elements.loading.hidden = true;
    elements.error.hidden = false;
    elements.error.querySelector("p").textContent = error.message;
  }
}

init();
