const METRIC_CONFIG = {
  monthly_listeners: {
    field: "monthlyListeners",
    placeField: "monthlyListenersTotal",
    rank: "placeRankMonthlyListeners",
    label: "Monthly listeners",
  },
  followers: {
    field: "followers",
    placeField: "followersTotal",
    rank: "placeRankFollowers",
    label: "Followers",
  },
};

const integerFormat = new Intl.NumberFormat("en-GB");
const decimalFormat = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const LEADERBOARD_LIMIT = 10;
export const AREA_BAND_LIMIT = 10;
export const PLACE_LEADERBOARD_LIMIT = 10;

function isPopulationNormalized(comparison) {
  return comparison === "population_normalized";
}

function geographyFields(metric, comparison) {
  const config = METRIC_CONFIG[metric];
  return isPopulationNormalized(comparison)
    ? {
        group: "fuaCode",
        rank: metric === "followers" ? "fuaRankFollowers" : "fuaRankMonthlyListeners",
        value: metric === "followers" ? "followersPerResident" : "monthlyListenersPerResident",
      }
    : { group: "originCluster", rank: config.rank, value: config.placeField };
}

function formattedValue(value, comparison) {
  return isPopulationNormalized(comparison)
    ? decimalFormat.format(value)
    : integerFormat.format(value);
}

function comparisonMetricLabel(metric, comparison) {
  const label = METRIC_CONFIG[metric].label;
  return isPopulationNormalized(comparison)
    ? `Population-normalized ${label.toLowerCase()}`
    : label;
}

function bandValue(band, metric, comparison, population) {
  const value = band[METRIC_CONFIG[metric].field];
  return isPopulationNormalized(comparison) ? value / population : value;
}

export function rankedBands(bands, geography, metric, selectedBandId, comparison = "raw") {
  const fields = geographyFields(metric, comparison);
  const placeBands = bands
    .filter((band) => band[fields.group] === geography)
    .sort((a, b) => a[fields.rank] - b[fields.rank]);
  const rows = placeBands.slice(0, LEADERBOARD_LIMIT).map((band) => ({ band, comparison: false }));
  const selected = placeBands.find((band) => band.id === selectedBandId);
  if (selected && selected[fields.rank] > LEADERBOARD_LIMIT) {
    rows.push({ band: selected, comparison: true });
  }
  return rows;
}

export function rankedPlaces(places, metric, comparison = "raw") {
  const fields = geographyFields(metric, comparison);
  return places
    .filter((place) =>
      place.locationStatus === "uk"
      && (isPopulationNormalized(comparison) || place.placeType === "locality"),
    )
    .sort((a, b) =>
      b[fields.value] - a[fields.value]
      || b.bandCount - a.bandCount
      || a.label.localeCompare(b.label, "en-GB"),
    )
    .slice(0, PLACE_LEADERBOARD_LIMIT);
}

export function rankedAreaBands(
  bands,
  placeIds,
  metric,
  comparison = "raw",
  geographies = [],
) {
  const fields = geographyFields(metric, comparison);
  const selectedPlaces = new Set(placeIds);
  const populationById = new Map(geographies.map((place) => [place.id, place.population]));
  return bands
    .filter((band) => selectedPlaces.has(band[fields.group]))
    .sort((a, b) =>
      bandValue(b, metric, comparison, populationById.get(b[fields.group]))
        - bandValue(a, metric, comparison, populationById.get(a[fields.group]))
      || a.catalogRank - b.catalogRank
      || a.name.localeCompare(b.name, "en-GB"),
    )
    .slice(0, AREA_BAND_LIMIT);
}

function renderRanking(container, rows, ariaLabel, onSelect, comparison = "raw") {
  const maxValue = Math.max(...rows.filter((row) => !row.comparison).map((row) => row.value), 1);
  const list = document.createElement("ol");
  list.className = "bar-list";
  list.setAttribute("aria-label", ariaLabel);

  rows.forEach((row) => {
    const item = document.createElement("li");
    item.className = "bar-row";
    if (row.selected) item.classList.add("is-selected");
    if (row.comparison) item.classList.add("is-comparison");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "bar-button";
    button.setAttribute("aria-label", row.ariaLabel);
    button.addEventListener("click", () => onSelect(row.id));

    const rank = document.createElement("span");
    rank.className = "bar-rank";
    rank.textContent = `#${row.rank}`;
    const name = document.createElement("span");
    name.className = "bar-name";
    name.textContent = row.name;
    const identity = document.createElement("span");
    identity.className = "bar-identity";
    const track = document.createElement("span");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(1.5, (row.value / maxValue) * 100)}%`;
    track.append(fill);
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = formattedValue(row.value, comparison);
    const selected = document.createElement("span");
    selected.className = "bar-selected-label";
    selected.textContent = row.selected ? "✓" : "";
    identity.append(name, selected);
    button.append(rank, identity, track, value);
    item.append(button);
    list.append(item);
  });
  container.append(list);
}

export function renderBarChart(
  container,
  bands,
  place,
  metric,
  selectedBandId,
  comparison,
  onSelectBand,
) {
  const fields = geographyFields(metric, comparison);
  const metricLabel = comparisonMetricLabel(metric, comparison);
  container.replaceChildren();
  if (!place) {
    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.innerHTML = "<strong>Geography unavailable</strong><p>Choose a mapped formation place or FUA to continue browsing the catalog.</p>";
    container.append(empty);
    return;
  }

  const rows = rankedBands(bands, place.id, metric, selectedBandId, comparison).map(({ band, comparison: isComparison }) => ({
    id: band.id,
    rank: band[fields.rank],
    name: band.name,
    value: bandValue(band, metric, comparison, place.population),
    selected: band.id === selectedBandId,
    comparison: isComparison,
    ariaLabel: `Rank ${band[fields.rank]}, ${band.name}, ${formattedValue(bandValue(band, metric, comparison, place.population), comparison)} ${metricLabel.toLowerCase()}${band.id === selectedBandId ? ", selected band" : ""}`,
  }));
  renderRanking(container, rows, `${metricLabel} ranking for ${place.label}`, onSelectBand, comparison);
}

export function renderPlaceChart(container, places, metric, comparison, onSelectPlace) {
  const fields = geographyFields(metric, comparison);
  const metricLabel = comparisonMetricLabel(metric, comparison);
  container.replaceChildren();
  const rows = rankedPlaces(places, metric, comparison).map((place, index) => ({
    id: place.id,
    rank: index + 1,
    name: place.label,
    value: place[fields.value],
    selected: false,
    comparison: false,
    ariaLabel: `Rank ${index + 1}, ${place.label}, ${formattedValue(place[fields.value], comparison)} ${metricLabel.toLowerCase()}, ${integerFormat.format(place.bandCount)} mapped catalog ${place.bandCount === 1 ? "band" : "bands"}`,
  }));
  const geographyLabel = isPopulationNormalized(comparison) ? "FUAs" : "formation places";
  renderRanking(container, rows, `Top ${PLACE_LEADERBOARD_LIMIT} UK ${geographyLabel} by ${metricLabel.toLowerCase()}`, onSelectPlace, comparison);
}

export function renderAreaBandChart(
  container,
  bands,
  placeIds,
  geographies,
  metric,
  comparison,
  onSelectBand,
) {
  const metricLabel = comparisonMetricLabel(metric, comparison);
  const fields = geographyFields(metric, comparison);
  const populationById = new Map(geographies.map((place) => [place.id, place.population]));
  const labelById = new Map(geographies.map((place) => [place.id, place.label]));
  container.replaceChildren();
  const areaBands = rankedAreaBands(bands, placeIds, metric, comparison, geographies);
  if (!areaBands.length) {
    const empty = document.createElement("div");
    empty.className = "chart-empty";
    empty.innerHTML = "<strong>No catalog bands in this area</strong><p>Clear the area or draw a larger rectangle.</p>";
    container.append(empty);
    return;
  }
  const rows = areaBands.map((band, index) => ({
    id: band.id,
    rank: index + 1,
    name: `${band.name} · ${isPopulationNormalized(comparison) ? labelById.get(band.fuaCode) : band.originCluster}`,
    value: bandValue(band, metric, comparison, populationById.get(band[fields.group])),
    selected: false,
    comparison: false,
    ariaLabel: `Rank ${index + 1}, ${band.name}, ${isPopulationNormalized(comparison) ? labelById.get(band.fuaCode) : band.originCluster}, ${formattedValue(bandValue(band, metric, comparison, populationById.get(band[fields.group])), comparison)} ${metricLabel.toLowerCase()}`,
  }));
  renderRanking(container, rows, `Top ${AREA_BAND_LIMIT} bands in the selected map area by ${metricLabel.toLowerCase()}`, onSelectBand, comparison);
}

export { METRIC_CONFIG };
